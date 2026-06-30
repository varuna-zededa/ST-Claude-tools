#!/usr/bin/env python3
"""MCP server exposing ZedCloud knowledge base search to Claude Code.

Three tools:
  kb_info          — collection status, provenance (branch/commit/when), chunk counts
  search_zcloud_kb — hybrid search (dense + BM25) over docs, swagger, protos, source
  read_zcloud_file — read a file+line range from the local clone, or GitHub fallback
                     (call after search returns a source_code or proto_defs result)

search_zcloud_kb and read_zcloud_file accept format="markdown" (default, human) or
format="json" (agent-consumable envelope with stable refs + machine-readable `fetch`
actions). The JSON envelope shape is identical across the eve-kb and zcloud-kb servers
(discriminated by the `kb` field) so a multi-KB agent can consume both uniformly.
"""

import json
import os
from pathlib import Path

import requests
from fastmcp import FastMCP
from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition, Filter, Fusion, FusionQuery, MatchValue, Prefetch, SparseVector,
)

# doc_type values that hold real content (excludes the internal _meta provenance point)
DOC_TYPES = ["zcloud_docs", "service_docs", "library_docs",
             "swagger_docs", "proto_defs", "source_code"]

# ---------------------------------------------------------------------------
# Config — written by setup.sh
# ---------------------------------------------------------------------------

_CONFIG_FILE = Path(__file__).parent.parent / "config.json"


def _load_config() -> dict:
    if _CONFIG_FILE.exists():
        return json.loads(_CONFIG_FILE.read_text())
    return {}


_CFG        = _load_config()
QDRANT_URL     = _CFG.get("qdrant_url",    "http://localhost:6333")
ZCLOUD_PATH    = _CFG.get("zcloud_path",   "/Users/Varuna_1/git/zedcloud")
GITHUB_BRANCH  = _CFG.get("github_branch", "main")
COLLECTION     = "zcloud_kb"
EMBED_MODEL    = "nomic-embed-text"
GITHUB_REPO    = "zededa/zedcloud"
GITHUB_RAW     = "https://raw.githubusercontent.com"
KB_NAME        = "zcloud"   # envelope discriminator for multi-KB agents

mcp     = FastMCP("zcloud-kb")
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
    """Structured, agent-consumable form of one search hit.

    Common fields on every item; plus a typed block:
      - source_code / proto_defs: `excerpt` + a machine-readable `fetch` action
      - swagger_docs:            an `api` block with the resolved operation schema
      - docs:                    full `text`
    """
    dt   = p.get("doc_type", "")
    item = {
        "rank":     rank,
        "score":    round(float(score), 4),
        "doc_type": dt,
        "source":   p.get("source", ""),
        "section":  p.get("section", ""),
        "version":  p.get("version", ""),
    }

    if dt in ("source_code", "proto_defs"):
        start = p.get("start_line", 1)
        end   = p.get("end_line", start + 60)
        item["start_line"] = start
        item["end_line"]   = end
        item["excerpt"]    = "\n".join(p.get("text", "").split("\n")[:6])
        item["fetch"]      = {
            "tool": "read_zcloud_file",
            "args": {"path": p.get("source", ""), "start_line": start, "end_line": end},
        }
    elif dt == "swagger_docs":
        raw_op = p.get("full_operation", "")
        api: dict = {
            "service":             p.get("api_title", p.get("source", "")),
            "method":              p.get("method", ""),
            "path":                p.get("path", ""),
            "summary":             p.get("summary", ""),
            "tags":                p.get("tags", []),
            "operation_truncated": bool(p.get("operation_truncated", False)),
        }
        try:
            api["operation"] = json.loads(raw_op) if raw_op else None
        except Exception:
            # Truncated/invalid JSON — hand back the raw string so nothing is lost.
            api["operation"]     = None
            api["operation_raw"] = raw_op
        item["api"] = api
    else:
        item["text"] = p.get("text", "")

    return item


def _format(results: list[tuple[float, dict]]) -> str:
    if not results:
        return "No relevant results found in the ZedCloud knowledge base."

    parts = []
    for score, p in results:
        dt          = p.get("doc_type", "")
        is_readable = dt in ("source_code", "proto_defs")
        is_swagger  = dt == "swagger_docs"
        start       = p.get("start_line", 1)
        end         = p.get("end_line",   start + 60)
        ver         = p.get("version", "")

        header = (
            f"**[{dt}] `{p['source']}`**"
            + (f" (line {start})" if is_readable else "")
            + (f"  ·  _{ver}_" if ver else "")
            + f"  \nSection: _{p['section']}_  \nScore: {score:.2f}"
        )

        if is_readable:
            excerpt = "\n".join(p["text"].split("\n")[:6])
            ext     = Path(p["source"]).suffix.lstrip(".") or "text"
            body = (
                f"```{ext}\n{excerpt}\n...\n```\n\n"
                f"→ Call `read_zcloud_file(\"{p['source']}\", {start}, {end})` for full context."
            )
        elif is_swagger:
            summary  = p.get("summary", "")
            tags     = p.get("tags", [])
            full_op  = p.get("full_operation", "")
            tag_line = f"Tags: {', '.join(tags)}" if tags else ""
            # Show the full operation. Only truncate pathological sizes, and say so.
            op_block = None
            if full_op:
                note = ""
                if p.get("operation_truncated"):
                    note = (f"\n[... operation truncated during indexing; "
                            f"open `{p['source']}` for the complete schema]")
                op_block = f"\n```json\n{full_op}{note}\n```"
            body = "\n".join(filter(None, [
                f"**{p['section']}**",
                f"Service: {p.get('api_title', p['source'])}",
                f"Summary: {summary}" if summary else None,
                tag_line,
                op_block,
            ]))
        else:
            body = p["text"]

        parts.append(f"{header}\n\n{body}")

    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# Tool 1: kb_info
