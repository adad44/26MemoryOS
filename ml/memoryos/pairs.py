from __future__ import annotations

import json
import random
import sqlite3
from pathlib import Path
from typing import List

from .config import PROCESSED_DIR, ensure_dirs
from .features import capture_document


PAIR_PATH = PROCESSED_DIR / "embedding_pairs.jsonl"


def _date_prefix(timestamp: str) -> str:
    return str(timestamp or "")[:10]


def generate_pairs(rows: List[sqlite3.Row], max_pairs: int = 2_000, seed: int = 42) -> Path:
    if len(rows) < 4:
        raise ValueError("Need at least 4 captures to generate embedding pairs.")

    rng = random.Random(seed)
    positives = []
    negatives = []
    by_context: dict[tuple[str, str], List[sqlite3.Row]] = {}

    for row in rows:
        key = (str(row["app_name"]), _date_prefix(row["timestamp"]))
        by_context.setdefault(key, []).append(row)

    for group in by_context.values():
        if len(group) < 2:
            continue
        rng.shuffle(group)
        for idx in range(len(group) - 1):
            positives.append((group[idx], group[idx + 1], 1.0))

    attempts = 0
    while len(negatives) < max_pairs and attempts < max_pairs * 10:
        attempts += 1
        left, right = rng.sample(rows, 2)
        if left["app_name"] == right["app_name"] and _date_prefix(left["timestamp"]) == _date_prefix(right["timestamp"]):
            continue
        negatives.append((left, right, 0.0))

    pairs = positives[: max_pairs // 2] + negatives[: max_pairs // 2]
    rng.shuffle(pairs)

    ensure_dirs()
    with PAIR_PATH.open("w", encoding="utf-8") as handle:
        for left, right, label in pairs:
            handle.write(
                json.dumps(
                    {
                        "text_a": capture_document(left),
                        "text_b": capture_document(right),
                        "label": label,
                        "capture_id_a": int(left["id"]),
                        "capture_id_b": int(right["id"]),
                    }
                )
                + "\n"
            )
    return PAIR_PATH
