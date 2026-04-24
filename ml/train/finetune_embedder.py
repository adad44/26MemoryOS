#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from memoryos.config import MODEL_DIR, ensure_dirs
from memoryos.index import DEFAULT_EMBEDDER
from memoryos.pairs import PAIR_PATH


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune the MemoryOS sentence embedding model.")
    parser.add_argument("--pairs", type=Path, default=PAIR_PATH)
    parser.add_argument("--base-model", default=DEFAULT_EMBEDDER)
    parser.add_argument("--output", type=Path, default=MODEL_DIR / "memoryos-embedder")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        from sentence_transformers import InputExample, SentenceTransformer, losses
        from torch.utils.data import DataLoader
    except ImportError as exc:
        raise SystemExit(
            "sentence-transformers is not installed. Run: python3 -m pip install -r ml/requirements.txt"
        ) from exc

    if not args.pairs.exists():
        raise SystemExit(f"Pairs file does not exist: {args.pairs}")

    examples = []
    with args.pairs.open("r", encoding="utf-8") as handle:
        for line in handle:
            item = json.loads(line)
            examples.append(
                InputExample(
                    texts=[item["text_a"], item["text_b"]],
                    label=float(item["label"]),
                )
            )

    if not examples:
        raise SystemExit("No training examples found.")

    ensure_dirs()
    model = SentenceTransformer(args.base_model)
    dataloader = DataLoader(examples, shuffle=True, batch_size=args.batch_size)
    train_loss = losses.CosineSimilarityLoss(model)
    model.fit(
        train_objectives=[(dataloader, train_loss)],
        epochs=args.epochs,
        warmup_steps=max(10, len(dataloader) // 10),
        output_path=str(args.output),
    )
    print(f"Saved fine-tuned embedder: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
