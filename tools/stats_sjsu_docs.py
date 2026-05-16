#!/usr/bin/env python3
"""
Summarize text files under data/sjsu_docs (or any directory) and estimate RAG
chunk counts using the same splitter defaults as rag_api (RecursiveCharacterTextSplitter).

Usage:
  python tools/stats_sjsu_docs.py
  python tools/stats_sjsu_docs.py --dir data/sjsu_docs --chunk-size 1500 --chunk-overlap 100

Match rag_api .env: set CHUNK_SIZE / CHUNK_OVERLAP or pass flags.

Exact chunk counts match rag_api when LangChain is installed:
  pip install langchain-core langchain-text-splitters
Otherwise a stride-based approximation is printed (often within a few percent).
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
from pathlib import Path

try:
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    _HAS_LANGCHAIN = True
except ImportError:
    Document = None  # type: ignore[misc, assignment]
    RecursiveCharacterTextSplitter = None  # type: ignore[misc, assignment]
    _HAS_LANGCHAIN = False


def approx_chunk_count(text: str, chunk_size: int, chunk_overlap: int) -> int:
    """Stride upper bound when LangChain is unavailable (no separator-aware splits)."""
    if not text:
        return 0
    stride = max(1, chunk_size - chunk_overlap)
    n = len(text)
    if n <= chunk_size:
        return 1
    return 1 + (n - chunk_size + stride - 1) // stride


def count_chunks_for_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    splitter: object | None,
) -> int:
    if _HAS_LANGCHAIN and splitter is not None:
        assert Document is not None
        return len(splitter.split_documents([Document(page_content=text)]))
    return approx_chunk_count(text, chunk_size, chunk_overlap)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Text stats and estimated embedding chunk count for a doc directory.",
    )
    parser.add_argument(
        "--dir",
        "-d",
        type=Path,
        default=Path("data/sjsu_docs"),
        help="Root directory to scan (default: data/sjsu_docs)",
    )
    parser.add_argument(
        "--glob",
        default="*.txt",
        help="Glob relative to each subdirectory (default: *.txt)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=int(os.environ.get("CHUNK_SIZE", "1500")),
        help="RecursiveCharacterTextSplitter chunk_size (default: 1500 or CHUNK_SIZE)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=int(os.environ.get("CHUNK_OVERLAP", "100")),
        help="RecursiveCharacterTextSplitter overlap (default: 100 or CHUNK_OVERLAP)",
    )
    args = parser.parse_args()

    root: Path = args.dir
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 1

    files = sorted(root.rglob(args.glob))
    files = [p for p in files if p.is_file()]
    if not files:
        print(f"No files matching {args.glob!r} under {root}")
        return 0

    splitter = None
    if _HAS_LANGCHAIN:
        splitter = RecursiveCharacterTextSplitter(  # type: ignore[misc]
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )

    total_bytes = 0
    total_chars = 0
    total_lines = 0
    total_words = 0
    sizes: list[int] = []
    total_chunks = 0
    empty_files = 0

    for path in files:
        raw = path.read_bytes()
        text = raw.decode("utf-8", errors="replace")
        nchars = len(text)
        sizes.append(nchars)
        total_bytes += len(raw)
        total_chars += nchars
        total_lines += len(text.splitlines())
        total_words += len(text.split())

        if not text.strip():
            empty_files += 1

        total_chunks += count_chunks_for_text(
            text, args.chunk_size, args.chunk_overlap, splitter
        )

    n = len(files)
    print(f"Directory: {root.resolve()}")
    print(f"Pattern: {args.glob}")
    print(f"Files: {n}")
    print(f"Empty (whitespace-only) bodies: {empty_files}")
    print(f"Total bytes: {total_bytes}")
    print(f"Total characters: {total_chars}")
    print(f"Total lines: {total_lines}")
    print(f"Total words (whitespace split): {total_words}")
    if sizes:
        med = statistics.median(sizes)
        print(f"Chars/file min / median / max: {min(sizes)} / {med:.0f} / {max(sizes)}")
    print(f"Splitter chunk_size / overlap: {args.chunk_size} / {args.chunk_overlap}")
    if _HAS_LANGCHAIN:
        print("Chunk count: exact (LangChain RecursiveCharacterTextSplitter)")
    else:
        print(
            "Chunk count: approximate (pip install langchain-core langchain-text-splitters for exact)",
        )
    print(f"Estimated chunks (embeddings): {total_chunks}")
    if n:
        print(f"Avg chunks per file: {total_chunks / n:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
