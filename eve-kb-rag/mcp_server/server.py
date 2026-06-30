#!/usr/bin/env python3
"""MCP server exposing EVE OS knowledge base search to Claude Code.

Three tools:
  kb_info          — collection status and chunk counts by doc_type
  search_eve_kb    — hybrid search (dense + keyword) over indexed docs + source
  read_eve_file    — read a specific file+line range from local clone or GitHub
                     (called after search_eve_kb returns a source_code result)

search_eve_kb and read_eve_file accept format="markdown" (default, human) or
format="json" (agent-consumable envelope with stable refs + machine-readable `fetch`
actions). The JSON envelope shape is identical across the eve-kb and zcloud-kb servers
(discriminated by the `kb` field) so a multi-KB agent can consume both uniformly.
"""

import json
from pathlib import Path

import requests
from fastmcp import FastMCP
from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition, Filter, Fusion, FusionQuery, MatchValue, Prefetch, SparseVector,
)

# ---------------------------------------------------------------------------
# Config — written by setup.sh, one entry per team member
# ---------------------------------------------------------------------------

_CONFIG_FILE = Path(__file__).parent.parent / "config.json"

def _load_config() -> dict:
    if _CONFIG_FILE.exists():
        return json.loads(_CONFIG_FILE.read_text())
    return {}

_CFG       = _load_config()
QDRANT_URL = _CFG.get("qdrant_url", "http://localhost:6333")
EVE_PATH   = _CFG.get("eve_path",   "/Users/Varuna_1/git/eve")
COLLECTION = "eve_kb"
EMBED_MODEL = "nomic-embed-text"
GITHUB_RAW  = "https://raw.githubusercontent.com/lf-edge/eve"
KB_NAME     = "eve"   # envelope discriminator for multi-KB agents

mcp      = FastMCP("eve-kb")
_client: QdrantClient | None = None


def _qdrant() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=QDRANT_URL)
    return _client


def _embed(text: str) -> list[float]:
    import ollama
    return ollama.embeddings(model=EMBED_MODEL, prompt=text)["embedding"]


# ---------------------------------------------------------------------------
# Hybrid search: dense (nomic) + BM25 sparse  →  RRF fusion
# ---------------------------------------------------------------------------

_bm25_model = None


def _get_bm25():
    global _bm25_model
    if _bm25_model is None:
        from fastembed import SparseTextEmbedding
        _bm25_model = SparseTextEmbedding(model_name="Qdrant/bm25")
    return _bm25_model


def _bm25_embed(text: str) -> SparseVector:
    result = list(_get_bm25().embed([text]))[0]
    return SparseVector(indices=result.indices.tolist(), values=result.values.tolist())


def _build_filter(doc_type: str, version: str) -> Filter:
    must = []
    if doc_type != "all":
        must.append(FieldCondition(key="doc_type", match=MatchValue(value=doc_type)))
    if version:
        must.append(FieldCondition(key="version", match=MatchValue(value=version)))
    # Never surface the internal provenance point in search results.
    must_not = [FieldCondition(key="doc_type", match=MatchValue(value="_meta"))]
    return Filter(must=must or None, must_not=must_not)


