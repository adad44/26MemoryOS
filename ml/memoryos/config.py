from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ML_ROOT = PROJECT_ROOT / "ml"
MODEL_DIR = ML_ROOT / "models"
PROCESSED_DIR = ML_ROOT / "data" / "processed"


def database_path() -> Path:
    override = os.environ.get("MEMORYOS_DB")
    if override:
        return Path(override).expanduser()
    return Path("~/Library/Application Support/MemoryOS/memoryos.db").expanduser()


def ensure_dirs() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
