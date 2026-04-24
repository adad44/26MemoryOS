from __future__ import annotations

from typing import Optional

from fastapi import Header, HTTPException, status

from .config import load_settings


settings = load_settings()


def require_api_key(x_memoryos_api_key: Optional[str] = Header(default=None)) -> None:
    if not settings.api_key_enabled:
        return
    if x_memoryos_api_key == settings.api_key:
        return
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid MemoryOS API key.",
    )
