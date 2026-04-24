#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from memoryos.db import connect, fetch_captures, update_noise_labels
from memoryos.features import result_snippet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manually label captures as keep or noise.")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--include-labeled", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with connect() as conn:
        rows = fetch_captures(
            conn,
            limit=args.limit,
            labeled=None if args.include_labeled else False,
        )
        if not rows:
            print("No captures available to label.")
            return 0

        labels = []
        print("Label each capture: 0=keep, 1=noise, s=skip, q=quit")
        for row in rows:
            print("\n" + "-" * 80)
            print(f"id: {row['id']}")
            print(f"time: {row['timestamp']}")
            print(f"app: {row['app_name']} | source: {row['source_type']}")
            print(f"title: {row['window_title'] or ''}")
            print(result_snippet(row["content"], max_chars=700))
            answer = input("label> ").strip().lower()
            if answer == "q":
                break
            if answer == "s" or answer == "":
                continue
            if answer not in {"0", "1"}:
                print("Invalid label; skipped.")
                continue
            labels.append((int(row["id"]), int(answer)))

        count = update_noise_labels(conn, labels)
        print(f"Saved {count} labels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
