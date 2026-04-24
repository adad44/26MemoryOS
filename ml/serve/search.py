#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from memoryos.db import connect, fetch_captures
from memoryos.index import format_hit, search_index


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search the local MemoryOS index.")
    parser.add_argument("query")
    parser.add_argument("--top-k", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with connect() as conn:
        rows = fetch_captures(conn, non_noise=True)
    rows_by_id = {int(row["id"]): row for row in rows}
    hits = search_index(args.query, rows_by_id, top_k=args.top_k)
    if not hits:
        print("No results.")
        return 0
    for hit in hits:
        print(format_hit(hit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
