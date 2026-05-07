from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1_000)
    top_k: int = Field(default=10, ge=1, le=50)
    candidate_k: int = Field(default=50, ge=1, le=200)


class CaptureResult(BaseModel):
    id: int
    score: Optional[float] = None
    similarity_score: Optional[float] = None
    rerank_score: Optional[float] = None
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
    is_pinned: int = 0


class SearchResponse(BaseModel):
    query: str
    count: int
    candidate_count: int = 0
    elapsed_ms: float = 0.0
    index_backend: str = "unknown"
    reranker: str = "none"
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
    storage_bytes: Optional[int] = None
    protected_captures: Optional[int] = None


class BrowserCaptureRequest(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    content: str = Field(min_length=20, max_length=20_000)
    timestamp: Optional[float] = None


class NoiseLabelRequest(BaseModel):
    is_noise: Optional[int] = Field(default=None)


class BulkNoiseLabelRequest(BaseModel):
    capture_ids: List[int] = Field(min_length=1, max_length=1_000)
    is_noise: Optional[int] = Field(default=None)


class BulkNoiseLabelResponse(BaseModel):
    updated_count: int


class PinRequest(BaseModel):
    is_pinned: bool


class CollectionSummary(BaseModel):
    id: str
    name: str
    description: str
    count: int
    latest_capture_at: Optional[str] = None
    captures: List[CaptureResult] = Field(default_factory=list)


class CollectionsResponse(BaseModel):
    count: int
    collections: List[CollectionSummary]


class WeeklyDigestResponse(BaseModel):
    from_timestamp: str
    to_timestamp: str
    capture_count: int
    keep_count: int
    noise_count: int
    pinned_count: int
    opened_count: int
    open_todo_count: int
    top_apps: List[Dict[str, Any]]
    top_sources: List[Dict[str, Any]]
    collections: List[CollectionSummary]
    pinned_captures: List[CaptureResult]
    opened_captures: List[CaptureResult]


class TodoItem(BaseModel):
    id: int
    title: str
    notes: Optional[str] = None
    status: str
    priority: int
    due_at: Optional[str] = None
    source_capture_id: Optional[int] = None
    created_at: str
    updated_at: str


class TodoListResponse(BaseModel):
    count: int
    todos: List[TodoItem]


class TodoCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    notes: Optional[str] = Field(default=None, max_length=2_000)
    priority: int = Field(default=2, ge=1, le=3)
    due_at: Optional[str] = None
    source_capture_id: Optional[int] = None


class TodoUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    notes: Optional[str] = Field(default=None, max_length=2_000)
    status: Optional[str] = None
    priority: Optional[int] = Field(default=None, ge=1, le=3)
    due_at: Optional[str] = None
    source_capture_id: Optional[int] = None


class UserModelResponse(BaseModel):
    status: str = "ready"
    summary: str = ""
    top_interests: List[str] = Field(default_factory=list)
    active_projects: List[str] = Field(default_factory=list)
    work_rhythm: str = ""
    knowledge_gaps: List[str] = Field(default_factory=list)
    generated_at: Optional[str] = None
    message: Optional[str] = None


class BeliefItem(BaseModel):
    topic: str
    belief_type: str
    summary: str
    confidence: float
    depth: Optional[str] = None
    times_reinforced: int
    last_updated: Optional[str] = None


class BeliefListResponse(BaseModel):
    count: int
    beliefs: List[BeliefItem]


class RunAbstractionResponse(BaseModel):
    status: str
    message: str


class AbstractionRunItem(BaseModel):
    id: int
    started_at: str
    finished_at: Optional[str] = None
    captures_read: int
    beliefs_written: int
    beliefs_updated: int
    status: str
    error: Optional[str] = None


class AbstractionRunsResponse(BaseModel):
    count: int
    runs: List[AbstractionRunItem]


class AbstractionStatusResponse(BaseModel):
    ollama_running: bool
    model: str
    running: bool


class PrivacySettings(BaseModel):
    blocked_apps: List[str] = []
    blocked_domains: List[str] = []
    excluded_path_fragments: List[str] = []


class StoragePolicy(BaseModel):
    mode: str = "balanced"
    auto_noise_enabled: bool = True
    min_text_chars: int = Field(default=180, ge=20, le=2_000)
    retention_days: int = Field(default=30, ge=1, le=3650)
    noise_retention_hours: int = Field(default=24, ge=1, le=8760)
    max_database_mb: int = Field(default=1024, ge=10, le=100_000)
    keep_clicked: bool = True
    protect_keep_labels: bool = True
    noise_apps: List[str] = []
    noise_domains: List[str] = []


class StorageStatsResponse(BaseModel):
    database_bytes: int
    index_bytes: int
    log_bytes: int
    total_bytes: int
    total_captures: int
    noise_captures: int
    keep_captures: int
    protected_captures: int
    oldest_capture_at: Optional[str]
    latest_capture_at: Optional[str]
    policy: StoragePolicy


class CleanupRequest(BaseModel):
    delete_noise: bool = True
    delete_duplicates: bool = True
    apply_retention: bool = True
    enforce_size_cap: bool = True
    rotate_logs: bool = True
    rebuild_index: bool = False
    confirm: bool = False


class CleanupResponse(BaseModel):
    deleted_noise: int
    deleted_old: int
    deleted_duplicates: int
    deleted_for_size: int
    logs_rotated: int
    index_removed: bool
    index_rebuilt: bool
    reclaimed_hint_bytes: int


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
    backend: str = "unknown"


class OpenCaptureRequest(BaseModel):
    capture_id: int


class OpenCaptureResponse(BaseModel):
    opened: bool
    target: str


class HealthResponse(BaseModel):
    ok: bool
    api_key_enabled: bool


class EnterprisePolicy(BaseModel):
    id: Optional[int] = None
    organization_id: int = 1
    name: str = Field(default="Default enterprise policy", min_length=1, max_length=120)
    capture_sources: List[str] = Field(default_factory=lambda: ["meeting", "docs", "tickets", "browser", "github", "local_files"])
    blocked_apps: List[str] = Field(default_factory=list)
    blocked_domains: List[str] = Field(default_factory=list)
    excluded_path_fragments: List[str] = Field(default_factory=list)
    redaction_terms: List[str] = Field(default_factory=list)
    retention_days: int = Field(default=90, ge=1, le=3650)
    sync_enabled: bool = True
    updated_at: Optional[str] = None


class OrganizationItem(BaseModel):
    id: int
    name: str
    slug: str
    created_at: str


class UserItem(BaseModel):
    id: int
    organization_id: int
    email: str
    name: str
    role: str
    created_at: str


class DeviceItem(BaseModel):
    id: int
    user_id: int
    device_name: str
    trust_state: str
    registered_at: str
    last_seen_at: Optional[str] = None


class TeamItem(BaseModel):
    id: int
    organization_id: int
    name: str
    description: Optional[str] = None
    member_count: int = 0
    created_at: str


class ProjectItem(BaseModel):
    id: int
    team_id: int
    name: str
    description: Optional[str] = None
    status: str
    member_count: int = 0
    created_at: str


class SharedMemoryItem(BaseModel):
    id: int
    capture_id: int
    organization_id: int
    team_id: Optional[int] = None
    project_id: Optional[int] = None
    shared_by_user_id: Optional[int] = None
    share_state: str
    summary: str
    created_at: str
    capture: Optional[CaptureResult] = None


class AuditEventItem(BaseModel):
    id: int
    actor_user_id: Optional[int] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    created_at: str


class EnterpriseStatus(BaseModel):
    personal_memory_local: bool
    enterprise_policy_service: bool
    identity_and_access: bool
    team_memory_sync: bool
    hermes_agent_connector: bool
    admin_dashboard: bool
    audit_logs: bool
    redaction: bool
    sso_provider: str
    encryption_scope: str
    device_trust: str


class TeamsOverviewResponse(BaseModel):
    organization: OrganizationItem
    users: List[UserItem]
    devices: List[DeviceItem]
    teams: List[TeamItem]
    projects: List[ProjectItem]
    policy: EnterprisePolicy
    shared_memories: List[SharedMemoryItem]
    audit_events: List[AuditEventItem]
    status: EnterpriseStatus


class ShareMemoryRequest(BaseModel):
    capture_id: int
    organization_id: int = 1
    team_id: Optional[int] = None
    project_id: Optional[int] = None
    shared_by_user_id: Optional[int] = None
    summary: Optional[str] = Field(default=None, max_length=2_000)


class AgentContextRequest(BaseModel):
    agent_name: str = Field(default="Hermes Agent", min_length=1, max_length=120)
    user_id: Optional[int] = None
    team_id: Optional[int] = None
    project_id: Optional[int] = None
    query: Optional[str] = Field(default=None, max_length=1_000)
    include_private: bool = False
    top_k: int = Field(default=8, ge=1, le=25)


class AgentContextResponse(BaseModel):
    agent_name: str
    policy: EnterprisePolicy
    private_recent: List[CaptureResult]
    shared_memories: List[SharedMemoryItem]
    audit_event: AuditEventItem
    note: str
