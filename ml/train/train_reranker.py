#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from memoryos.reranker import train_reranker


def main() -> int:
    path = train_reranker()
    print(f"Saved re-ranker: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
