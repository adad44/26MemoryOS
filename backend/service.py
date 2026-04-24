from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional

from .config import PROJECT_ROOT

ML_ROOT = PROJECT_ROOT / "ml"
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from memoryos.config import database_path
from memoryos.db import CAPTURE_COLUMNS, connect, fetch_captures
from memoryos.features import normalize_text, result_snippet
from memoryos.index import DEFAULT_EMBEDDER, INDEX_ARTIFACT_PATH, build_index, search_index

from .schemas import CaptureResult
from .schemas import PrivacySettings


def row_to_capture_result(row: sqlite3.Row, score: Optional[float] = None, rank: Optional[int] = None) -> CaptureResult:
    content = str(row["content"] or "")
    return CaptureResult(
        id=int(row["id"]),
        score=score,
        rank=rank,
        timestamp=str(row["timestamp"]),
        app_name=str(row["app_name"]),
        window_title=row["window_title"],
        content=content,
        snippet=result_snippet(content),
        source_type=str(row["source_type"]),
        url=row["url"],
        file_path=row["file_path"],
        is_noise=row["is_noise"],
    )


def search(query: str, top_k: int) -> list[CaptureResult]:
    if not INDEX_ARTIFACT_PATH.exists():
        raise FileNotFoundError("Search index is missing. Run /refresh-index or ml/train/build_index.py first.")
    with connect() as conn:
        rows = fetch_captures(conn, non_noise=True)
    rows_by_id = {int(row["id"]): row for row in rows}
    hits = search_index(query, rows_by_id, top_k=top_k)
    return [
        row_to_capture_result(hit.row, score=hit.score, rank=hit.rank)
        for hit in hits
    ]


def recent(limit: int, app_name: Optional[str] = None, source_type: Optional[str] = None) -> list[CaptureResult]:
    where = []
    params: list[object] = []
    if app_name:
        where.append("app_name = ?")
        params.append(app_name)
    if source_type:
        where.append("source_type = ?")
        params.append(source_type)

    sql = f"SELECT {CAPTURE_COLUMNS} FROM captures"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_capture_result(row) for row in rows]


def stats() -> dict:
    db_path = database_path()
    with connect() as conn:
        total = int(conn.execute("SELECT COUNT(*) AS count FROM captures").fetchone()["count"])
        by_app = [
            {"app_name": row["app_name"], "count": int(row["count"])}
            for row in conn.execute(
                """
                SELECT app_name, COUNT(*) AS count
                FROM captures
                GROUP BY app_name
                ORDER BY count DESC
                LIMIT 20
                """
            )
        ]
        by_source = [
            {"source_type": row["source_type"], "count": int(row["count"])}
            for row in conn.execute(
                """
                SELECT source_type, COUNT(*) AS count
                FROM captures
                GROUP BY source_type
                ORDER BY count DESC
                """
            )
        ]
        noise_counts = [
            {"is_noise": row["is_noise"], "count": int(row["count"])}
            for row in conn.execute(
                """
                SELECT is_noise, COUNT(*) AS count
                FROM captures
                GROUP BY is_noise
                ORDER BY is_noise
                """
            )
        ]
        latest = conn.execute("SELECT MAX(timestamp) AS latest FROM captures").fetchone()["latest"]

    return {
        "database_path": str(db_path),
        "total_captures": total,
        "indexed_available": INDEX_ARTIFACT_PATH.exists(),
        "counts_by_app": by_app,
        "counts_by_source_type": by_source,
        "noise_counts": noise_counts,
        "latest_capture_at": latest,
    }


def _timestamp_from_browser(value: Optional[float]) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(float(value) / 1000, timezone.utc).isoformat()


def insert_browser_capture(url: Optional[str], title: Optional[str], content: str, timestamp: Optional[float]) -> int:
    cleaned = normalize_text(content)[:3_000]
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO captures
            (timestamp, app_name, window_title, content, source_type, url, file_path)
            VALUES (?, ?, ?, ?, ?, ?, NULL)
            """,
            (_timestamp_from_browser(timestamp), "Browser", title, cleaned, "browser", url),
        )
        conn.commit()
        return int(cursor.lastrowid)


def refresh_index(backend: str, model: Optional[str], limit: Optional[int]) -> tuple[int, str]:
    with connect() as conn:
        rows = fetch_captures(conn, limit=limit, non_noise=True)
    artifact_path = build_index(
        rows,
        model_name=model or DEFAULT_EMBEDDER,
        backend=backend,
    )
    return len(rows), str(artifact_path)


def log_search_click(query: str, capture_id: int, rank: Optional[int]) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO search_clicks (query, capture_id, rank) VALUES (?, ?, ?)",
            (query, capture_id, rank),
        )
        conn.commit()


def update_capture_noise_label(capture_id: int, is_noise: Optional[int]) -> bool:
    if is_noise not in (None, 0, 1):
        raise ValueError("is_noise must be null, 0, or 1.")
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE captures SET is_noise = ? WHERE id = ?",
            (is_noise, capture_id),
        )
        conn.commit()
        return cursor.rowcount > 0


def _privacy_path():
    support = Path.home() / "Library" / "Application Support" / "MemoryOS"
    support.mkdir(parents=True, exist_ok=True)
    return support / "privacy.json"


DEFAULT_PRIVACY = PrivacySettings(
    blocked_apps=["1Password", "Keychain Access", "System Settings", "System Preferences"],
    blocked_domains=["bank", "chase.com", "wellsfargo.com", "capitalone.com", "paypal.com", "venmo.com"],
    excluded_path_fragments=["/Library/", "/.ssh/", "/.gnupg/", "/.Trash/"],
)


def get_privacy_settings() -> PrivacySettings:
    path = _privacy_path()
    if not path.exists():
        return DEFAULT_PRIVACY
    data = json.loads(path.read_text(encoding="utf-8"))
    return PrivacySettings(**data)


def save_privacy_settings(settings: PrivacySettings) -> PrivacySettings:
    path = _privacy_path()
    path.write_text(json.dumps(settings.dict(), indent=2), encoding="utf-8")
    return settings


def export_data() -> dict:
    with connect() as conn:
        captures = [
            dict(row)
            for row in conn.execute(f"SELECT {CAPTURE_COLUMNS} FROM captures ORDER BY timestamp DESC")
        ]
        sessions = [
            dict(row)
            for row in conn.execute(
                "SELECT id, app_name, start_time, end_time, duration_s FROM sessions ORDER BY start_time DESC"
            )
        ]
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "capture_count": len(captures),
        "session_count": len(sessions),
        "captures": captures,
        "sessions": sessions,
    }


def forget_captures(
    from_timestamp: Optional[str],
    to_timestamp: Optional[str],
    app_name: Optional[str],
    source_type: Optional[str],
) -> int:
    where = []
    params = []
    if from_timestamp:
        where.append("timestamp >= ?")
        params.append(from_timestamp)
    if to_timestamp:
        where.append("timestamp <= ?")
        params.append(to_timestamp)
    if app_name:
        where.append("app_name = ?")
        params.append(app_name)
    if source_type:
        where.append("source_type = ?")
        params.append(source_type)
    if not where:
        raise ValueError("At least one delete filter is required.")

    sql = "DELETE FROM captures WHERE " + " AND ".join(where)
    with connect() as conn:
        cursor = conn.execute(sql, params)
        conn.commit()
        return int(cursor.rowcount)
