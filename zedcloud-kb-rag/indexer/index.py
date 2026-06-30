#!/usr/bin/env python3
"""Index ZedCloud documentation, Swagger, protos, and Go source into Qdrant.

Four content parts — all hybrid search (dense + BM25):

  DOCS       — docs/**/*.md, srvs/*/README.md, libs/*/README.md
               Chunked by markdown headings.

  SWAGGER    — all *.swagger.json / swagger.yaml / openapi.yaml
               One chunk per API endpoint (method + path). The operation is stored
               UNRESOLVED (compact, valid JSON): $ref names like
               "#/definitions/AppInstance" point to the data model — resolve
               field-level detail via proto_defs (the proto messages), not by
               inlining (full inlining explodes to >1 MB per endpoint).

  PROTOS     — **/*.proto (excl. vendor)
               Chunked by message/service/enum/extend — field-level constraints.

  CODE       — srvs/**/*.go and libs/**/*.go (hand-written only; tests, mocks,
               and generated *.pb.go are excluded). Chunked by Go declarations.
               This covers handler/proc/validation logic, not just entrypoints.

doc_type values: zcloud_docs | service_docs | library_docs | swagger_docs
                 | proto_defs | source_code

Provenance & versioning:
  Every point carries a `version` (the git branch). Two branches index into
  the same collection without colliding, so you can hold e.g. a known-good and
  a current build side by side and filter searches by version.
  A `_meta` point per version records source mode, branch, commit, and timestamp
  (surfaced by the kb_info MCP tool).

Two source modes:
  --source local   (default) Read from a local clone (--zcloud-path).
  --source github  Fetch from github.com/zededa/zedcloud (needs GITHUB_TOKEN,
                   private repo). Optional --branch (default: main).

Examples:
    python index.py --zcloud-path ~/git/zedcloud --reset
    python index.py --source github --branch main --reset
    python index.py --zcloud-path ~/git/zedcloud --skip-source
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import ollama
import requests
import yaml
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, Modifier, PointStruct, SparseVector, SparseVectorParams, VectorParams,
)

COLLECTION      = "zcloud_kb"
EMBED_MODEL     = "nomic-embed-text"
QDRANT_URL      = "http://localhost:6333"
VECTOR_DIM      = 768
MAX_CHUNK_CHARS = 1200          # cap on the text that gets embedded (vector quality)
MAX_FULL_OP     = 20000         # cap on stored swagger full_operation payload

GITHUB_REPO = "zededa/zedcloud"
GITHUB_API  = "https://api.github.com/repos"
GITHUB_RAW  = "https://raw.githubusercontent.com"

# Top-level dirs whose Go files we index (recursively, post-exclusion).
CODE_ROOTS = ["srvs", "libs"]
# Top-level dirs to scan for .proto files.
PROTO_ROOTS = ["libs", "srvs", "zobjects", "zservices"]

# Set in main(); included in every point id + payload so versions don't collide.
_VERSION = "local"


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
# DOCS — markdown chunking
# ---------------------------------------------------------------------------

def chunk_markdown(content: str, file_label: str) -> list[dict]:
    """Split markdown into heading-anchored chunks with start_line tracking."""
    heading_re = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    matches    = list(heading_re.finditer(content))

    if not matches:
        text = content.strip()
        return [{"section": file_label, "text": text, "start_line": 1}] if text else []

    chunks   = []
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

    result = []
    for chunk in chunks:
        if len(chunk["text"]) <= MAX_CHUNK_CHARS:
            result.append(chunk)
            continue
        parts      = chunk["text"].split("\n\n")
        current    = ""
        part_num   = 0
        part_start = chunk["start_line"]
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
# SWAGGER — one chunk per endpoint (full operation stored untruncated)
# ---------------------------------------------------------------------------

def _swagger_source_name(path: Path) -> str:
    stem = path.stem.replace(".swagger", "")
    if stem in ("swagger", "openapi"):
        stem = path.parent.parent.name + "_" + stem
    return stem


def _load_swagger_content(content: str, suffix: str) -> dict:
    # Unresolved on purpose — $refs stay as references. Full jsonref inlining
    # explodes some operations to >1 MB; the $ref names are what we want anyway.
    return yaml.safe_load(content) if suffix in (".yaml", ".yml") else json.loads(content)


def chunk_swagger(spec: dict, source_name: str) -> list[dict]:
    """One chunk per endpoint (path + HTTP method). Operation stored unresolved."""
    chunks    = []
    api_title = spec.get("info", {}).get("title", source_name)
    _METHODS  = {"get", "post", "put", "patch", "delete", "head", "options"}

    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in _METHODS or not isinstance(operation, dict):
                continue

            summary     = operation.get("summary", "")
            description = operation.get("description", "")
            tags        = operation.get("tags", [])
            params      = operation.get("parameters", [])
            req_body    = operation.get("requestBody", {})
            responses   = operation.get("responses", {})

            parts = [f"API: {api_title}", f"Endpoint: {method.upper()} {path}"]
            if summary:
                parts.append(f"Summary: {summary}")
            if description:
                parts.append(f"Description: {description}")
            if tags:
                parts.append(f"Tags: {', '.join(tags)}")
            if params:
                param_lines = [
                    f"  - {p.get('name')} ({p.get('in', '?')}): {p.get('description', '')}"
                    for p in params if isinstance(p, dict)
                ]
                if param_lines:
                    parts.append("Parameters:\n" + "\n".join(param_lines))
            if req_body and isinstance(req_body, dict):
                rb_desc = req_body.get("description", "")
                parts.append(f"Request body: {rb_desc}" if rb_desc else "Request body: present")
            for status, resp in responses.items():
                if isinstance(resp, dict) and resp.get("description"):
                    parts.append(f"Response {status}: {resp['description']}")

            # Operation is unresolved (small + valid JSON). Cap only as a
            # pathological-size guard; mark explicitly if ever hit (no silent loss).
            full_op = json.dumps(operation, default=str)
            truncated = False
            if len(full_op) > MAX_FULL_OP:
                full_op = full_op[:MAX_FULL_OP]
                truncated = True

            chunks.append({
                "section":           f"{method.upper()} {path}",
                "text":              "\n".join(parts),
                "api_title":         api_title,
                "path":              path,
                "method":            method.upper(),
                "summary":           summary,
                "tags":              tags,
                "full_operation":    full_op,
                "operation_truncated": truncated,
            })

    return chunks


# ---------------------------------------------------------------------------
# PROTOS — chunk by top-level message/service/enum/extend
# ---------------------------------------------------------------------------

_PROTO_DECL_RE = re.compile(r"^(message|service|enum|extend)\s+(\w+)")


def chunk_proto(content: str, file_label: str) -> list[dict]:
    lines   = content.split("\n")
    chunks  = []
    current: list[str] = []
    c_start = 1
    section = file_label

    for i, line in enumerate(lines):
        line_num = i + 1
        m = _PROTO_DECL_RE.match(line)
        if m and current:
            text = "\n".join(current).strip()
            if len(text) >= 30:
                chunks.append({
                    "section": section, "text": text[:MAX_CHUNK_CHARS],
                    "start_line": c_start, "end_line": line_num - 1,
                })
            current = [line]
            c_start = line_num
            section = f"{m.group(1)} {m.group(2)}"
        else:
            current.append(line)

    if current:
        text = "\n".join(current).strip()
        if len(text) >= 30:
            chunks.append({
                "section": section, "text": text[:MAX_CHUNK_CHARS],
                "start_line": c_start, "end_line": len(lines),
            })
    return chunks


# ---------------------------------------------------------------------------
# CODE — Go source chunking
# ---------------------------------------------------------------------------

_DECL_RE = re.compile(r"^(func|type|var|const)\s")


def chunk_source_go(content: str, file_label: str) -> list[dict]:
    """Chunk Go source by top-level declarations, tracking start/end lines."""
    lines   = content.split("\n")
    chunks  = []
    current: list[str] = []
    c_start = 1

    for i, line in enumerate(lines):
        line_num  = i + 1
        new_decl  = bool(_DECL_RE.match(line)) and len(current) > 5
        too_large = len("\n".join(current)) > MAX_CHUNK_CHARS

        if (new_decl or too_large) and current:
            text = "\n".join(current).strip()
            if text:
                chunks.append({
                    "section": file_label, "text": text[:MAX_CHUNK_CHARS],
                    "start_line": c_start, "end_line": line_num - 1,
                })
            current = [line]
            c_start = line_num
        else:
            current.append(line)

    if current:
        text = "\n".join(current).strip()
        if text:
            chunks.append({
                "section": file_label, "text": text[:MAX_CHUNK_CHARS],
                "start_line": c_start, "end_line": len(lines),
            })
    return chunks


def _is_indexable_go(name: str) -> bool:
    """Hand-written Go only — drop tests, mocks, and generated files."""
    if name.endswith("_test.go"):
        return False
    if name.endswith(".pb.go") or name.endswith(".pb.gw.go"):
        return False
    if name.startswith("mock_") or name.endswith("_mock.go"):
        return False
    if name == "gen.go" or name.endswith("_gen.go") or name.startswith("zz_generated"):
        return False
    return True


# ---------------------------------------------------------------------------
# Qdrant upsert — unified for all content types
# ---------------------------------------------------------------------------

def upsert_chunks(chunks: list[dict], source: str, doc_type: str, client: QdrantClient) -> int:
    count = 0
    for chunk in chunks:
        dense_vec  = embed(chunk["text"])
        sparse_vec = bm25_embed(chunk["text"])
        payload: dict = {
            "version":    _VERSION,
            "source":     source,
            "section":    chunk["section"],
            "doc_type":   doc_type,
            "text":       chunk["text"],
            "start_line": chunk.get("start_line", 1),
        }
        if "end_line" in chunk:
            payload["end_line"] = chunk["end_line"]
        for field in ("api_title", "path", "method", "summary", "tags",
                      "full_operation", "operation_truncated"):
            if field in chunk:
                payload[field] = chunk[field]

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
# LOCAL — indexing functions
# ---------------------------------------------------------------------------

def local_index_docs_dir(zcloud_path: Path, rel_dir: str, doc_type: str, client: QdrantClient) -> int:
    target = zcloud_path / rel_dir
    if not target.exists():
        print(f"  skip {rel_dir} (not found)")
        return 0
    total = 0
    for md_file in sorted(target.glob("**/*.md")):
        content = md_file.read_text(encoding="utf-8", errors="ignore")
        rel     = str(md_file.relative_to(zcloud_path))
        n       = upsert_chunks(chunk_markdown(content, md_file.stem), rel, doc_type, client)
        print(f"  {rel}: {n} chunks")
        total += n
    return total


def local_index_readmes(zcloud_path: Path, parent_dir: str, doc_type: str, client: QdrantClient) -> int:
    target = zcloud_path / parent_dir
    if not target.exists():
        print(f"  skip {parent_dir} (not found)")
        return 0
    total = 0
    for readme in sorted(target.glob("*/README.md")):
        content = readme.read_text(encoding="utf-8", errors="ignore")
        rel     = str(readme.relative_to(zcloud_path))
        n       = upsert_chunks(chunk_markdown(content, readme.parent.name), rel, doc_type, client)
        if n:
            print(f"  {rel}: {n} chunks")
        total += n
    return total


def local_index_swagger(zcloud_path: Path, client: QdrantClient) -> int:
    globs = [
        "libs/zmsg/zapiservices/swagger/*.swagger.json",
        "srvs/*/api/swagger.yaml", "srvs/*/api/swagger.yml",
        "srvs/*/swagger.yaml", "srvs/*/swagger.yml", "srvs/*/doc/swagger.yaml",
        "zservices/swagger/*.swagger.json",
    ]
    seen: set[str] = set()
    files: list[tuple[Path, str]] = []
    for pattern in globs:
        for f in sorted(zcloud_path.glob(pattern)):
            name = _swagger_source_name(f)
            if name not in seen:
                seen.add(name)
                files.append((f, name))

    print(f"  found {len(files)} swagger files (after dedup)")
    total = 0
    for swagger_path, source_name in files:
        rel = str(swagger_path.relative_to(zcloud_path))
        try:
            content = swagger_path.read_text(encoding="utf-8", errors="ignore")
            spec    = _load_swagger_content(content, swagger_path.suffix)
            chunks  = chunk_swagger(spec, source_name)
        except Exception as e:
            print(f"  WARNING: could not load {rel}: {e}")
            continue
        if not chunks:
            continue
        n = upsert_chunks(chunks, rel, "swagger_docs", client)
        print(f"  {rel} ({source_name}): {n} endpoints")
        total += n
    return total


def local_index_protos(zcloud_path: Path, client: QdrantClient) -> int:
    total = 0
    files = sorted(
        p for root in PROTO_ROOTS
        for p in (zcloud_path / root).glob("**/*.proto")
        if "vendor" not in p.parts
    )
    print(f"  found {len(files)} proto files")
    for proto_file in files:
        content = proto_file.read_text(encoding="utf-8", errors="ignore")
        rel     = str(proto_file.relative_to(zcloud_path))
        n       = upsert_chunks(chunk_proto(content, proto_file.stem), rel, "proto_defs", client)
        if n:
            print(f"  {rel}: {n} chunks")
        total += n
    return total


def local_index_source(zcloud_path: Path, client: QdrantClient) -> int:
    total = 0
    seen_dirs = 0
    for root in CODE_ROOTS:
        root_dir = zcloud_path / root
        if not root_dir.exists():
            print(f"  skip {root}/ (not found)")
            continue
        files = sorted(
            p for p in root_dir.glob("**/*.go")
            if "vendor" not in p.parts and _is_indexable_go(p.name)
        )
        print(f"  {root}/: {len(files)} Go files")
        for i, gofile in enumerate(files, 1):
            content = gofile.read_text(encoding="utf-8", errors="ignore")
            rel     = str(gofile.relative_to(zcloud_path))
            n       = upsert_chunks(chunk_source_go(content, rel), rel, "source_code", client)
            total  += n
            if i % 50 == 0:
                print(f"    [{root}] {i}/{len(files)} files, {total} chunks so far...")
        seen_dirs += 1
    return total


# ---------------------------------------------------------------------------
# GITHUB — enumeration via the git trees API (few calls), raw fetch per file
# ---------------------------------------------------------------------------

def _gh_headers(token: str = "") -> dict:
    h = {"Accept": "application/vnd.github+json"}
    tok = token or os.environ.get("GITHUB_TOKEN", "")
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    return h


def _gh_get(url: str, token: str, tries: int = 3):
    """GET with simple backoff on rate-limit / transient errors."""
    import time
    for attempt in range(tries):
        resp = requests.get(url, headers=_gh_headers(token), timeout=30)
        if resp.status_code == 200:
            return resp
        if resp.status_code in (403, 429, 500, 502, 503) and attempt < tries - 1:
            wait = 2 ** attempt * 3
            print(f"    GitHub {resp.status_code} on {url} — retrying in {wait}s")
            time.sleep(wait)
            continue
        return resp
    return resp


def gh_fetch(path: str, branch: str, token: str = "") -> str | None:
    resp = _gh_get(f"{GITHUB_RAW}/{GITHUB_REPO}/{branch}/{path}", token)
    return resp.text if resp.status_code == 200 else None


def gh_list_blobs(top_name: str, branch: str, token: str) -> list[str]:
    """Return all blob paths under a top-level dir using the trees API."""
    top = _gh_get(f"{GITHUB_API}/{GITHUB_REPO}/git/trees/{branch}", token)
    if top.status_code != 200:
        return []
    sha = next((e["sha"] for e in top.json().get("tree", [])
                if e["type"] == "tree" and e["path"] == top_name), None)
    if sha is None:
        return []
    sub = _gh_get(f"{GITHUB_API}/{GITHUB_REPO}/git/trees/{sha}?recursive=1", token)
    if sub.status_code != 200:
        return []
    data = sub.json()
    if data.get("truncated"):
        print(f"  WARNING: GitHub tree for {top_name}/ was truncated — index may be incomplete")
    return [f"{top_name}/{e['path']}" for e in data.get("tree", []) if e["type"] == "blob"]


def _gh_commit(branch: str, token: str) -> str:
    resp = _gh_get(f"{GITHUB_API}/{GITHUB_REPO}/commits/{branch}", token)
    if resp.status_code == 200:
        return resp.json().get("sha", "unknown")[:10]
    return "unknown"


def github_index_docs(branch: str, token: str, client: QdrantClient) -> int:
    print("  listing docs/ from GitHub...")
    total = 0
    for path in sorted(p for p in gh_list_blobs("docs", branch, token) if p.endswith(".md")):
        content = gh_fetch(path, branch, token)
        if content is None:
            continue
        n = upsert_chunks(chunk_markdown(content, Path(path).stem), path, "zcloud_docs", client)
        print(f"  {path}: {n} chunks")
        total += n
    return total


def github_index_readmes(top: str, doc_type: str, branch: str, token: str, client: QdrantClient) -> int:
    total = 0
    # Only direct children: top/<name>/README.md
    readmes = [p for p in gh_list_blobs(top, branch, token)
               if p.endswith("/README.md") and p.count("/") == 2]
    for path in sorted(readmes):
        content = gh_fetch(path, branch, token)
        if content is None:
            continue
        n = upsert_chunks(chunk_markdown(content, Path(path).parent.name), path, doc_type, client)
        if n:
            print(f"  {path}: {n} chunks")
        total += n
    return total


def github_index_swagger(branch: str, token: str, client: QdrantClient) -> int:
    srvs_blobs = gh_list_blobs("srvs", branch, token)
    libs_blobs = gh_list_blobs("libs", branch, token)
    zsvc_blobs = gh_list_blobs("zservices", branch, token)

    seen: set[str] = set()
    files: list[str] = []
    # priority order: libs/zmsg first, then per-service, then zservices fallback
    candidates = (
        [p for p in libs_blobs if "zapiservices/swagger/" in p and p.endswith(".swagger.json")]
        + [p for p in srvs_blobs if p.endswith(("swagger.yaml", "swagger.yml"))]
        + [p for p in zsvc_blobs if p.endswith(".swagger.json")]
    )
    for path in candidates:
        name = _swagger_source_name(Path(path))
        if name not in seen:
            seen.add(name)
            files.append(path)

    print(f"  found {len(files)} swagger files (after dedup)")
    total = 0
    for path in files:
        content = gh_fetch(path, branch, token)
        if content is None:
            print(f"  WARNING: could not fetch {path}")
            continue
        try:
            spec   = _load_swagger_content(content, Path(path).suffix)
            chunks = chunk_swagger(spec, _swagger_source_name(Path(path)))
        except Exception as e:
            print(f"  WARNING: could not parse {path}: {e}")
            continue
        if not chunks:
            continue
        n = upsert_chunks(chunks, path, "swagger_docs", client)
        print(f"  {path}: {n} endpoints")
        total += n
    return total


def github_index_protos(branch: str, token: str, client: QdrantClient) -> int:
    paths: list[str] = []
    for root in PROTO_ROOTS:
        paths += [p for p in gh_list_blobs(root, branch, token)
                  if p.endswith(".proto") and "/vendor/" not in p]
    paths = sorted(set(paths))
    print(f"  found {len(paths)} proto files")
    total = 0
    for path in paths:
        content = gh_fetch(path, branch, token)
        if content is None:
            continue
        n = upsert_chunks(chunk_proto(content, Path(path).stem), path, "proto_defs", client)
        if n:
            print(f"  {path}: {n} chunks")
        total += n
    return total


def github_index_source(branch: str, token: str, client: QdrantClient) -> int:
    total = 0
    for root in CODE_ROOTS:
        files = sorted(p for p in gh_list_blobs(root, branch, token)
                       if p.endswith(".go") and "/vendor/" not in p
                       and _is_indexable_go(Path(p).name))
        print(f"  {root}/: {len(files)} Go files")
        for i, path in enumerate(files, 1):
            content = gh_fetch(path, branch, token)
            if content is None:
                continue
            n = upsert_chunks(chunk_source_go(content, path), path, "source_code", client)
            total += n
            if i % 50 == 0:
                print(f"    [{root}] {i}/{len(files)} files, {total} chunks so far...")
    return total


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
        info       = client.get_collection(COLLECTION)
        sparse_cfg = getattr(info.config.params, "sparse_vectors", None) or {}
        if "bm25" not in sparse_cfg:
            print(
                f"ERROR: Collection '{COLLECTION}' exists but lacks 'bm25' sparse vector config.\n"
                f"Re-run with --reset to rebuild.\n", file=sys.stderr,
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
# Main
# ---------------------------------------------------------------------------

def _local_git(path: Path, *args: str) -> str:
    try:
        out = subprocess.run(["git", "-C", str(path), *args],
                             capture_output=True, text=True, timeout=5)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main():
    global _VERSION

    parser = argparse.ArgumentParser(description="Index ZedCloud into Qdrant (hybrid search)")
    parser.add_argument("--source",       choices=["local", "github"], default="local")
    parser.add_argument("--zcloud-path",  default="/Users/Varuna_1/git/zedcloud",
                        help="Local ZedCloud repo root (--source local only)")
    parser.add_argument("--branch",       default="main",
                        help="Git branch to index (--source github only)")
    parser.add_argument("--github-token", default="",
                        help="GitHub token (overrides GITHUB_TOKEN env var)")
    parser.add_argument("--qdrant-url",   default=QDRANT_URL)
    parser.add_argument("--reset",        action="store_true",
                        help="Wipe the whole collection and re-index from scratch")
    parser.add_argument("--skip-swagger", action="store_true")
    parser.add_argument("--skip-protos",  action="store_true")
    parser.add_argument("--skip-source",  action="store_true")
    args = parser.parse_args()

    client = QdrantClient(url=args.qdrant_url)
    ensure_collection(client, args.reset)

    total = 0

    if args.source == "local":
        zcloud_path = Path(args.zcloud_path)
        if not zcloud_path.exists():
            print(f"ERROR: ZedCloud path not found: {zcloud_path}", file=sys.stderr)
            sys.exit(1)

        branch   = _local_git(zcloud_path, "rev-parse", "--abbrev-ref", "HEAD")
        commit   = _local_git(zcloud_path, "rev-parse", "--short", "HEAD")
        _VERSION = branch if branch != "unknown" else "local"
        print(f"Source: local  ({zcloud_path})  version={_VERSION}  commit={commit}\n")

        print("[zcloud_docs] docs/")
        total += local_index_docs_dir(zcloud_path, "docs", "zcloud_docs", client)
        print("\n[service_docs] srvs/*/README.md")
        total += local_index_readmes(zcloud_path, "srvs", "service_docs", client)
        print("\n[library_docs] libs/*/README.md")
        total += local_index_readmes(zcloud_path, "libs", "library_docs", client)
        if not args.skip_swagger:
            print("\n[swagger_docs] swagger/openapi files")
            total += local_index_swagger(zcloud_path, client)
        if not args.skip_protos:
            print("\n[proto_defs] **/*.proto")
            total += local_index_protos(zcloud_path, client)
        if not args.skip_source:
            print("\n[source_code] srvs/**/*.go + libs/**/*.go (hand-written)")
            total += local_index_source(zcloud_path, client)

        write_meta(client, "local", branch, commit, str(zcloud_path))

    else:
        branch = args.branch
        token  = args.github_token or os.environ.get("GITHUB_TOKEN", "")
        if not token:
            print("WARNING: GITHUB_TOKEN not set. zededa/zedcloud is private — "
                  "requests will fail. Set GITHUB_TOKEN or pass --github-token.",
                  file=sys.stderr)
        _VERSION = branch
        commit   = _gh_commit(branch, token)
        print(f"Source: github  (zededa/zedcloud  branch={branch}  commit={commit})\n")

        print("[zcloud_docs] docs/")
        total += github_index_docs(branch, token, client)
        print("\n[service_docs] srvs/*/README.md")
        total += github_index_readmes("srvs", "service_docs", branch, token, client)
        print("\n[library_docs] libs/*/README.md")
        total += github_index_readmes("libs", "library_docs", branch, token, client)
        if not args.skip_swagger:
            print("\n[swagger_docs] swagger/openapi files")
            total += github_index_swagger(branch, token, client)
        if not args.skip_protos:
            print("\n[proto_defs] **/*.proto")
            total += github_index_protos(branch, token, client)
        if not args.skip_source:
            print("\n[source_code] srvs/**/*.go + libs/**/*.go (hand-written)")
            total += github_index_source(branch, token, client)

        write_meta(client, "github", branch, commit, f"{GITHUB_REPO}@{branch}")

    print(f"\nDone. {total} chunks indexed into '{COLLECTION}' (version={_VERSION}).")


if __name__ == "__main__":
    main()
