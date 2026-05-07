from __future__ import annotations

import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Optional

from .config import PROJECT_ROOT

ML_ROOT = PROJECT_ROOT / "ml"
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from memoryos.config import database_path
from memoryos.db import CAPTURE_COLUMNS, connect, fetch_captures
from memoryos.features import normalize_text, result_snippet
from memoryos.index import (
    DEFAULT_EMBEDDER,
    FAISS_INDEX_PATH,
    FAISS_MAPPING_PATH,
    INDEX_ARTIFACT_PATH,
    SearchHit,
    build_index,
    index_backend,
    search_index,
)
from memoryos.reranker import rerank_hits

from .schemas import CaptureResult
from .schemas import CollectionSummary
from .schemas import CleanupResponse
from .schemas import EnterprisePolicy
from .schemas import PrivacySettings
from .schemas import StoragePolicy
from .schemas import TodoItem
from .time_query import TimeQuery, parse_capture_timestamp, parse_time_query, same_day_fallback_score, temporal_score, text_score


def row_to_capture_result(
    row: sqlite3.Row,
    score: Optional[float] = None,
    rank: Optional[int] = None,
    similarity_score: Optional[float] = None,
    rerank_score: Optional[float] = None,
) -> CaptureResult:
    content = str(row["content"] or "")
    return CaptureResult(
        id=int(row["id"]),
        score=score,
        similarity_score=similarity_score,
        rerank_score=rerank_score,
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
        is_pinned=int(row["is_pinned"] or 0),
    )


def _support_dir() -> Path:
    support = Path.home() / "Library" / "Application Support" / "MemoryOS"
    support.mkdir(parents=True, exist_ok=True)
    return support


def _path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _database_size_bytes() -> int:
    db_path = database_path()
    return sum(_path_size(Path(str(db_path) + suffix)) for suffix in ("", "-wal", "-shm"))


def _index_size_bytes() -> int:
    model_dir = PROJECT_ROOT / "ml" / "models"
    return _path_size(model_dir)


def _log_size_bytes() -> int:
    return _path_size(PROJECT_ROOT / ".logs")


def _protected_capture_ids(conn: sqlite3.Connection, policy: StoragePolicy) -> set[int]:
    protected: set[int] = set()
    protected.update(int(row["id"]) for row in conn.execute("SELECT id FROM captures WHERE is_pinned = 1"))
    if policy.protect_keep_labels:
        protected.update(int(row["id"]) for row in conn.execute("SELECT id FROM captures WHERE is_noise = 0"))
    if policy.keep_clicked:
        protected.update(int(row["capture_id"]) for row in conn.execute("SELECT DISTINCT capture_id FROM search_clicks"))
    return protected


def _storage_policy_path() -> Path:
    return _support_dir() / "storage_policy.json"


DEFAULT_STORAGE_POLICY = StoragePolicy(
    mode="balanced",
    auto_noise_enabled=True,
    min_text_chars=180,
    retention_days=30,
    noise_retention_hours=24,
    max_database_mb=1024,
    keep_clicked=True,
    protect_keep_labels=True,
    noise_apps=["Netflix", "Spotify", "TV", "Music", "Steam", "Games"],
    noise_domains=["netflix.com", "youtube.com", "youtu.be", "tiktok.com", "instagram.com", "spotify.com"],
)


def get_storage_policy() -> StoragePolicy:
    path = _storage_policy_path()
    if not path.exists():
        return DEFAULT_STORAGE_POLICY
    data = json.loads(path.read_text(encoding="utf-8"))
    defaults = DEFAULT_STORAGE_POLICY.dict()
    defaults.update(data)
    return StoragePolicy(**defaults)


def save_storage_policy(policy: StoragePolicy) -> StoragePolicy:
    presets = {
        "light": {"retention_days": 7, "noise_retention_hours": 12, "max_database_mb": 512},
        "balanced": {"retention_days": 30, "noise_retention_hours": 24, "max_database_mb": 1024},
        "deep": {"retention_days": 90, "noise_retention_hours": 72, "max_database_mb": 4096},
        "archive": {"retention_days": 3650, "noise_retention_hours": 168, "max_database_mb": 20_000},
    }
    if policy.mode in presets and policy.mode != get_storage_policy().mode:
        policy = policy.copy(update=presets[policy.mode])
    _storage_policy_path().write_text(json.dumps(policy.dict(), indent=2), encoding="utf-8")
    return policy


def _host_from_url(url: Optional[str]) -> str:
    if not url:
        return ""
    try:
        from urllib.parse import urlparse

        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def should_skip_capture(app_name: str, title: Optional[str], content: str, url: Optional[str], policy: StoragePolicy) -> bool:
    text = normalize_text(content)
    if len(text) < policy.min_text_chars:
        return True
    joined = " ".join([app_name or "", title or "", _host_from_url(url)]).lower()
    if any(item.lower() in joined for item in policy.noise_apps):
        return True
    return False


def auto_noise_label(app_name: str, title: Optional[str], content: str, url: Optional[str], policy: StoragePolicy) -> Optional[int]:
    if not policy.auto_noise_enabled:
        return None
    host = _host_from_url(url)
    joined = " ".join([app_name or "", title or "", host]).lower()
    if any(item.lower() in joined for item in policy.noise_apps):
        return 1
    if any(fragment.lower() in host for fragment in policy.noise_domains):
        return 1
    text = normalize_text(content)
    alpha_ratio = sum(char.isalpha() for char in text) / max(len(text), 1)
    if len(text) < policy.min_text_chars or alpha_ratio < 0.25:
        return 1
    return None


