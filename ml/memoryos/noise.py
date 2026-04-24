from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import joblib
import numpy as np
import sqlite3
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, precision_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from .config import MODEL_DIR, ensure_dirs
from .features import capture_documents


NOISE_MODEL_PATH = MODEL_DIR / "noise_classifier.joblib"


@dataclass
class NoiseTrainingResult:
    model_path: Path
    labeled_count: int
    keep_precision: float
    report: str


def train_noise_classifier(rows: List[sqlite3.Row]) -> NoiseTrainingResult:
    labeled = [row for row in rows if row["is_noise"] is not None]
    if len(labeled) < 20:
        raise ValueError("Need at least 20 labeled captures before training the noise classifier.")

    y = np.array([int(row["is_noise"]) for row in labeled])
    if len(set(y.tolist())) < 2:
        raise ValueError("Need both labels: 0=keep and 1=noise.")

    docs = capture_documents(labeled)
    stratify = y if min(np.bincount(y)) >= 2 else None
    x_train, x_test, y_train, y_test = train_test_split(
        docs,
        y,
        test_size=0.25,
        random_state=42,
        stratify=stratify,
    )

    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    max_features=10_000,
                    ngram_range=(1, 2),
                    min_df=1,
                    strip_accents="unicode",
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=1_000,
                    random_state=42,
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    keep_precision = precision_score(y_test, predictions, pos_label=0, zero_division=0)
    report = classification_report(
        y_test,
        predictions,
        labels=[0, 1],
        target_names=["keep", "noise"],
        zero_division=0,
    )

    ensure_dirs()
    artifact = {
        "pipeline": pipeline,
        "labels": {"keep": 0, "noise": 1},
        "keep_precision": float(keep_precision),
        "labeled_count": len(labeled),
    }
    joblib.dump(artifact, NOISE_MODEL_PATH)

    return NoiseTrainingResult(
        model_path=NOISE_MODEL_PATH,
        labeled_count=len(labeled),
        keep_precision=float(keep_precision),
        report=report,
    )


def load_noise_model(path: Path = NOISE_MODEL_PATH):
    artifact = joblib.load(path)
    return artifact["pipeline"]


def predict_noise(rows: Iterable[sqlite3.Row], model_path: Path = NOISE_MODEL_PATH) -> List[tuple[int, int]]:
    rows = list(rows)
    if not rows:
        return []
    model = load_noise_model(model_path)
    docs = capture_documents(rows)
    predictions = model.predict(docs)
    return [(int(row["id"]), int(label)) for row, label in zip(rows, predictions)]
