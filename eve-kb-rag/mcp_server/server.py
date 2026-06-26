#!/usr/bin/env python3
"""MCP server exposing EVE OS knowledge base search to Claude Code.

Two tools:
  search_eve_kb    — hybrid search (dense + keyword) over indexed docs + source
  read_eve_file    — read a specific file+line range from local clone or GitHub
                     (called after search_eve_kb returns a source_code result)
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


def _hybrid_search(query: str, doc_type: str, top_k: int) -> list[tuple[float, dict]]:
    dense_vec  = _embed(query)
    sparse_vec = _bm25_embed(query)

    dt_filter = (
        Filter(must=[FieldCondition(key="doc_type", match=MatchValue(value=doc_type))])
        if doc_type != "all" else None
    )

    results = _qdrant().query_points(
        collection_name=COLLECTION,
        prefetch=[
            Prefetch(query=dense_vec,  using="dense", filter=dt_filter, limit=top_k * 2),
            Prefetch(query=sparse_vec, using="bm25",  filter=dt_filter, limit=top_k * 2),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=top_k,
        with_payload=True,
    )

    return [(p.score, p.payload) for p in results.points]


# ---------------------------------------------------------------------------
# Result formatting — docs get full chunk, source_code gets excerpt + hint
# ---------------------------------------------------------------------------

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
    """Show EVE knowledge base status: chunk counts by type and configuration.

    Call this to check whether the KB is populated, what was indexed,
    and whether a re-index is needed before testing a new EVE release.
    """
    try:
        total = _qdrant().count(collection_name=COLLECTION, exact=True).count
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
            f"Total chunks: **{total}**\n\n"
            f"| doc_type | chunks |\n|---|---|\n{rows}\n\n"
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
def search_eve_kb(query: str, doc_type: str = "all", top_k: int = 5) -> str:
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
    """
    try:
        results = _hybrid_search(query, doc_type, top_k)
        return _format(results)
    except Exception as e:
        return (
            f"search_eve_kb failed: {e}\n\n"
            f"Check: Is Qdrant running at `{QDRANT_URL}`? "
            f"Is Ollama running with `nomic-embed-text` pulled?"
        )


# ---------------------------------------------------------------------------
# Tool 2: read_eve_file  (Phase 2 — source code only)
# ---------------------------------------------------------------------------

@mcp.tool()
def read_eve_file(path: str, start_line: int = 1, end_line: int = 0) -> str:
    """Read a file from the EVE repo at a specific line range.

    Call this after search_eve_kb returns a source_code result to get the
    full function/logic context that the chunk excerpt omits.
    Tries the local EVE clone first; falls back to GitHub if not found.

    Args:
        path: File path relative to EVE root (e.g. "pkg/pillar/cmd/nim/nim.go")
        start_line: First line to read, 1-indexed (default: 1)
        end_line: Last line to read; 0 means read 120 lines from start_line
    """
    try:
        local = Path(EVE_PATH) / path

        if local.exists():
            all_lines    = local.read_text(encoding="utf-8", errors="ignore").split("\n")
            source_label = "local"
        else:
            url  = f"{GITHUB_RAW}/master/{path}"
            resp = requests.get(url, timeout=15)
            if resp.status_code == 404:
                return (
                    f"File not found: `{path}`\n"
                    f"Checked local: `{local}`\n"
                    f"Checked GitHub: `{url}`"
                )
            resp.raise_for_status()
            all_lines    = resp.text.split("\n")
            source_label = "github:master"

        s   = max(0, start_line - 1)
        e   = end_line if end_line > 0 else min(len(all_lines), s + 120)
        ext = Path(path).suffix.lstrip(".") or "text"

        return (
            f"**`{path}`** lines {s + 1}–{e} ({source_label})\n\n"
            f"```{ext}\n" + "\n".join(all_lines[s:e]) + "\n```"
        )
    except Exception as ex:
        return f"read_eve_file failed for `{path}`: {ex}"


if __name__ == "__main__":
    mcp.run()