def search(query: str, top_k: int, candidate_k: int = 50) -> dict:
    started = time.perf_counter()
    time_query = parse_time_query(query)
    if not INDEX_ARTIFACT_PATH.exists() and time_query is None:
        raise FileNotFoundError("Search index is missing. Run /refresh-index or ml/train/build_index.py first.")
    with connect() as conn:
        rows = fetch_captures(conn, non_noise=True)
    rows_by_id = {int(row["id"]): row for row in rows}
    candidate_limit = max(top_k, candidate_k)

    if time_query is not None:
        hits = _time_aware_hits(query, rows, rows_by_id, time_query, candidate_limit)
        ranked_hits = [(hit, hit.score) for hit in hits[:top_k]]
        reranker_name = "time-aware"
        backend_name = index_backend() if INDEX_ARTIFACT_PATH.exists() else "missing"
        backend_name = f"{backend_name}+time"
    else:
        hits = search_index(query, rows_by_id, top_k=candidate_limit)
        ranked_hits, reranker_name = rerank_hits(query, hits)
        backend_name = index_backend()

    results = []
    for rank, (hit, rerank_score) in enumerate(ranked_hits[:top_k], start=1):
        results.append(
            row_to_capture_result(
                hit.row,
                score=rerank_score,
                rank=rank,
                similarity_score=hit.score,
                rerank_score=rerank_score,
            )
        )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return {
        "results": results,
        "candidate_count": len(hits),
        "elapsed_ms": round(elapsed_ms, 2),
        "index_backend": backend_name,
        "reranker": reranker_name,
    }


def _time_aware_hits(query: str, rows: list[sqlite3.Row], rows_by_id: dict[int, sqlite3.Row], time_query: TimeQuery, top_k: int) -> list[SearchHit]:
    search_text = time_query.cleaned_query
    index_scores: dict[int, float] = {}
    if search_text and INDEX_ARTIFACT_PATH.exists():
        for hit in search_index(search_text, rows_by_id, top_k=top_k):
            index_scores[hit.capture_id] = max(index_scores.get(hit.capture_id, 0.0), hit.score)

    hits = _collect_time_hits(rows, time_query, search_text, index_scores, fallback_to_day=False)
    if not hits and time_query.center_utc is not None:
        hits = _collect_time_hits(rows, time_query, search_text, index_scores, fallback_to_day=True)

    hits.sort(key=lambda hit: (hit.score, str(hit.row["timestamp"])), reverse=True)
    return [SearchHit(hit.capture_id, hit.score, rank, hit.row) for rank, hit in enumerate(hits, start=1)]


def _collect_time_hits(
    rows: list[sqlite3.Row],
    time_query: TimeQuery,
    search_text: str,
    index_scores: dict[int, float],
    fallback_to_day: bool,
) -> list[SearchHit]:
    hits = []
    for row in rows:
        captured_at = parse_capture_timestamp(str(row["timestamp"]))
        if captured_at is None:
            continue
        proximity = same_day_fallback_score(captured_at, time_query) if fallback_to_day else temporal_score(captured_at, time_query)
        if proximity <= 0:
            continue

        capture_id = int(row["id"])
        lexical = text_score(
            (
                row["app_name"],
                row["window_title"],
                row["content"],
                row["source_type"],
                row["url"],
                row["file_path"],
            ),
            search_text,
        )
        semantic = max(index_scores.get(capture_id, 0.0), lexical)
        score = (0.82 * proximity) + (0.18 * semantic if search_text else 0.0)
        hits.append(SearchHit(capture_id=capture_id, score=score, rank=0, row=row))
    return hits


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
        protected = len(_protected_capture_ids(conn, get_storage_policy()))

    return {
        "database_path": str(db_path),
        "total_captures": total,
        "indexed_available": INDEX_ARTIFACT_PATH.exists(),
        "counts_by_app": by_app,
        "counts_by_source_type": by_source,
        "noise_counts": noise_counts,
        "latest_capture_at": latest,
        "storage_bytes": _database_size_bytes() + _index_size_bytes() + _log_size_bytes(),
        "protected_captures": protected,
    }


def _timestamp_from_browser(value: Optional[float]) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(float(value) / 1000, timezone.utc).isoformat()


