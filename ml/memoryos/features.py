from __future__ import annotations

import re
import sqlite3
from typing import Iterable, List


WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: object) -> str:
    return WHITESPACE_RE.sub(" ", str(value or "")).strip()


def capture_document(row: sqlite3.Row) -> str:
    app = normalize_text(row["app_name"])
    title = normalize_text(row["window_title"])
    source = normalize_text(row["source_type"])
    content = normalize_text(row["content"])
    return f"app:{app} source:{source} title:{title}\n{content}"


def capture_documents(rows: Iterable[sqlite3.Row]) -> List[str]:
    return [capture_document(row) for row in rows]


def result_snippet(content: str, max_chars: int = 260) -> str:
    text = normalize_text(content)
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."
