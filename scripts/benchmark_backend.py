#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sqlite3
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def seed_database(path: Path, captures: int) -> None:
    from ml.memoryos.db import SCHEMA

    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        rows = [
            (
                f"2026-04-24T12:{idx % 60:02d}:00Z",
                "VSCode" if idx % 2 == 0 else "Safari",
                "MemoryOS benchmark",
                f"Benchmark capture {idx} about python embeddings vector search attention debugging privacy controls.",
                "accessibility" if idx % 2 == 0 else "browser",
                0,
            )
            for idx in range(captures)
        ]
        conn.executemany(
            """
            INSERT INTO captures
            (timestamp, app_name, window_title, content, source_type, is_noise)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((pct / 100) * (len(ordered) - 1)))
    return ordered[index]


def timed(label: str, count: int, fn) -> dict[str, float | str]:
    values = []
    for _ in range(count):
        start = time.perf_counter()
        response = fn()
        elapsed_ms = (time.perf_counter() - start) * 1000
        values.append(elapsed_ms)
        assert response.status_code < 400, response.text
    return {
        "name": label,
        "runs": count,
        "mean_ms": round(statistics.mean(values), 2),
        "p50_ms": round(percentile(values, 50), 2),
        "p95_ms": round(percentile(values, 95), 2),
        "max_ms": round(max(values), 2),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark MemoryOS backend endpoints with a seeded temp database.")
    parser.add_argument("--captures", type=int, default=500)
    parser.add_argument("--runs", type=int, default=20)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fd, raw_path = tempfile.mkstemp(prefix="memoryos-benchmark.", suffix=".db")
    os.close(fd)
    db_path = Path(raw_path)
    os.environ["MEMORYOS_DB"] = str(db_path)

    try:
        seed_database(db_path, args.captures)

        from fastapi.testclient import TestClient
        from backend.main import app

        client = TestClient(app)
        refresh = client.post("/refresh-index", json={"backend": "tfidf"})
        assert refresh.status_code == 200, refresh.text

        results = [
            timed("health", args.runs, lambda: client.get("/health")),
            timed("stats", args.runs, lambda: client.get("/stats")),
            timed("recent", args.runs, lambda: client.get("/recent?limit=50")),
            timed(
                "search",
                args.runs,
                lambda: client.post("/search", json={"query": "python embedding search", "top_k": 10}),
            ),
        ]

        print("| Endpoint | Runs | Mean ms | P50 ms | P95 ms | Max ms |")
        print("| :-- | --: | --: | --: | --: | --: |")
        for row in results:
            print(
                f"| {row['name']} | {row['runs']} | {row['mean_ms']} | "
                f"{row['p50_ms']} | {row['p95_ms']} | {row['max_ms']} |"
            )
    finally:
        db_path.unlink(missing_ok=True)
        (ROOT / "ml" / "models" / "search_index.joblib").unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
