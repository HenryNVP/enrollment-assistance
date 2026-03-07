#!/usr/bin/env python3
"""
Ingest documents from a directory into the RAG API vector store.

Use this to build the vector store from enrollment_docs/ms-ai (or any folder).
Each file is uploaded with a stable file_id so re-running replaces that document.

Usage:
  python tools/ingest_rag.py [--dir enrollment_docs/ms-ai] [--rag-url URL]

Requires: RAG_API_URL (or --rag-url), and JWT_SECRET (from RAG API .env) or RAG_TOKEN.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

try:
    import httpx
    import jwt as jwt_lib
except ImportError:
    try:
        from jose import jwt as jwt_lib
    except ImportError:
        jwt_lib = None
if jwt_lib is None:
    print("Install: pip install httpx PyJWT (or python-jose)", file=sys.stderr)
    sys.exit(1)

# Extensions the RAG API can ingest (see document_loader)
RAG_EXTENSIONS = {
    "pdf", "txt", "md", "csv", "rst", "xml", "ppt", "pptx",
    "doc", "docx", "xls", "xlsx", "json", "epub",
}

# MIME types for upload
MIME = {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "md": "text/markdown",
    "csv": "text/csv",
    "json": "application/json",
}


def slug_file_id(path: Path) -> str:
    """Stable file_id from path (e.g. ms-ai/prereq.txt -> ms-ai-prereq)."""
    name = path.with_suffix("").name
    parent = path.parent.name
    if parent and parent not in (".", ".."):
        base = f"{parent}-{name}"
    else:
        base = name
    return re.sub(r"[^\w\-]", "_", base).strip("_") or "doc"


def get_token(jwt_secret: str | None) -> str | None:
    if not jwt_secret:
        return os.environ.get("RAG_TOKEN", "").strip() or None
    try:
        import datetime
        payload = {
            "id": "ingest-script",
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1),
        }
        return jwt_lib.encode(payload, jwt_secret, algorithm="HS256")
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest a directory of documents into RAG API.")
    parser.add_argument(
        "--dir", "-d",
        default="enrollment_docs/ms-ai",
        help="Directory to ingest (default: enrollment_docs/ms-ai)",
    )
    parser.add_argument(
        "--rag-url",
        default=os.environ.get("RAG_API_URL", "http://localhost:8010"),
        help="RAG API base URL",
    )
    parser.add_argument(
        "--entity-id",
        default=os.environ.get("RAG_ENTITY_ID", "public"),
        help="entity_id for RAG (default: public)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list files that would be ingested",
    )
    args = parser.parse_args()

    root = Path(args.dir)
    if not root.is_dir():
        print(f"Directory not found: {root}", file=sys.stderr)
        return 1

    files = [
        f for f in root.rglob("*")
        if f.is_file() and f.suffix.lstrip(".").lower() in RAG_EXTENSIONS
    ]
    files.sort(key=lambda p: p.name)

    if not files:
        print(f"No supported files in {root}. Extensions: {', '.join(sorted(RAG_EXTENSIONS))}")
        return 0

    if args.dry_run:
        for f in files:
            print(slug_file_id(f), f)
        return 0

    jwt_secret = os.environ.get("JWT_SECRET", "").strip()
    if not jwt_secret:
        rag_env = Path(__file__).resolve().parent.parent / "backend" / "services" / "rag_api" / ".env"
        if rag_env.exists():
            for line in rag_env.read_text().splitlines():
                if line.strip().startswith("JWT_SECRET="):
                    jwt_secret = line.split("=", 1)[1].strip().strip("'\"").strip()
                    break
    token = get_token(jwt_secret)
    if not token:
        print("No auth: set JWT_SECRET or RAG_TOKEN (or add JWT_SECRET to backend/services/rag_api/.env)", file=sys.stderr)
        return 1

    embed_url = f"{args.rag_url.rstrip('/')}/embed"
    uploaded = 0
    for path in files:
        file_id = slug_file_id(path)
        ext = path.suffix.lstrip(".").lower()
        mime = MIME.get(ext, "application/octet-stream")
        try:
            with path.open("rb") as f:
                r = httpx.post(
                    embed_url,
                    headers={"Authorization": f"Bearer {token}"},
                    data={"file_id": file_id, "entity_id": args.entity_id},
                    files={"file": (path.name, f, mime)},
                    timeout=120.0,
                )
            if r.status_code == 200 and r.json().get("status") is True:
                print(f"  {file_id}")
                uploaded += 1
            else:
                print(f"  {file_id} FAILED: {r.status_code} {r.text[:200]}", file=sys.stderr)
        except Exception as e:
            print(f"  {file_id} ERROR: {e}", file=sys.stderr)

    print(f"\nIngested {uploaded}/{len(files)} files into RAG at {args.rag_url}")
    return 0 if uploaded == len(files) else 1


if __name__ == "__main__":
    sys.exit(main())
