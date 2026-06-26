#!/usr/bin/env python3
"""
Ingest Swagger/OpenAPI spec files into Qdrant using nomic-embed-text via Ollama.

Usage:
    python ingest.py <file_or_glob> [<file_or_glob> ...]

Examples:
    python ingest.py ~/git/zedcloud/zservices/swagger/*.swagger.json
    python ingest.py ~/git/zedcloud/srvs/ganges/api/swagger.yaml myservice
"""

import glob
import hashlib
import json
import sys
from pathlib import Path

import jsonref
import requests
import yaml
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

OLLAMA_URL = "http://localhost:11434/api/embeddings"
EMBED_MODEL = "nomic-embed-text"
QDRANT_URL = "http://localhost:6333"
COLLECTION = "swagger_docs"
VECTOR_SIZE = 768  # nomic-embed-text output dims
BATCH_SIZE = 50    # upsert in batches to avoid large payloads


def get_embedding(text: str) -> list[float]:
    resp = requests.post(OLLAMA_URL, json={"model": EMBED_MODEL, "prompt": text}, timeout=30)
    resp.raise_for_status()
    return resp.json()["embedding"]


def load_swagger(path: str) -> dict:
    with open(path) as f:
        raw = yaml.safe_load(f) if path.endswith((".yaml", ".yml")) else json.load(f)
    # Resolve all $ref inline so every chunk is self-contained
    return jsonref.replace_refs(raw, proxies=False)


def chunk_swagger(spec: dict, source_name: str) -> list[dict]:
    """One chunk per endpoint (path + HTTP method)."""
    chunks = []
    info = spec.get("info", {})
    api_title = info.get("title", source_name)

    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method not in ("get", "post", "put", "patch", "delete", "head", "options"):
                continue
            if not isinstance(operation, dict):
                continue

            summary = operation.get("summary", "")
            description = operation.get("description", "")
            tags = operation.get("tags", [])
            params = operation.get("parameters", [])
            request_body = operation.get("requestBody", {})
            responses = operation.get("responses", {})

            text_parts = [
                f"API: {api_title}",
                f"Endpoint: {method.upper()} {path}",
            ]
            if summary:
                text_parts.append(f"Summary: {summary}")
            if description:
                text_parts.append(f"Description: {description}")
            if tags:
                text_parts.append(f"Tags: {', '.join(tags)}")

            if params:
                param_strs = [
                    f"  - {p.get('name')} ({p.get('in', '?')}): {p.get('description', '')}"
                    for p in params if isinstance(p, dict)
                ]
                if param_strs:
                    text_parts.append("Parameters:\n" + "\n".join(param_strs))

            if request_body and isinstance(request_body, dict):
                rb_desc = request_body.get("description", "")
                text_parts.append(f"Request body: {rb_desc}" if rb_desc else "Request body: present")

            for status, resp in responses.items():
                if isinstance(resp, dict):
                    resp_desc = resp.get("description", "")
                    if resp_desc:
                        text_parts.append(f"Response {status}: {resp_desc}")

            text = "\n".join(text_parts)

            # Store the full inlined operation for direct retrieval (capped at 6KB)
            try:
                full_op = json.dumps(dict(operation), default=str)[:6000]
            except Exception:
                full_op = "{}"

            chunk_id = int(
                hashlib.md5(f"{source_name}:{method}:{path}".encode()).hexdigest()[:15], 16
            )

            chunks.append({
                "id": chunk_id,
                "text": text,
                "payload": {
                    "source": source_name,
                    "api_title": api_title,
                    "path": path,
                    "method": method.upper(),
                    "summary": summary,
                    "tags": tags,
                    "full_operation": full_op,
                },
            })

    return chunks


def ensure_collection(client: QdrantClient):
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
        print(f"Created collection '{COLLECTION}'")


def ingest_file(path: str, client: QdrantClient, source_override: str = None):
    stem = Path(path).stem.replace(".swagger", "")
    # Fall back to parent dir name when filename is generic (e.g. swagger.yaml)
    if stem in ("swagger", "openapi"):
        stem = Path(path).parent.parent.name + "_" + stem
    source_name = source_override or stem
    print(f"\nIngesting {source_name} ({path})")

    try:
        spec = load_swagger(path)
    except Exception as e:
        print(f"  ERROR loading file: {e}")
        return 0

    chunks = chunk_swagger(spec, source_name)
    if not chunks:
        print(f"  No endpoints found — skipping")
        return 0

    print(f"  {len(chunks)} endpoints found, embedding...")

    points = []
    for i, chunk in enumerate(chunks):
        try:
            embedding = get_embedding(chunk["text"])
        except Exception as e:
            print(f"  WARNING: embedding failed for {chunk['payload']['method']} {chunk['payload']['path']}: {e}")
            continue

        points.append(PointStruct(
            id=chunk["id"],
            vector=embedding,
            payload=chunk["payload"],
        ))

        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(chunks)}] embedded...")

    # Upsert in batches
    for start in range(0, len(points), BATCH_SIZE):
        batch = points[start:start + BATCH_SIZE]
        client.upsert(collection_name=COLLECTION, points=batch)

    print(f"  Done — {len(points)} endpoints indexed from {source_name}")
    return len(points)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    client = QdrantClient(url=QDRANT_URL)
    ensure_collection(client)

    # Expand globs and collect unique paths
    paths = []
    for pattern in sys.argv[1:]:
        expanded = glob.glob(pattern)
        if expanded:
            paths.extend(expanded)
        elif Path(pattern).exists():
            paths.append(pattern)
        else:
            print(f"WARNING: no files matched '{pattern}'")

    if not paths:
        print("No files to ingest.")
        sys.exit(1)

    total = 0
    for path in sorted(set(paths)):
        total += ingest_file(path, client)

    collection_info = client.get_collection(COLLECTION)
    print(f"\nIngestion complete. Total new/updated: {total}")
    print(f"Collection '{COLLECTION}' now has {collection_info.points_count} points total.")


if __name__ == "__main__":
    main()