# ---------------------------------------------------------------------------

@mcp.tool()
def kb_info() -> str:
    """Show ZedCloud knowledge base status: provenance, versions, and chunk counts.

    Reports which branch/commit each indexed version came from and when it was
    indexed — check this before trusting answers against a specific build, and
    to see whether a re-index is needed.
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
            prov = "_No provenance recorded — index was built before versioning was added; re-index to populate._"

        # Per-doc_type counts.
        counts = {}
        for dt in DOC_TYPES:
            counts[dt] = _qdrant().count(
                collection_name=COLLECTION,
                count_filter=Filter(must=[FieldCondition(key="doc_type", match=MatchValue(value=dt))]),
                exact=True,
            ).count
        rows = "\n".join(f"| {dt} | {n} |" for dt, n in counts.items())

        return (
            f"**ZedCloud Knowledge Base** (`{COLLECTION}`)\n"
            f"Total points: **{total}**\n\n"
            f"**Versions indexed:**\n{prov}\n\n"
            f"**Chunks by type:**\n| doc_type | chunks |\n|---|---|\n{rows}\n\n"
            f"Qdrant: `{QDRANT_URL}`  \nLocal path: `{ZCLOUD_PATH}`  \n"
            f"GitHub fallback branch: `{GITHUB_BRANCH}`\n\n"
            f"To re-index from local:\n"
            f"```bash\npython indexer/index.py --zcloud-path {ZCLOUD_PATH} --reset\n```"
        )
    except Exception as e:
        return (
            f"Cannot reach Qdrant at `{QDRANT_URL}`: {e}\n\n"
            "Check that Qdrant is running: `curl http://localhost:6333/healthz`"
        )


# ---------------------------------------------------------------------------
# Tool 2: search_zcloud_kb
# ---------------------------------------------------------------------------

@mcp.tool()
def search_zcloud_kb(query: str, doc_type: str = "all", top_k: int = 5,
                     version: str = "", format: str = "markdown") -> str:
    """Search ZedCloud docs, Swagger endpoints, proto definitions, and Go source.

    Uses hybrid search: dense semantic vectors (nomic-embed-text) + BM25 sparse
    vectors fused with Reciprocal Rank Fusion (RRF).
    For source_code and proto_defs results, follow the read_zcloud_file() hint
    to get full context. For swagger_docs, the full operation schema is inline.

    Args:
        query: Natural language query, e.g. "seine app instance deployment validation",
               "device attestation thames", "what fields does create app instance take"
        doc_type: "all" (default) | "zcloud_docs" | "service_docs" | "library_docs"
                  | "swagger_docs" | "proto_defs" | "source_code"
        top_k: Results to return (default 5)
        version: Restrict to one indexed version (git branch, e.g. "main"). Empty
                 searches all indexed versions — pass a version when comparing
                 builds or analyzing a regression against a specific branch.
        format: "markdown" (default, human-readable) or "json" (agent-consumable
                envelope: {kb, query, doc_type, version, count, warnings, results[]}
                where each result carries stable source/line refs, and source_code/
                proto_defs results include a `fetch` action to call read_zcloud_file).
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
            f"search_zcloud_kb failed: {e}\n\n"
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
# Tool 3: read_zcloud_file
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

    base  = Path(ZCLOUD_PATH).resolve()
    local = (base / rel).resolve()
    if not str(local).startswith(str(base)):
        return {"error": f"`{path}` resolves outside the ZedCloud repo root."}

    if local.exists():
        all_lines = local.read_text(encoding="utf-8", errors="ignore").split("\n")
        origin    = "local"
    else:
        token   = os.environ.get("GITHUB_TOKEN", "")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        url     = f"{GITHUB_RAW}/{GITHUB_REPO}/{GITHUB_BRANCH}/{path}"
        resp    = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 404:
            return {"error": f"File not found locally or on GitHub ({GITHUB_BRANCH}): {path}. "
                             "If not checked out locally, set GITHUB_TOKEN for GitHub fallback."}
        resp.raise_for_status()
        all_lines = resp.text.split("\n")
        origin    = f"github:{GITHUB_BRANCH}"

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
def read_zcloud_file(path: str, start_line: int = 1, end_line: int = 0, format: str = "markdown") -> str:
    """Read a file from the ZedCloud repo at a specific line range.

    Call this after search_zcloud_kb returns a source_code or proto_defs result
    to get the full function/message context that the chunk excerpt omits.
    Tries the local clone first; falls back to GitHub if not found locally.

    Args:
        path: File path relative to ZedCloud root
              (e.g. "srvs/seine/appinstproc.go" or "libs/zmsg/device/device.proto")
        start_line: First line to read, 1-indexed (default: 1)
        end_line: Last line to read; 0 means read 120 lines from start_line
        format: "markdown" (default, human-readable) or "json" (agent-consumable envelope)
    """
    try:
        data = _read_core(path, start_line, end_line)
    except Exception as ex:
        data = {"error": f"read_zcloud_file failed for `{path}`: {ex}"}

    if format == "json":
        envelope = {"kb": KB_NAME, "source": path, "warnings": []}
        if "error" in data:
            envelope["error"] = data["error"]
            envelope["warnings"].append("read_failed")
            envelope["content"] = None
        else:
            envelope.update(data)
        return json.dumps(envelope, indent=2)

    # markdown
    if "error" in data:
        return data["error"]
    return (
        f"**`{path}`** lines {data['start_line']}–{data['end_line']} ({data['origin']})\n\n"
        f"```{data['language']}\n{data['content']}\n```"
    )


if __name__ == "__main__":
    mcp.run()
