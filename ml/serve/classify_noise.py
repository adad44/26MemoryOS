#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from memoryos.db import connect, fetch_captures, update_noise_labels
from memoryos.noise import predict_noise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply the trained noise classifier to unlabeled captures.")
    parser.add_argument("--limit", type=int, default=1000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with connect() as conn:
        rows = fetch_captures(conn, limit=args.limit, labeled=False)
        predictions = predict_noise(rows)
        count = update_noise_labels(conn, predictions)
    print(f"Classified {count} captures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