def _hybrid_search(query: str, doc_type: str, top_k: int, version: str = "") -> list[tuple[float, dict]]:
    dense_vec  = _embed(query)
    sparse_vec = _bm25_embed(query)
    flt        = _build_filter(doc_type, version)

    results = _qdrant().query_points(
        collection_name=COLLECTION,
        prefetch=[
            Prefetch(query=dense_vec,  using="dense", filter=flt, limit=top_k * 2),
            Prefetch(query=sparse_vec, using="bm25",  filter=flt, limit=top_k * 2),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=top_k,
        with_payload=True,
    )

    return [(p.score, p.payload) for p in results.points]


# ---------------------------------------------------------------------------
# Result formatting — markdown (human) and JSON (agent)
# ---------------------------------------------------------------------------

def _result_item(rank: int, score: float, p: dict) -> dict:
    """Structured, agent-consumable form of one search hit. Shape matches the
    zcloud-kb server (discriminated by `kb`) so an agent consumes both uniformly.
    source_code → excerpt + a machine-readable `fetch` action; docs → full text."""
    dt   = p.get("doc_type", "")
    item = {
        "rank":     rank,
        "score":    round(float(score), 4),
        "doc_type": dt,
        "source":   p.get("source", ""),
        "section":  p.get("section", ""),
        "version":  p.get("version", ""),   # empty until eve-kb is version-indexed
    }
    if dt == "source_code":
        start = p.get("start_line", 1)
        end   = p.get("end_line", start + 60)
        item["start_line"] = start
        item["end_line"]   = end
        item["excerpt"]    = "\n".join(p.get("text", "").split("\n")[:6])
        item["fetch"]      = {
            "tool": "read_eve_file",
            "args": {"path": p.get("source", ""), "start_line": start, "end_line": end},
        }
    else:
        item["text"] = p.get("text", "")
    return item


def _format(results: list[tuple[float, dict]]) -> str:
    if not results:
        return "No relevant results found in the EVE knowledge base."

    parts = []
    for score, p in results:
        is_source = p.get("doc_type") == "source_code"
        start     = p.get("start_line", 1)
        end       = p.get("end_line",   start + 60)

        header = (
            f"**[{p['doc_type']}] `{p['source']}`**"
            + (f" (line {start})" if is_source else "")
            + f"  \nSection: _{p['section']}_  \nScore: {score:.2f}"
        )

        if is_source:
            excerpt = "\n".join(p["text"].split("\n")[:6])
            body = (
                f"```go\n{excerpt}\n...\n```\n\n"
                f"→ Call `read_eve_file(\"{p['source']}\", {start}, {end})` for full context."
            )
        else:
            body = p["text"]

        parts.append(f"{header}\n\n{body}")

    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Tool 1: search_eve_kb
# ---------------------------------------------------------------------------

@mcp.tool()
def kb_info() -> str:
    """Show EVE knowledge base status: provenance, versions, and chunk counts.

    Reports which branch/commit each indexed version came from and when it was
    indexed — check this before trusting answers against a specific EVE release.
    """
    try:
        total = _qdrant().count(collection_name=COLLECTION, exact=True).count

        # Provenance: read all _meta points.
        metas, _ = _qdrant().scroll(
            collection_name=COLLECTION,
            scroll_filter=Filter(must=[FieldCondition(key="doc_type", match=MatchValue(value="_meta"))]),
            limit=50, with_payload=True,
        )
        prov_lines = []
        for m in metas:
            pl = m.payload
            prov_lines.append(
                f"| `{pl.get('version','?')}` | {pl.get('source_mode','?')} | "
                f"`{pl.get('commit','?')}` | {pl.get('indexed_at','?')} |"
            )
        if prov_lines:
            prov = ("| version | source | commit | indexed_at |\n"
                    "|---|---|---|---|\n" + "\n".join(prov_lines))
        else:
            prov = "_No provenance recorded — index predates versioning; re-index to populate._"

        counts = {}
        for dt in ["eve_docs", "pillar_docs", "edgeview", "source_code"]:
            counts[dt] = _qdrant().count(
                collection_name=COLLECTION,
                count_filter=Filter(must=[FieldCondition(key="doc_type", match=MatchValue(value=dt))]),
                exact=True,
            ).count
        rows = "\n".join(f"| {dt} | {n} |" for dt, n in counts.items())

        return (
            f"**EVE Knowledge Base** (`{COLLECTION}`)\n"
            f"Total points: **{total}**\n\n"
            f"**Versions indexed:**\n{prov}\n\n"
            f"**Chunks by type:**\n| doc_type | chunks |\n|---|---|\n{rows}\n\n"
            f"Qdrant: `{QDRANT_URL}`  \nEVE path: `{EVE_PATH}`\n\n"
            f"To re-index for a new release:\n"
            f"```bash\npython indexer/index.py --source local --eve-path {EVE_PATH} --reset\n```"
        )
    except Exception as e:
        return (
            f"Cannot reach Qdrant at `{QDRANT_URL}`: {e}\n\n"
            "Check that Qdrant is running: `curl http://localhost:6333/healthz`"
        )


@mcp.tool()
def search_eve_kb(query: str, doc_type: str = "all", top_k: int = 5,
                  version: str = "", format: str = "markdown") -> str:
    """Search EVE OS documentation and source code.

    Uses hybrid search: dense semantic vectors (nomic-embed-text) + BM25 sparse
    vectors fused with Reciprocal Rank Fusion (RRF) for best-of-both coverage.
    For source_code results, the response includes a read_eve_file() call to
    get full context — always follow that hint for source code questions.

    Args:
        query: Natural language query, e.g. "check network interface status",
               "debug app deployment failure", "nim DHCP probe flags"
        doc_type: "all" (default) | "eve_docs" | "pillar_docs" | "edgeview" | "source_code"
        top_k: Results to return (default 5)
        version: Restrict to one indexed version (git branch, e.g. "master"). Empty
                 searches all indexed versions — pass a version when comparing EVE
                 releases or analyzing a regression against a specific branch.
        format: "markdown" (default, human-readable) or "json" (agent-consumable
                envelope: {kb, query, doc_type, version, count, warnings, results[]}
                where source_code results include a `fetch` action to call read_eve_file).
    """
    try:
        results = _hybrid_search(query, doc_type, top_k, version)
    except Exception as e:
        if format == "json":
            return json.dumps({
                "kb": KB_NAME, "query": query, "doc_type": doc_type,
                "version": version or None, "count": 0,
                "warnings": ["search_failed"], "error": str(e), "results": [],
            }, indent=2)
        return (
            f"search_eve_kb failed: {e}\n\n"
            f"Check: Is Qdrant running at `{QDRANT_URL}`? "
            f"Is Ollama running with `nomic-embed-text` pulled?"
        )

    if format == "json":
        return json.dumps({
            "kb":       KB_NAME,
            "query":    query,
            "doc_type": doc_type,
            "version":  version or None,
            "count":    len(results),
            "warnings": [],
            "results":  [_result_item(i, score, p) for i, (score, p) in enumerate(results, 1)],
        }, indent=2)

    return _format(results)


# ---------------------------------------------------------------------------
# Tool 2: read_eve_file  (Phase 2 — source code only)
# ---------------------------------------------------------------------------

def _safe_rel(path: str) -> Path | None:
    """Reject absolute paths and any '..' traversal; return a clean relative Path."""
    rel = Path(path)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    return rel


def _read_core(path: str, start_line: int, end_line: int) -> dict:
    """Read a repo file (local, then GitHub fallback). Returns a dict with either
    the slice + metadata, or an `error` key. Shared by both output formats."""
    rel = _safe_rel(path)
    if rel is None:
        return {"error": f"`{path}` is not a safe repo-relative path (absolute or contains '..')."}

    base  = Path(EVE_PATH).resolve()
    local = (base / rel).resolve()
    if not str(local).startswith(str(base)):
        return {"error": f"`{path}` resolves outside the EVE repo root."}

    if local.exists():
        all_lines = local.read_text(encoding="utf-8", errors="ignore").split("\n")
        origin    = "local"
    else:
        url  = f"{GITHUB_RAW}/master/{path}"
        resp = requests.get(url, timeout=15)
        if resp.status_code == 404:
            return {"error": f"File not found locally or on GitHub (master): {path}"}
        resp.raise_for_status()
        all_lines = resp.text.split("\n")
        origin    = "github:master"

    s = max(0, start_line - 1)
    e = end_line if end_line > 0 else min(len(all_lines), s + 120)
    return {
        "source":     path,
        "origin":     origin,
        "language":   Path(path).suffix.lstrip(".") or "text",
        "start_line": s + 1,
        "end_line":   e,
        "content":    "\n".join(all_lines[s:e]),
    }


@mcp.tool()
def read_eve_file(path: str, start_line: int = 1, end_line: int = 0, format: str = "markdown") -> str:
    """Read a file from the EVE repo at a specific line range.

    Call this after search_eve_kb returns a source_code result to get the
    full function/logic context that the chunk excerpt omits.
    Tries the local EVE clone first; falls back to GitHub if not found.

    Args:
        path: File path relative to EVE root (e.g. "pkg/pillar/cmd/nim/nim.go")
        start_line: First line to read, 1-indexed (default: 1)
        end_line: Last line to read; 0 means read 120 lines from start_line
        format: "markdown" (default, human-readable) or "json" (agent-consumable envelope)
    """
    try:
        data = _read_core(path, start_line, end_line)
    except Exception as ex:
        data = {"error": f"read_eve_file failed for `{path}`: {ex}"}

    if format == "json":
        envelope = {"kb": KB_NAME, "source": path, "warnings": []}
        if "error" in data:
            envelope["error"] = data["error"]
            envelope["warnings"].append("read_failed")
            envelope["content"] = None
        else:
            envelope.update(data)
        return json.dumps(envelope, indent=2)

    if "error" in data:
        return data["error"]
    return (
        f"**`{path}`** lines {data['start_line']}–{data['end_line']} ({data['origin']})\n\n"
        f"```{data['language']}\n{data['content']}\n```"
    )


if __name__ == "__main__":
    mcp.run()