def insert_browser_capture(url: Optional[str], title: Optional[str], content: str, timestamp: Optional[float]) -> int:
    cleaned = normalize_text(content)[:3_000]
    policy = get_storage_policy()
    if should_skip_capture("Browser", title, cleaned, url, policy):
        return 0
    label = auto_noise_label("Browser", title, cleaned, url, policy)
    with connect() as conn:
        duplicate = conn.execute(
            """
            SELECT id FROM captures
            WHERE source_type = 'browser'
              AND COALESCE(url, '') = COALESCE(?, '')
              AND COALESCE(window_title, '') = COALESCE(?, '')
              AND content = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (url, title, cleaned),
        ).fetchone()
        if duplicate:
            return int(duplicate["id"])
        cursor = conn.execute(
            """
            INSERT INTO captures
            (timestamp, app_name, window_title, content, source_type, url, file_path, is_noise)
            VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
            """,
            (_timestamp_from_browser(timestamp), "Browser", title, cleaned, "browser", url, label),
        )
        conn.commit()
        return int(cursor.lastrowid)


def refresh_index(backend: str, model: Optional[str], limit: Optional[int]) -> tuple[int, str, str]:
    with connect() as conn:
        rows = fetch_captures(conn, limit=limit, non_noise=True)
    artifact_path = build_index(
        rows,
        model_name=model or DEFAULT_EMBEDDER,
        backend=backend,
    )
    return len(rows), str(artifact_path), index_backend()


def log_search_click(query: str, capture_id: int, rank: Optional[int], dwell_ms: Optional[int] = None) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO search_clicks (query, capture_id, rank, dwell_ms) VALUES (?, ?, ?, ?)",
            (query, capture_id, rank, dwell_ms),
        )
        conn.commit()


def open_capture(capture_id: int) -> str:
    with connect() as conn:
        row = conn.execute(
            f"SELECT {CAPTURE_COLUMNS} FROM captures WHERE id = ?",
            (capture_id,),
        ).fetchone()
    if row is None:
        raise ValueError("Capture not found.")

    target = row["url"] or row["file_path"]
    if not target:
        raise ValueError("Capture has no URL or file path to open.")

    subprocess.run(["open", str(target)], check=True)
    return str(target)


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


def update_capture_noise_labels(capture_ids: list[int], is_noise: Optional[int]) -> int:
    if is_noise not in (None, 0, 1):
        raise ValueError("is_noise must be null, 0, or 1.")
    unique_ids = sorted({int(capture_id) for capture_id in capture_ids})
    if not unique_ids:
        return 0
    placeholders = ",".join("?" for _ in unique_ids)
    with connect() as conn:
        cursor = conn.execute(
            f"UPDATE captures SET is_noise = ? WHERE id IN ({placeholders})",
            [is_noise, *unique_ids],
        )
        conn.commit()
        return int(cursor.rowcount)


def update_capture_pin(capture_id: int, is_pinned: bool) -> bool:
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE captures SET is_pinned = ? WHERE id = ?",
            (1 if is_pinned else 0, capture_id),
        )
        conn.commit()
        return cursor.rowcount > 0


COLLECTION_DEFINITIONS = [
    {
        "id": "pinned",
        "name": "Pinned",
        "description": "Memories the user explicitly pinned.",
        "where": "is_pinned = 1",
        "params": [],
    },
    {
        "id": "papers-research",
        "name": "Papers and Research",
        "description": "Papers, arXiv pages, lectures, and research notes.",
        "where": "(LOWER(COALESCE(url, '') || ' ' || COALESCE(window_title, '') || ' ' || content) LIKE ? OR LOWER(COALESCE(url, '') || ' ' || COALESCE(window_title, '') || ' ' || content) LIKE ? OR LOWER(COALESCE(url, '') || ' ' || COALESCE(window_title, '') || ' ' || content) LIKE ? OR LOWER(COALESCE(url, '') || ' ' || COALESCE(window_title, '') || ' ' || content) LIKE ?)",
        "params": ["%arxiv%", "%paper%", "%lecture%", "%research%"],
    },
    {
        "id": "coding-debugging",
        "name": "Coding and Debugging",
        "description": "Code, errors, training loops, traces, and implementation work.",
        "where": "(LOWER(COALESCE(window_title, '') || ' ' || content || ' ' || COALESCE(file_path, '')) LIKE ? OR LOWER(COALESCE(window_title, '') || ' ' || content || ' ' || COALESCE(file_path, '')) LIKE ? OR LOWER(COALESCE(window_title, '') || ' ' || content || ' ' || COALESCE(file_path, '')) LIKE ? OR LOWER(COALESCE(window_title, '') || ' ' || content || ' ' || COALESCE(file_path, '')) LIKE ?)",
        "params": ["%python%", "%debug%", "%traceback%", "%train%"],
    },
    {
        "id": "notes-documents",
        "name": "Notes and Documents",
        "description": "Local documents, Notion-style notes, PDFs, and markdown files.",
        "where": "(source_type = 'file' OR LOWER(app_name || ' ' || COALESCE(window_title, '') || ' ' || COALESCE(file_path, '')) LIKE ? OR LOWER(COALESCE(file_path, '')) LIKE ? OR LOWER(COALESCE(file_path, '')) LIKE ?)",
        "params": ["%notion%", "%.pdf%", "%.md%"],
    },
    {
        "id": "career-work",
        "name": "Career and Job Search",
        "description": "Resume, internship, LinkedIn, and application-related memories.",
        "where": "(LOWER(COALESCE(url, '') || ' ' || COALESCE(window_title, '') || ' ' || content) LIKE ? OR LOWER(COALESCE(url, '') || ' ' || COALESCE(window_title, '') || ' ' || content) LIKE ? OR LOWER(COALESCE(url, '') || ' ' || COALESCE(window_title, '') || ' ' || content) LIKE ? OR LOWER(COALESCE(url, '') || ' ' || COALESCE(window_title, '') || ' ' || content) LIKE ?)",
        "params": ["%resume%", "%linkedin%", "%internship%", "%application%"],
    },
]


def smart_collections(limit_per_collection: int = 5) -> list[CollectionSummary]:
    collections: list[CollectionSummary] = []
    with connect() as conn:
        for definition in COLLECTION_DEFINITIONS:
            where = f"({definition['where']}) AND (is_noise = 0 OR is_noise IS NULL)"
            params = list(definition["params"])
            count_row = conn.execute(
                f"SELECT COUNT(*) AS count, MAX(timestamp) AS latest FROM captures WHERE {where}",
                params,
            ).fetchone()
            count = int(count_row["count"] or 0)
            if count == 0:
                continue
            rows = conn.execute(
                f"SELECT {CAPTURE_COLUMNS} FROM captures WHERE {where} ORDER BY is_pinned DESC, timestamp DESC LIMIT ?",
                [*params, limit_per_collection],
            ).fetchall()
            collections.append(
                CollectionSummary(
                    id=str(definition["id"]),
                    name=str(definition["name"]),
                    description=str(definition["description"]),
                    count=count,
                    latest_capture_at=count_row["latest"],
                    captures=[row_to_capture_result(row) for row in rows],
                )
            )
    return collections


def weekly_digest() -> dict:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)
    start_iso = start.isoformat()
    now_iso = now.isoformat()
    with connect() as conn:
        capture_count = int(conn.execute("SELECT COUNT(*) AS count FROM captures WHERE timestamp >= ?", (start_iso,)).fetchone()["count"])
        keep_count = int(conn.execute("SELECT COUNT(*) AS count FROM captures WHERE timestamp >= ? AND is_noise = 0", (start_iso,)).fetchone()["count"])
        noise_count = int(conn.execute("SELECT COUNT(*) AS count FROM captures WHERE timestamp >= ? AND is_noise = 1", (start_iso,)).fetchone()["count"])
        pinned_count = int(conn.execute("SELECT COUNT(*) AS count FROM captures WHERE timestamp >= ? AND is_pinned = 1", (start_iso,)).fetchone()["count"])
        opened_count = int(conn.execute("SELECT COUNT(*) AS count FROM search_clicks WHERE clicked_at >= ?", (start_iso,)).fetchone()["count"])
        open_todo_count = int(conn.execute("SELECT COUNT(*) AS count FROM todos WHERE status = 'open'").fetchone()["count"])
        top_apps = [dict(row) for row in conn.execute(
            """
            SELECT app_name, COUNT(*) AS count
            FROM captures
            WHERE timestamp >= ?
            GROUP BY app_name
            ORDER BY count DESC
            LIMIT 8
            """,
            (start_iso,),
        )]
        top_sources = [dict(row) for row in conn.execute(
            """
            SELECT source_type, COUNT(*) AS count
            FROM captures
            WHERE timestamp >= ?
            GROUP BY source_type
            ORDER BY count DESC
            """,
            (start_iso,),
        )]
        pinned_rows = conn.execute(
            f"SELECT {CAPTURE_COLUMNS} FROM captures WHERE is_pinned = 1 ORDER BY timestamp DESC LIMIT 8"
        ).fetchall()
        opened_rows = conn.execute(
            """
            SELECT DISTINCT
              captures.id AS id,
              captures.timestamp AS timestamp,
              captures.app_name AS app_name,
              captures.window_title AS window_title,
              captures.content AS content,
              captures.source_type AS source_type,
              captures.url AS url,
              captures.file_path AS file_path,
              captures.is_noise AS is_noise,
              captures.is_pinned AS is_pinned
            FROM captures
            JOIN search_clicks ON search_clicks.capture_id = captures.id
            WHERE search_clicks.clicked_at >= ?
            ORDER BY search_clicks.clicked_at DESC
            LIMIT 8
            """,
            (start_iso,),
        ).fetchall()
    return {
        "from_timestamp": start_iso,
        "to_timestamp": now_iso,
        "capture_count": capture_count,
        "keep_count": keep_count,
        "noise_count": noise_count,
        "pinned_count": pinned_count,
        "opened_count": opened_count,
        "open_todo_count": open_todo_count,
        "top_apps": top_apps,
        "top_sources": top_sources,
        "collections": smart_collections(limit_per_collection=3),
        "pinned_captures": [row_to_capture_result(row) for row in pinned_rows],
        "opened_captures": [row_to_capture_result(row) for row in opened_rows],
    }


def row_to_todo(row: sqlite3.Row) -> TodoItem:
    return TodoItem(
        id=int(row["id"]),
        title=str(row["title"]),
        notes=row["notes"],
        status=str(row["status"]),
        priority=int(row["priority"]),
        due_at=row["due_at"],
        source_capture_id=row["source_capture_id"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def list_todos(status: Optional[str] = None) -> list[TodoItem]:
    where = []
    params: list[object] = []
    if status:
        where.append("status = ?")
        params.append(status)
    sql = "SELECT * FROM todos"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY status ASC, priority ASC, COALESCE(due_at, '9999-12-31') ASC, created_at DESC"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_todo(row) for row in rows]


def create_todo(
    title: str,
    notes: Optional[str],
    priority: int,
    due_at: Optional[str],
    source_capture_id: Optional[int],
) -> TodoItem:
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO todos (title, notes, priority, due_at, source_capture_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (title.strip(), notes, priority, due_at, source_capture_id, now, now),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM todos WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return row_to_todo(row)


def update_todo(todo_id: int, **updates) -> Optional[TodoItem]:
    allowed = ["title", "notes", "status", "priority", "due_at", "source_capture_id"]
    values = {key: value for key, value in updates.items() if key in allowed and value is not None}
    if "status" in values and values["status"] not in {"open", "done"}:
        raise ValueError("status must be open or done.")
    if not values:
        with connect() as conn:
            row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
        return row_to_todo(row) if row else None
    values["updated_at"] = datetime.now(timezone.utc).isoformat()
    assignments = ", ".join(f"{key} = ?" for key in values)
    params = [*values.values(), todo_id]
    with connect() as conn:
        conn.execute(f"UPDATE todos SET {assignments} WHERE id = ?", params)
        conn.commit()
        row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    return row_to_todo(row) if row else None


def delete_todo(todo_id: int) -> bool:
    with connect() as conn:
        cursor = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
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


def storage_stats() -> dict:
    policy = get_storage_policy()
    with connect() as conn:
        total = int(conn.execute("SELECT COUNT(*) AS count FROM captures").fetchone()["count"])
        noise = int(conn.execute("SELECT COUNT(*) AS count FROM captures WHERE is_noise = 1").fetchone()["count"])
        keep = int(conn.execute("SELECT COUNT(*) AS count FROM captures WHERE is_noise = 0").fetchone()["count"])
        oldest = conn.execute("SELECT MIN(timestamp) AS oldest FROM captures").fetchone()["oldest"]
        latest = conn.execute("SELECT MAX(timestamp) AS latest FROM captures").fetchone()["latest"]
        protected = len(_protected_capture_ids(conn, policy))

    db_size = _database_size_bytes()
    index_size = _index_size_bytes()
    log_size = _log_size_bytes()
    return {
        "database_bytes": db_size,
        "index_bytes": index_size,
        "log_bytes": log_size,
        "total_bytes": db_size + index_size + log_size,
        "total_captures": total,
        "noise_captures": noise,
        "keep_captures": keep,
        "protected_captures": protected,
        "oldest_capture_at": oldest,
        "latest_capture_at": latest,
        "policy": policy,
    }


def _delete_capture_ids(conn: sqlite3.Connection, ids: list[int]) -> int:
    if not ids:
        return 0
    placeholders = ",".join("?" for _ in ids)
    cursor = conn.execute(f"DELETE FROM captures WHERE id IN ({placeholders})", ids)
    return int(cursor.rowcount)


def _cleanup_duplicates(conn: sqlite3.Connection, protected: set[int]) -> int:
    rows = conn.execute(
        f"SELECT {CAPTURE_COLUMNS} FROM captures ORDER BY timestamp DESC, id DESC"
    ).fetchall()
    seen: set[tuple[str, str, str, str, str]] = set()
    duplicate_ids: list[int] = []
    for row in rows:
        capture_id = int(row["id"])
        key = (
            str(row["source_type"] or ""),
            str(row["app_name"] or ""),
            str(row["window_title"] or ""),
            str(row["url"] or row["file_path"] or ""),
            str(row["content"] or ""),
        )
        if key in seen and capture_id not in protected:
            duplicate_ids.append(capture_id)
        else:
            seen.add(key)
    return _delete_capture_ids(conn, duplicate_ids)


def _remove_index_artifacts() -> bool:
    removed = False
    for path in [INDEX_ARTIFACT_PATH, FAISS_INDEX_PATH, FAISS_MAPPING_PATH]:
        if path.exists():
            path.unlink()
            removed = True
    return removed


def _rotate_logs(max_bytes: int = 5_000_000) -> int:
    log_dir = PROJECT_ROOT / ".logs"
    if not log_dir.exists():
        return 0
    rotated = 0
    for path in log_dir.glob("*.log"):
        if path.stat().st_size <= max_bytes:
            continue
        rotated_path = path.with_suffix(path.suffix + ".1")
        rotated_path.unlink(missing_ok=True)
        path.rename(rotated_path)
        path.write_text("", encoding="utf-8")
        rotated += 1
    return rotated


def cleanup_storage(
    delete_noise: bool = True,
    delete_duplicates: bool = True,
    apply_retention: bool = True,
    enforce_size_cap: bool = True,
    rotate_logs: bool = True,
    rebuild_index: bool = False,
) -> CleanupResponse:
    policy = get_storage_policy()
    before_size = _database_size_bytes() + _index_size_bytes() + _log_size_bytes()
    deleted_noise = 0
    deleted_old = 0
    deleted_duplicates = 0
    deleted_for_size = 0

    with connect() as conn:
        protected = _protected_capture_ids(conn, policy)
        if delete_noise:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=policy.noise_retention_hours)).isoformat()
            cursor = conn.execute("DELETE FROM captures WHERE is_noise = 1 AND timestamp < ?", (cutoff,))
            deleted_noise = int(cursor.rowcount)

        if apply_retention:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=policy.retention_days)).isoformat()
            rows = conn.execute("SELECT id FROM captures WHERE timestamp < ? ORDER BY timestamp ASC", (cutoff,)).fetchall()
            old_ids = [int(row["id"]) for row in rows if int(row["id"]) not in protected]
            deleted_old = _delete_capture_ids(conn, old_ids)

        if delete_duplicates:
            protected = _protected_capture_ids(conn, policy)
            deleted_duplicates = _cleanup_duplicates(conn, protected)

        conn.commit()

        if enforce_size_cap and _database_size_bytes() > policy.max_database_mb * 1_000_000:
            protected = _protected_capture_ids(conn, policy)
            rows = conn.execute("SELECT id FROM captures ORDER BY timestamp ASC").fetchall()
            size_ids = []
            for row in rows:
                capture_id = int(row["id"])
                if capture_id not in protected:
                    size_ids.append(capture_id)
                if len(size_ids) >= 500:
                    break
            deleted_for_size = _delete_capture_ids(conn, size_ids)
            conn.commit()

        deleted_total = deleted_noise + deleted_old + deleted_duplicates + deleted_for_size
        if deleted_total:
            conn.execute("VACUUM")

    logs_rotated = _rotate_logs() if rotate_logs else 0
    index_removed = False
    index_rebuilt = False
    if deleted_noise + deleted_old + deleted_duplicates + deleted_for_size:
        index_removed = _remove_index_artifacts()
        if rebuild_index:
            try:
                refresh_index("auto", None, None)
                index_rebuilt = True
            except Exception:
                index_rebuilt = False

    after_size = _database_size_bytes() + _index_size_bytes() + _log_size_bytes()
    return CleanupResponse(
        deleted_noise=deleted_noise,
        deleted_old=deleted_old,
        deleted_duplicates=deleted_duplicates,
        deleted_for_size=deleted_for_size,
        logs_rotated=logs_rotated,
        index_removed=index_removed,
        index_rebuilt=index_rebuilt,
        reclaimed_hint_bytes=max(0, before_size - after_size),
    )


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


def _json_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    try:
        parsed = json.loads(str(value))
    except Exception:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed if str(item).strip()]


def _json_text(items: list[str]) -> str:
    return json.dumps([item.strip() for item in items if item.strip()])


def _row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def _policy_from_row(row: sqlite3.Row) -> EnterprisePolicy:
    return EnterprisePolicy(
        id=int(row["id"]),
        organization_id=int(row["organization_id"]),
        name=str(row["name"]),
        capture_sources=_json_list(row["capture_sources"]),
        blocked_apps=_json_list(row["blocked_apps"]),
        blocked_domains=_json_list(row["blocked_domains"]),
        excluded_path_fragments=_json_list(row["excluded_path_fragments"]),
        redaction_terms=_json_list(row["redaction_terms"]),
        retention_days=int(row["retention_days"]),
        sync_enabled=bool(row["sync_enabled"]),
        updated_at=str(row["updated_at"]),
    )


def _default_enterprise_policy(organization_id: int) -> EnterprisePolicy:
    privacy = get_privacy_settings()
    return EnterprisePolicy(
        organization_id=organization_id,
        name="Default private-first Teams policy",
        capture_sources=["meetings", "docs", "tickets", "browser", "github", "local_files"],
        blocked_apps=privacy.blocked_apps,
        blocked_domains=privacy.blocked_domains,
        excluded_path_fragments=privacy.excluded_path_fragments,
        redaction_terms=["api key", "password", "secret", "token"],
        retention_days=90,
        sync_enabled=True,
    )


def _log_audit(
    conn: sqlite3.Connection,
    action: str,
    resource_type: str,
    resource_id: Optional[object] = None,
    actor_user_id: Optional[int] = None,
    details: Optional[dict[str, Any]] = None,
) -> sqlite3.Row:
    cursor = conn.execute(
        """
        INSERT INTO audit_events (actor_user_id, action, resource_type, resource_id, details)
        VALUES (?, ?, ?, ?, ?)
        """,
        (actor_user_id, action, resource_type, str(resource_id) if resource_id is not None else None, json.dumps(details or {})),
    )
    return conn.execute("SELECT * FROM audit_events WHERE id = ?", (cursor.lastrowid,)).fetchone()


def _audit_from_row(row: sqlite3.Row) -> dict[str, Any]:
    data = _row_dict(row)
    try:
        data["details"] = json.loads(data.get("details") or "{}")
    except Exception:
        data["details"] = {}
    return data


def _ensure_teams_seed(conn: sqlite3.Connection) -> int:
    org = conn.execute("SELECT id FROM organizations WHERE slug = ?", ("memoryos-demo",)).fetchone()
    if org:
        return int(org["id"])

    cursor = conn.execute(
        "INSERT INTO organizations (name, slug) VALUES (?, ?)",
        ("MemoryOS Demo Enterprise", "memoryos-demo"),
    )
    organization_id = int(cursor.lastrowid)
    user_cursor = conn.execute(
        """
        INSERT INTO users (organization_id, email, name, role)
        VALUES (?, ?, ?, ?)
        """,
        (organization_id, "admin@memoryos.local", "MemoryOS Admin", "org_admin"),
    )
    user_id = int(user_cursor.lastrowid)
    conn.execute(
        """
        INSERT INTO devices (user_id, device_name, trust_state, last_seen_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, "Local work computer", "trusted", datetime.now(timezone.utc).isoformat()),
    )
    team_cursor = conn.execute(
        """
        INSERT INTO teams (organization_id, name, description)
        VALUES (?, ?, ?)
        """,
        (organization_id, "Product Team", "Default team workspace for shared MemoryOS project context."),
    )
    team_id = int(team_cursor.lastrowid)
    conn.execute("INSERT INTO team_memberships (team_id, user_id, role) VALUES (?, ?, ?)", (team_id, user_id, "owner"))
    project_cursor = conn.execute(
        """
        INSERT INTO projects (team_id, name, description)
        VALUES (?, ?, ?)
        """,
        (team_id, "MemoryOS Teams", "Enterprise memory and agent-context rollout."),
    )
    project_id = int(project_cursor.lastrowid)
    conn.execute(
        "INSERT INTO project_memberships (project_id, user_id, role) VALUES (?, ?, ?)",
        (project_id, user_id, "owner"),
    )
    policy = _default_enterprise_policy(organization_id)
    conn.execute(
        """
        INSERT INTO enterprise_policies
        (organization_id, name, capture_sources, blocked_apps, blocked_domains, excluded_path_fragments, redaction_terms, retention_days, sync_enabled, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            organization_id,
            policy.name,
            _json_text(policy.capture_sources),
            _json_text(policy.blocked_apps),
            _json_text(policy.blocked_domains),
            _json_text(policy.excluded_path_fragments),
            _json_text(policy.redaction_terms),
            policy.retention_days,
            1 if policy.sync_enabled else 0,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.execute(
        """
        INSERT INTO agent_access_grants
        (agent_name, user_id, team_id, project_id, scope, can_read_private, can_read_shared)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("Hermes Agent", user_id, team_id, project_id, "project", 0, 1),
    )
    _log_audit(
        conn,
        action="teams_bootstrap",
        resource_type="organization",
        resource_id=organization_id,
        actor_user_id=user_id,
        details={"policy": "Employees own private work memory. Companies own shared project memory."},
    )
    conn.commit()
    return organization_id


