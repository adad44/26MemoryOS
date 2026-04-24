from __future__ import annotations

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from .config import load_settings
from .schemas import (
    BrowserCaptureRequest,
    ExportResponse,
    ForgetRequest,
    ForgetResponse,
    HealthResponse,
    NoiseLabelRequest,
    PrivacySettings,
    RecentResponse,
    RefreshRequest,
    RefreshResponse,
    SearchRequest,
    SearchResponse,
    StatsResponse,
)
from .security import require_api_key
from .service import (
    insert_browser_capture,
    export_data,
    forget_captures,
    get_privacy_settings,
    log_search_click,
    recent,
    refresh_index,
    save_privacy_settings,
    search,
    stats,
    update_capture_noise_label,
)


settings = load_settings()

app = FastAPI(
    title="MemoryOS Backend",
    version="0.1.0",
    description="Local FastAPI service for MemoryOS search, stats, and capture ingest.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-MemoryOS-API-Key"],
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(ok=True, api_key_enabled=settings.api_key_enabled)


@app.post("/search", response_model=SearchResponse, dependencies=[Depends(require_api_key)])
def search_endpoint(request: SearchRequest) -> SearchResponse:
    try:
        results = search(request.query, request.top_k)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return SearchResponse(query=request.query, count=len(results), results=results)


@app.get("/recent", response_model=RecentResponse, dependencies=[Depends(require_api_key)])
def recent_endpoint(
    limit: int = Query(default=50, ge=1, le=500),
    app_name: Optional[str] = None,
    source_type: Optional[str] = None,
) -> RecentResponse:
    results = recent(limit=limit, app_name=app_name, source_type=source_type)
    return RecentResponse(count=len(results), results=results)


@app.get("/stats", response_model=StatsResponse, dependencies=[Depends(require_api_key)])
def stats_endpoint() -> StatsResponse:
    return StatsResponse(**stats())


@app.post("/refresh-index", response_model=RefreshResponse, dependencies=[Depends(require_api_key)])
def refresh_index_endpoint(request: RefreshRequest) -> RefreshResponse:
    if request.backend not in {"auto", "sentence", "tfidf"}:
        raise HTTPException(status_code=422, detail="backend must be one of: auto, sentence, tfidf")
    try:
        count, artifact_path = refresh_index(
            backend=request.backend,
            model=request.model,
            limit=request.limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RefreshResponse(indexed_count=count, artifact_path=artifact_path)


@app.post("/capture/browser", dependencies=[Depends(require_api_key)])
def capture_browser_endpoint(request: BrowserCaptureRequest) -> Response:
    insert_browser_capture(
        url=request.url,
        title=request.title,
        content=request.content,
        timestamp=request.timestamp,
    )
    return Response(status_code=204)


@app.post("/click", dependencies=[Depends(require_api_key)])
def click_endpoint(query: str, capture_id: int, rank: Optional[int] = None) -> Response:
    log_search_click(query=query, capture_id=capture_id, rank=rank)
    return Response(status_code=204)


@app.patch("/captures/{capture_id}/noise", dependencies=[Depends(require_api_key)])
def label_capture_endpoint(capture_id: int, request: NoiseLabelRequest) -> Response:
    try:
        found = update_capture_noise_label(capture_id, request.is_noise)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not found:
        raise HTTPException(status_code=404, detail="Capture not found.")
    return Response(status_code=204)


@app.get("/privacy", response_model=PrivacySettings, dependencies=[Depends(require_api_key)])
def privacy_endpoint() -> PrivacySettings:
    return get_privacy_settings()


@app.put("/privacy", response_model=PrivacySettings, dependencies=[Depends(require_api_key)])
def update_privacy_endpoint(request: PrivacySettings) -> PrivacySettings:
    return save_privacy_settings(request)


@app.get("/export", response_model=ExportResponse, dependencies=[Depends(require_api_key)])
def export_endpoint() -> ExportResponse:
    return ExportResponse(**export_data())


@app.post("/forget", response_model=ForgetResponse, dependencies=[Depends(require_api_key)])
def forget_endpoint(request: ForgetRequest) -> ForgetResponse:
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Set confirm=true before deleting captures.")
    try:
        deleted = forget_captures(
            from_timestamp=request.from_timestamp,
            to_timestamp=request.to_timestamp,
            app_name=request.app_name,
            source_type=request.source_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ForgetResponse(deleted_count=deleted)


def run() -> None:
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
