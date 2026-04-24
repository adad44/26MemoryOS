from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1_000)
    top_k: int = Field(default=10, ge=1, le=50)


class CaptureResult(BaseModel):
    id: int
    score: Optional[float] = None
    rank: Optional[int] = None
    timestamp: str
    app_name: str
    window_title: Optional[str] = None
    content: str
    snippet: str
    source_type: str
    url: Optional[str] = None
    file_path: Optional[str] = None
    is_noise: Optional[int] = None


class SearchResponse(BaseModel):
    query: str
    count: int
    results: List[CaptureResult]


class RecentResponse(BaseModel):
    count: int
    results: List[CaptureResult]


class StatsResponse(BaseModel):
    database_path: str
    total_captures: int
    indexed_available: bool
    counts_by_app: List[Dict[str, Any]]
    counts_by_source_type: List[Dict[str, Any]]
    noise_counts: List[Dict[str, Any]]
    latest_capture_at: Optional[str]


class BrowserCaptureRequest(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    content: str = Field(min_length=20, max_length=20_000)
    timestamp: Optional[float] = None


class NoiseLabelRequest(BaseModel):
    is_noise: Optional[int] = Field(default=None)


class PrivacySettings(BaseModel):
    blocked_apps: List[str] = []
    blocked_domains: List[str] = []
    excluded_path_fragments: List[str] = []


class ForgetRequest(BaseModel):
    from_timestamp: Optional[str] = None
    to_timestamp: Optional[str] = None
    app_name: Optional[str] = None
    source_type: Optional[str] = None
    confirm: bool = False


class ForgetResponse(BaseModel):
    deleted_count: int


class ExportResponse(BaseModel):
    exported_at: str
    capture_count: int
    session_count: int
    captures: List[Dict[str, Any]]
    sessions: List[Dict[str, Any]]


class RefreshRequest(BaseModel):
    backend: str = "auto"
    model: Optional[str] = None
    limit: Optional[int] = Field(default=None, ge=1)


class RefreshResponse(BaseModel):
    indexed_count: int
    artifact_path: str


class HealthResponse(BaseModel):
    ok: bool
    api_key_enabled: bool