def _active_policy(conn: sqlite3.Connection, organization_id: int) -> EnterprisePolicy:
    row = conn.execute("SELECT * FROM enterprise_policies WHERE organization_id = ?", (organization_id,)).fetchone()
    if row:
        return _policy_from_row(row)
    policy = _default_enterprise_policy(organization_id)
    save_enterprise_policy(policy)
    row = conn.execute("SELECT * FROM enterprise_policies WHERE organization_id = ?", (organization_id,)).fetchone()
    return _policy_from_row(row)


def save_enterprise_policy(policy: EnterprisePolicy) -> EnterprisePolicy:
    now = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        _ensure_teams_seed(conn)
        existing = conn.execute(
            "SELECT id FROM enterprise_policies WHERE organization_id = ?",
            (policy.organization_id,),
        ).fetchone()
        params = (
            policy.name,
            _json_text(policy.capture_sources),
            _json_text(policy.blocked_apps),
            _json_text(policy.blocked_domains),
            _json_text(policy.excluded_path_fragments),
            _json_text(policy.redaction_terms),
            int(policy.retention_days),
            1 if policy.sync_enabled else 0,
            now,
            policy.organization_id,
        )
        if existing:
            conn.execute(
                """
                UPDATE enterprise_policies
                SET name = ?, capture_sources = ?, blocked_apps = ?, blocked_domains = ?,
                    excluded_path_fragments = ?, redaction_terms = ?, retention_days = ?,
                    sync_enabled = ?, updated_at = ?
                WHERE organization_id = ?
                """,
                params,
            )
        else:
            conn.execute(
                """
                INSERT INTO enterprise_policies
                (name, capture_sources, blocked_apps, blocked_domains, excluded_path_fragments, redaction_terms, retention_days, sync_enabled, updated_at, organization_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params,
            )
        _log_audit(
            conn,
            action="enterprise_policy_updated",
            resource_type="enterprise_policy",
            resource_id=policy.organization_id,
            details={"retention_days": policy.retention_days, "sync_enabled": policy.sync_enabled},
        )
        conn.commit()
        row = conn.execute("SELECT * FROM enterprise_policies WHERE organization_id = ?", (policy.organization_id,)).fetchone()
    return _policy_from_row(row)


def _redact_text(text: str, policy: EnterprisePolicy) -> str:
    redacted = text
    for term in policy.redaction_terms:
        if not term:
            continue
        redacted = redacted.replace(term, "[redacted]")
        redacted = redacted.replace(term.title(), "[redacted]")
        redacted = redacted.replace(term.upper(), "[redacted]")
    return redacted


def _shared_memory_from_row(conn: sqlite3.Connection, row: sqlite3.Row, policy: EnterprisePolicy) -> dict[str, Any]:
    capture = conn.execute(f"SELECT {CAPTURE_COLUMNS} FROM captures WHERE id = ?", (row["capture_id"],)).fetchone()
    data = _row_dict(row)
    data["summary"] = _redact_text(str(data["summary"]), policy)
    data["capture"] = row_to_capture_result(capture).dict() if capture else None
    if data["capture"]:
        data["capture"]["content"] = _redact_text(str(data["capture"]["content"]), policy)
        data["capture"]["snippet"] = _redact_text(str(data["capture"]["snippet"]), policy)
    return data


def share_capture_to_team(
    capture_id: int,
    organization_id: int = 1,
    team_id: Optional[int] = None,
    project_id: Optional[int] = None,
    shared_by_user_id: Optional[int] = None,
    summary: Optional[str] = None,
) -> dict[str, Any]:
    with connect() as conn:
        organization_id = _ensure_teams_seed(conn) if organization_id == 1 else organization_id
        policy = _active_policy(conn, organization_id)
        if not policy.sync_enabled:
            raise ValueError("Team memory sync is disabled by enterprise policy.")
        capture = conn.execute(f"SELECT {CAPTURE_COLUMNS} FROM captures WHERE id = ?", (capture_id,)).fetchone()
        if capture is None:
            raise ValueError("Capture not found.")
        if int(capture["is_noise"] or 0) == 1:
            raise ValueError("Noise captures cannot be shared to team memory.")
        if team_id is None:
            team = conn.execute("SELECT id FROM teams WHERE organization_id = ? ORDER BY id LIMIT 1", (organization_id,)).fetchone()
            team_id = int(team["id"]) if team else None
        if project_id is None and team_id is not None:
            project = conn.execute("SELECT id FROM projects WHERE team_id = ? ORDER BY id LIMIT 1", (team_id,)).fetchone()
            project_id = int(project["id"]) if project else None
        if shared_by_user_id is None:
            user = conn.execute("SELECT id FROM users WHERE organization_id = ? ORDER BY id LIMIT 1", (organization_id,)).fetchone()
            shared_by_user_id = int(user["id"]) if user else None

        share_summary = summary or result_snippet(str(capture["content"] or ""))
        share_summary = _redact_text(share_summary[:2_000], policy)
        cursor = conn.execute(
            """
            INSERT INTO memory_shares
            (capture_id, organization_id, team_id, project_id, shared_by_user_id, share_state, summary)
            VALUES (?, ?, ?, ?, ?, 'shared', ?)
            """,
            (capture_id, organization_id, team_id, project_id, shared_by_user_id, share_summary),
        )
        share_id = int(cursor.lastrowid)
        _log_audit(
            conn,
            action="memory_shared",
            resource_type="memory_share",
            resource_id=share_id,
            actor_user_id=shared_by_user_id,
            details={"capture_id": capture_id, "team_id": team_id, "project_id": project_id},
        )
        conn.commit()
        row = conn.execute("SELECT * FROM memory_shares WHERE id = ?", (share_id,)).fetchone()
    with connect() as read_conn:
        return _shared_memory_from_row(read_conn, row, policy)


def teams_overview() -> dict[str, Any]:
    with connect() as conn:
        organization_id = _ensure_teams_seed(conn)
        policy = _active_policy(conn, organization_id)
        organization = _row_dict(conn.execute("SELECT * FROM organizations WHERE id = ?", (organization_id,)).fetchone())
        users = [_row_dict(row) for row in conn.execute("SELECT * FROM users WHERE organization_id = ? ORDER BY id", (organization_id,))]
        devices = [
            _row_dict(row)
            for row in conn.execute(
                """
                SELECT devices.*
                FROM devices
                JOIN users ON users.id = devices.user_id
                WHERE users.organization_id = ?
                ORDER BY devices.id
                """,
                (organization_id,),
            )
        ]
        teams = [
            {
                **_row_dict(row),
                "member_count": int(row["member_count"] or 0),
            }
            for row in conn.execute(
                """
                SELECT teams.*, COUNT(team_memberships.id) AS member_count
                FROM teams
                LEFT JOIN team_memberships ON team_memberships.team_id = teams.id
                WHERE teams.organization_id = ?
                GROUP BY teams.id
                ORDER BY teams.id
                """,
                (organization_id,),
            )
        ]
        projects = [
            {
                **_row_dict(row),
                "member_count": int(row["member_count"] or 0),
            }
            for row in conn.execute(
                """
                SELECT projects.*, COUNT(project_memberships.id) AS member_count
                FROM projects
                LEFT JOIN project_memberships ON project_memberships.project_id = projects.id
                JOIN teams ON teams.id = projects.team_id
                WHERE teams.organization_id = ?
                GROUP BY projects.id
                ORDER BY projects.id
                """,
                (organization_id,),
            )
        ]
        share_rows = conn.execute(
            """
            SELECT * FROM memory_shares
            WHERE organization_id = ? AND share_state = 'shared'
            ORDER BY created_at DESC
            LIMIT 25
            """,
            (organization_id,),
        ).fetchall()
        shared_memories = [_shared_memory_from_row(conn, row, policy) for row in share_rows]
        audit_events = [
            _audit_from_row(row)
            for row in conn.execute(
                "SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 25",
            )
        ]
    return {
        "organization": organization,
        "users": users,
        "devices": devices,
        "teams": teams,
        "projects": projects,
        "policy": policy,
        "shared_memories": shared_memories,
        "audit_events": audit_events,
        "status": {
            "personal_memory_local": True,
            "enterprise_policy_service": True,
            "identity_and_access": True,
            "team_memory_sync": True,
            "hermes_agent_connector": True,
            "admin_dashboard": True,
            "audit_logs": True,
            "redaction": True,
            "sso_provider": "local demo identity; external SSO not connected",
            "encryption_scope": "local SQLite/filesystem plus optional API key; managed enterprise KMS not connected",
            "device_trust": "device registration table with trusted/pending/revoked states",
        },
    }


def agent_context(
    agent_name: str,
    user_id: Optional[int],
    team_id: Optional[int],
    project_id: Optional[int],
    query: Optional[str],
    include_private: bool,
    top_k: int,
) -> dict[str, Any]:
    with connect() as conn:
        organization_id = _ensure_teams_seed(conn)
        policy = _active_policy(conn, organization_id)
        shared_where = ["memory_shares.organization_id = ?", "memory_shares.share_state = 'shared'"]
        params: list[object] = [organization_id]
        if team_id is not None:
            shared_where.append("memory_shares.team_id = ?")
            params.append(team_id)
        if project_id is not None:
            shared_where.append("memory_shares.project_id = ?")
            params.append(project_id)
        if query:
            shared_where.append("(LOWER(memory_shares.summary) LIKE ? OR LOWER(captures.content) LIKE ?)")
            needle = f"%{query.lower()}%"
            params.extend([needle, needle])
        share_rows = conn.execute(
            f"""
            SELECT memory_shares.*
            FROM memory_shares
            JOIN captures ON captures.id = memory_shares.capture_id
            WHERE {' AND '.join(shared_where)}
            ORDER BY memory_shares.created_at DESC
            LIMIT ?
            """,
            [*params, top_k],
        ).fetchall()
        shared_memories = [_shared_memory_from_row(conn, row, policy) for row in share_rows]

        private_recent: list[CaptureResult] = []
        if include_private:
            rows = fetch_captures(conn, limit=top_k, non_noise=True)
            private_recent = [row_to_capture_result(row) for row in rows]
            for capture in private_recent:
                capture.content = _redact_text(capture.content, policy)
                capture.snippet = _redact_text(capture.snippet, policy)

        audit = _log_audit(
            conn,
            action="agent_context_read",
            resource_type="agent_context",
            resource_id=agent_name,
            actor_user_id=user_id,
            details={
                "team_id": team_id,
                "project_id": project_id,
                "include_private": include_private,
                "query": query,
                "shared_count": len(shared_memories),
            },
        )
        conn.commit()
    return {
        "agent_name": agent_name,
        "policy": policy,
        "private_recent": private_recent,
        "shared_memories": shared_memories,
        "audit_event": _audit_from_row(audit),
        "note": "Hermes Agent context is policy-bound. Shared memory is available by default; private recent memory is only returned when include_private is true.",
    }
