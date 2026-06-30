#!/usr/bin/env python3
"""Index EVE OS documentation and source code into Qdrant for semantic search.

Two source modes:

  --source local   (default) Read from a local EVE repo clone.
                   Requires --eve-path pointing to the repo root.

  --source github  Fetch directly from GitHub. No local clone needed.
                   Optional: --branch <name>  (default: master)

What gets indexed:
  eve_docs     — docs/*.md  (75 files, all EVE design/operational docs)
  pillar_docs  — pkg/pillar/docs/*.md  (per-agent implementation docs)
  edgeview     — pkg/edgeview/README.md
  source_code  — pkg/pillar/cmd/*/run.go  (CLI entrypoints + flag definitions)

Examples:
    python index.py --source local --eve-path ~/git/eve
    python index.py --source github
    python index.py --source github --branch eve-9.13 --reset
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import ollama
import requests
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, Modifier, PointStruct, SparseVector, SparseVectorParams, VectorParams,
)

COLLECTION = "eve_kb"
EMBED_MODEL = "nomic-embed-text"
QDRANT_URL = "http://localhost:6333"
VECTOR_DIM = 768
MAX_CHUNK_CHARS = 1200

GITHUB_REPO = "lf-edge/eve"
GITHUB_API  = "https://api.github.com/repos"
GITHUB_RAW  = "https://raw.githubusercontent.com"
GH_HEADERS  = {"Accept": "application/vnd.github+json"}

# (path relative to EVE root, doc_type label)
INDEX_DIRS = [
    ("docs",             "eve_docs"),
    ("pkg/pillar/docs",  "pillar_docs"),
]
INDEX_FILES = [
    ("pkg/edgeview/README.md", "edgeview"),
    ("CLAUDE.md",              "eve_docs"),
]

# Set in main(); included in every point id + payload so versions don't collide.
_VERSION = "master"


# ---------------------------------------------------------------------------
# Embedding + ID helpers
# ---------------------------------------------------------------------------

def embed(text: str) -> list[float]:
    if len(text) > MAX_CHUNK_CHARS:
        text = text[:MAX_CHUNK_CHARS]
    return ollama.embeddings(model=EMBED_MODEL, prompt=text)["embedding"]


_bm25_model: SparseTextEmbedding | None = None


def _get_bm25() -> SparseTextEmbedding:
    global _bm25_model
    if _bm25_model is None:
        _bm25_model = SparseTextEmbedding(model_name="Qdrant/bm25")
    return _bm25_model


def bm25_embed(text: str) -> SparseVector:
    result = list(_get_bm25().embed([text[:MAX_CHUNK_CHARS]]))[0]
    return SparseVector(indices=result.indices.tolist(), values=result.values.tolist())


def make_id(key: str) -> str:
    h = hashlib.md5(key.encode()).hexdigest()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


# ---------------------------------------------------------------------------
# Markdown chunking  (docs + pillar_docs)
# ---------------------------------------------------------------------------

def chunk_markdown(content: str, file_label: str) -> list[dict]:
    """Split markdown into heading-anchored chunks with start_line tracking."""
    heading_re = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches = list(heading_re.finditer(content))

    if not matches:
        text = content.strip()
        return [{"section": file_label, "text": text, "start_line": 1}] if text else []

    chunks = []
    h1_title = ""
    for i, m in enumerate(matches):
        level = len(m.group(1))
        title = m.group(2).strip()
        start = m.start()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        text  = content[start:end].strip()

        if level == 1:
            h1_title = title
        if len(text) < 30:
            continue

        section_label = f"{h1_title} > {title}" if h1_title and level > 1 else title
        start_line    = content[:start].count("\n") + 1
        chunks.append({"section": section_label, "text": text, "start_line": start_line})

    # Split oversized chunks at paragraph boundaries
    result = []
    for chunk in chunks:
        if len(chunk["text"]) <= MAX_CHUNK_CHARS:
            result.append(chunk)
            continue
        parts       = chunk["text"].split("\n\n")
        current     = ""
        part_num    = 0
        part_start  = chunk["start_line"]
        for para in parts:
            if current and len(current) + len(para) > MAX_CHUNK_CHARS:
                result.append({
                    "section":    f"{chunk['section']} (part {part_num})",
                    "text":       current.strip(),
                    "start_line": part_start,
                })
                part_num   += 1
                part_start += current.count("\n")
                current     = para
            else:
                current = f"{current}\n\n{para}" if current else para
        if current.strip():
            result.append({
                "section":    f"{chunk['section']} (part {part_num})",
                "text":       current.strip(),
                "start_line": part_start,
            })
    return result


# ---------------------------------------------------------------------------
# Go source chunking  (source_code)
# ---------------------------------------------------------------------------

_DECL_RE = re.compile(r"^(func|type|var|const)\s")


def chunk_source_go(content: str, file_label: str) -> list[dict]:
    """Chunk Go source by top-level declarations, tracking start/end lines."""
    lines   = content.split("\n")
    chunks  = []
    current: list[str] = []
    c_start = 1

    for i, line in enumerate(lines):
        line_num    = i + 1
        new_decl    = bool(_DECL_RE.match(line)) and len(current) > 5
        too_large   = len("\n".join(current)) > MAX_CHUNK_CHARS

        if (new_decl or too_large) and current:
            text = "\n".join(current).strip()
            if text:
                chunks.append({
                    "section":    file_label,
                    "text":       text[:MAX_CHUNK_CHARS],
                    "start_line": c_start,
                    "end_line":   line_num - 1,
                })
            current  = [line]
            c_start  = line_num
        else:
            current.append(line)

    if current:
        text = "\n".join(current).strip()
        if text:
            chunks.append({
                "section":    file_label,
                "text":       text[:MAX_CHUNK_CHARS],
                "start_line": c_start,
                "end_line":   len(lines),
            })
    return chunks


# ---------------------------------------------------------------------------
# Qdrant upsert
# ---------------------------------------------------------------------------

def upsert_chunks(chunks: list[dict], source: str, doc_type: str, client: QdrantClient) -> int:
    count = 0
    for chunk in chunks:
        dense_vec  = embed(chunk["text"])
        sparse_vec = bm25_embed(chunk["text"])
        payload = {
            "version":    _VERSION,
            "source":     source,
            "section":    chunk["section"],
            "doc_type":   doc_type,
            "text":       chunk["text"],
            "start_line": chunk.get("start_line", 1),
        }
        if "end_line" in chunk:
            payload["end_line"] = chunk["end_line"]

        client.upsert(
            collection_name=COLLECTION,
            points=[PointStruct(
                id=make_id(f"{_VERSION}#{source}#{chunk['section']}#{chunk.get('start_line', 0)}"),
                vector={"dense": dense_vec, "bm25": sparse_vec},
                payload=payload,
            )],
        )
        count += 1
    return count


# ---------------------------------------------------------------------------
# LOCAL source — docs
# ---------------------------------------------------------------------------

def local_index_dir(eve_path: Path, rel_dir: str, doc_type: str, client: QdrantClient) -> int:
    target = eve_path / rel_dir
    if not target.exists():
        print(f"  skip {rel_dir} (not found)")
        return 0
    total = 0
    for md_file in sorted(target.glob("**/*.md")):
        content = md_file.read_text(encoding="utf-8", errors="ignore")
        rel     = str(md_file.relative_to(eve_path))
        n       = upsert_chunks(chunk_markdown(content, md_file.stem), rel, doc_type, client)
        print(f"  {rel}: {n} chunks")
        total += n
    return total


def local_index_file(eve_path: Path, rel_file: str, doc_type: str, client: QdrantClient) -> int:
    path = eve_path / rel_file
    if not path.exists():
        print(f"  skip {rel_file} (not found)")
        return 0
    content = path.read_text(encoding="utf-8", errors="ignore")
    rel     = str(path.relative_to(eve_path))
    n       = upsert_chunks(chunk_markdown(content, path.stem), rel, doc_type, client)
    print(f"  {rel}: {n} chunks")
    return n


# ---------------------------------------------------------------------------
# LOCAL source — Go source code
# ---------------------------------------------------------------------------

def _find_agent_file(agent_dir: Path) -> Path | None:
    """Return the main source file for a pillar agent.
    Newer agents use run.go; older agents use <agentname>.go."""
    for candidate in [agent_dir / "run.go", agent_dir / f"{agent_dir.name}.go"]:
        if candidate.exists():
            return candidate
    return None


def local_index_source(eve_path: Path, client: QdrantClient) -> int:
    cmd_dir = eve_path / "pkg/pillar/cmd"
    if not cmd_dir.exists():
        print("  skip pkg/pillar/cmd (not found)")
        return 0
    total = 0
    for agent_dir in sorted(d for d in cmd_dir.iterdir() if d.is_dir()):
        src = _find_agent_file(agent_dir)
        if src is None:
            continue
        content = src.read_text(encoding="utf-8", errors="ignore")
        rel     = str(src.relative_to(eve_path))
        chunks  = chunk_source_go(content, f"{agent_dir.name}/{src.name}")
        n       = upsert_chunks(chunks, rel, "source_code", client)
        if n:
            print(f"  {rel}: {n} chunks")
        total += n
    return total


# ---------------------------------------------------------------------------
# GITHUB source — docs
# ---------------------------------------------------------------------------

def gh_list_md_files(dir_path: str, branch: str) -> list[str]:
    url  = f"{GITHUB_API}/{GITHUB_REPO}/contents/{dir_path}?ref={branch}"
    resp = requests.get(url, headers=GH_HEADERS, timeout=15)
    if resp.status_code == 404:
        print(f"  skip {dir_path} (not found on branch {branch})")
        return []
    resp.raise_for_status()
    paths = []
    for entry in resp.json():
        if entry["type"] == "file" and entry["name"].endswith(".md"):
            paths.append(entry["path"])
        elif entry["type"] == "dir":
            paths.extend(gh_list_md_files(entry["path"], branch))
    return sorted(paths)


def gh_fetch(path: str, branch: str) -> str | None:
    resp = requests.get(f"{GITHUB_RAW}/{GITHUB_REPO}/{branch}/{path}",
                        headers=GH_HEADERS, timeout=15)
    return resp.text if resp.status_code == 200 else None


def github_index_dir(rel_dir: str, doc_type: str, branch: str, client: QdrantClient) -> int:
    print(f"  listing {rel_dir}/ from GitHub...")
    total = 0
    for path in gh_list_md_files(rel_dir, branch):
        content = gh_fetch(path, branch)
        if content is None:
            continue
        n = upsert_chunks(chunk_markdown(content, Path(path).stem), path, doc_type, client)
        print(f"  {path}: {n} chunks")
        total += n
    return total


def github_index_file(rel_file: str, doc_type: str, branch: str, client: QdrantClient) -> int:
    content = gh_fetch(rel_file, branch)
    if content is None:
        print(f"  skip {rel_file} (not found)")
        return 0
    n = upsert_chunks(chunk_markdown(content, Path(rel_file).stem), rel_file, doc_type, client)
    print(f"  {rel_file}: {n} chunks")
    return n


# ---------------------------------------------------------------------------
# GITHUB source — Go source code
# ---------------------------------------------------------------------------

def github_index_source(branch: str, client: QdrantClient) -> int:
    url  = f"{GITHUB_API}/{GITHUB_REPO}/contents/pkg/pillar/cmd?ref={branch}"
    resp = requests.get(url, headers=GH_HEADERS, timeout=15)
    if resp.status_code != 200:
        print("  skip pkg/pillar/cmd (API error)")
        return 0

    agent_dirs = [e["name"] for e in resp.json() if e["type"] == "dir"]
    total = 0
    for agent in sorted(agent_dirs):
        # Newer agents: run.go. Older agents: <agentname>.go
        content = filename = None
        for candidate in ["run.go", f"{agent}.go"]:
            content = gh_fetch(f"pkg/pillar/cmd/{agent}/{candidate}", branch)
            if content is not None:
                filename = candidate
                break
        if content is None:
            continue
        path   = f"pkg/pillar/cmd/{agent}/{filename}"
        chunks = chunk_source_go(content, f"{agent}/{filename}")
        n      = upsert_chunks(chunks, path, "source_code", client)
        if n:
            print(f"  {path}: {n} chunks")
        total += n
    return total


# ---------------------------------------------------------------------------
# Collection setup
# ---------------------------------------------------------------------------

def ensure_collection(client: QdrantClient, reset: bool) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if reset and COLLECTION in existing:
        print(f"Deleting collection '{COLLECTION}'...")
        client.delete_collection(COLLECTION)
        existing = [c for c in existing if c != COLLECTION]

    if COLLECTION in existing:
        info = client.get_collection(COLLECTION)
        sparse_cfg = getattr(info.config.params, "sparse_vectors", None) or {}
        if "bm25" not in sparse_cfg:
            print(
                f"ERROR: Collection '{COLLECTION}' exists but lacks the 'bm25' sparse vector config.\n"
                f"Re-run with --reset to rebuild the collection with the updated schema:\n\n"
                f"  python index.py --source local --eve-path <path> --reset\n",
                file=sys.stderr,
            )
            sys.exit(1)
        return

    print(f"Creating collection '{COLLECTION}'...")
    client.create_collection(
        COLLECTION,
        vectors_config={"dense": VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)},
        sparse_vectors_config={"bm25": SparseVectorParams(modifier=Modifier.IDF)},
    )


# ---------------------------------------------------------------------------
# Provenance meta point
# ---------------------------------------------------------------------------

def write_meta(client: QdrantClient, source_mode: str, branch: str, commit: str, ref: str) -> None:
    payload = {
        "doc_type":    "_meta",
        "version":     _VERSION,
        "source_mode": source_mode,
        "branch":      branch,
        "commit":      commit,
        "ref":         ref,
        "indexed_at":  datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    client.upsert(
        collection_name=COLLECTION,
        points=[PointStruct(
            id=make_id(f"__meta__#{_VERSION}"),
            vector={"dense": embed(f"meta {_VERSION} {source_mode}"),
                    "bm25":  bm25_embed(_VERSION)},
            payload=payload,
        )],
    )
    print(f"\nProvenance: version={_VERSION} mode={source_mode} branch={branch} "
          f"commit={commit} at {payload['indexed_at']}")


def _local_git(path: Path, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", str(path), *args],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _gh_commit(branch: str) -> str:
    try:
        resp = requests.get(f"{GITHUB_API}/{GITHUB_REPO}/commits/{branch}",
                            headers=GH_HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("sha", "unknown")[:10]
    except Exception:
        pass
    return "unknown"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global _VERSION

    parser = argparse.ArgumentParser(description="Index EVE OS docs + source into Qdrant")
    parser.add_argument("--source",    choices=["local", "github"], default="local")
    parser.add_argument("--eve-path",  default="/Users/Varuna_1/git/eve",
                        help="Local EVE repo root (--source local only)")
    parser.add_argument("--branch",    default="master",
                        help="Git branch/tag (--source github only)")
    parser.add_argument("--qdrant-url", default=QDRANT_URL)
    parser.add_argument("--reset",     action="store_true",
                        help="Wipe and re-index — use when switching EVE releases")
    args = parser.parse_args()

    client = QdrantClient(url=args.qdrant_url)
    ensure_collection(client, args.reset)

    total = 0

    if args.source == "local":
        eve_path = Path(args.eve_path)
        if not eve_path.exists():
            print(f"ERROR: EVE path not found: {eve_path}", file=sys.stderr)
            sys.exit(1)

        branch   = _local_git(eve_path, "rev-parse", "--abbrev-ref", "HEAD")
        commit   = _local_git(eve_path, "rev-parse", "--short", "HEAD")
        _VERSION = branch if branch != "unknown" else "local"
        print(f"Source: local  ({eve_path})  version={_VERSION}  commit={commit}\n")

        for rel_dir, doc_type in INDEX_DIRS:
            print(f"[{doc_type}] {rel_dir}/")
            total += local_index_dir(eve_path, rel_dir, doc_type, client)

        for rel_file, doc_type in INDEX_FILES:
            print(f"\n[{doc_type}] {rel_file}")
            total += local_index_file(eve_path, rel_file, doc_type, client)

        print(f"\n[source_code] pkg/pillar/cmd/*/run.go")
        total += local_index_source(eve_path, client)

        write_meta(client, "local", branch, commit, str(eve_path))

    else:
        branch   = args.branch
        _VERSION = branch
        commit   = _gh_commit(branch)
        print(f"Source: github  (lf-edge/eve  branch={branch}  commit={commit})\n")

        for rel_dir, doc_type in INDEX_DIRS:
            print(f"[{doc_type}] {rel_dir}/")
            total += github_index_dir(rel_dir, doc_type, branch, client)

        for rel_file, doc_type in INDEX_FILES:
            print(f"\n[{doc_type}] {rel_file}")
            total += github_index_file(rel_file, doc_type, branch, client)

        print(f"\n[source_code] pkg/pillar/cmd/*/run.go")
        total += github_index_source(branch, client)

        write_meta(client, "github", branch, commit, f"{GITHUB_REPO}@{branch}")

    print(f"\nDone. {total} chunks indexed into '{COLLECTION}' (version={_VERSION}).")


if __name__ == "__main__":
    main()
