#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from memoryos.db import connect, fetch_captures
from memoryos.noise import train_noise_classifier


def main() -> int:
    with connect() as conn:
        rows = fetch_captures(conn, labeled=True)
    result = train_noise_classifier(rows)
    print(f"Saved: {result.model_path}")
    print(f"Labeled captures: {result.labeled_count}")
    print(f"Keep precision: {result.keep_precision:.3f}")
    print(result.report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
