#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from memoryos.db import connect, fetch_captures
from memoryos.pairs import generate_pairs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate contrastive embedding pairs from captured data.")
    parser.add_argument("--max-pairs", type=int, default=2000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with connect() as conn:
        rows = fetch_captures(conn, non_noise=True)
    path = generate_pairs(rows, max_pairs=args.max_pairs)
    print(f"Saved pairs: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
