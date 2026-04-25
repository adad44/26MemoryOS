from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier

from .config import MODEL_DIR, ensure_dirs
from .db import connect, fetch_captures
from .index import SearchHit, search_index


RERANKER_PATH = MODEL_DIR / "temporal_reranker.joblib"


def _parse_timestamp(value: str) -> datetime:
    text = str(value or "").replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _features(
    query: str,
    row,
    similarity: float,
    now: datetime,
    avg_dwell_ms: float = 0.0,
) -> List[float]:
    captured_at = _parse_timestamp(row["timestamp"])
    hours_since = max(0.0, (now - captured_at).total_seconds() / 3600.0)
    app_name = str(row["app_name"] or "").lower()
    title = str(row["window_title"] or "").lower()
    query_lower = query.lower()
    app_match = 1.0 if app_name and app_name in query_lower else 0.0
    title_match = 1.0 if title and any(token in title for token in query_lower.split()) else 0.0
    content_length = min(len(str(row["content"] or "")) / 5_000.0, 1.0)
    dwell_scaled = min(max(avg_dwell_ms, 0.0) / 120_000.0, 1.0)
    return [float(similarity), hours_since, app_match, title_match, content_length, dwell_scaled]


def _click_stats(capture_ids: Iterable[int]) -> Dict[int, float]:
    ids = sorted({int(capture_id) for capture_id in capture_ids})
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT capture_id, AVG(COALESCE(dwell_ms, 0)) AS avg_dwell_ms
            FROM search_clicks
            WHERE capture_id IN ({placeholders})
            GROUP BY capture_id
            """,
            ids,
        ).fetchall()
    return {int(row["capture_id"]): float(row["avg_dwell_ms"] or 0.0) for row in rows}


def rerank_hits(query: str, hits: List[SearchHit]) -> tuple[List[tuple[SearchHit, float]], str]:
    if not hits:
        return [], "none"

    now = datetime.now(timezone.utc)
    dwell_by_capture = _click_stats(hit.capture_id for hit in hits)
    feature_rows = np.array(
        [
            _features(query, hit.row, hit.score, now, dwell_by_capture.get(hit.capture_id, 0.0))
            for hit in hits
        ],
        dtype="float32",
    )

    if RERANKER_PATH.exists():
        try:
            artifact = joblib.load(RERANKER_PATH)
            model = artifact["model"]
            probabilities = model.predict_proba(feature_rows)[:, 1]
            ranked = sorted(zip(hits, probabilities.tolist()), key=lambda item: item[1], reverse=True)
            return ranked, "trained"
        except Exception:
            pass

    similarities = feature_rows[:, 0]
    hours_since = feature_rows[:, 1]
    dwell_scaled = feature_rows[:, 5]
    recency = 1.0 / (1.0 + np.log1p(hours_since))
    heuristic = (0.72 * similarities) + (0.18 * recency) + (0.10 * dwell_scaled)
    ranked = sorted(zip(hits, heuristic.tolist()), key=lambda item: item[1], reverse=True)
    return ranked, "heuristic"


def build_reranker_training_set(top_k: int = 30) -> Tuple[np.ndarray, np.ndarray]:
    with connect() as conn:
        clicks = conn.execute(
            "SELECT query, capture_id, dwell_ms FROM search_clicks ORDER BY clicked_at DESC"
        ).fetchall()
        rows = fetch_captures(conn, non_noise=True)

    if not clicks:
        raise ValueError("No search_clicks rows available. Collect click data before training the re-ranker.")

    rows_by_id = {int(row["id"]): row for row in rows}
    x_values = []
    y_values = []
    now = datetime.now(timezone.utc)

    for click in clicks:
        clicked_id = int(click["capture_id"])
        hits = search_index(str(click["query"]), rows_by_id, top_k=top_k)
        for hit in hits:
            x_values.append(_features(str(click["query"]), hit.row, hit.score, now, float(click["dwell_ms"] or 0)))
            y_values.append(1 if hit.capture_id == clicked_id else 0)

    if len(set(y_values)) < 2:
        raise ValueError("Need both clicked and non-clicked candidates to train the re-ranker.")

    return np.array(x_values, dtype="float32"), np.array(y_values, dtype="int64")


def train_reranker() -> Path:
    x_values, y_values = build_reranker_training_set()
    model = GradientBoostingClassifier(n_estimators=100, random_state=42)
    model.fit(x_values, y_values)
    ensure_dirs()
    artifact = {
        "model": model,
        "features": [
            "cosine_similarity",
            "hours_since_capture",
            "app_match",
            "title_token_match",
            "content_length_scaled",
            "avg_dwell_scaled",
        ],
        "training_rows": int(len(y_values)),
    }
    joblib.dump(artifact, RERANKER_PATH)
    return RERANKER_PATH
