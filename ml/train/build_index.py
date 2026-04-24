#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from memoryos.db import connect, fetch_captures
from memoryos.index import DEFAULT_EMBEDDER, build_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the MemoryOS semantic search index.")
    parser.add_argument("--backend", choices=["auto", "sentence", "tfidf"], default="auto")
    parser.add_argument("--model", default=DEFAULT_EMBEDDER)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with connect() as conn:
        rows = fetch_captures(conn, limit=args.limit, non_noise=True)
    path = build_index(rows, model_name=args.model, backend=args.backend)
    print(f"Indexed {len(rows)} captures.")
    print(f"Saved: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
