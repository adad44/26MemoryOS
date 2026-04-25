# Phase 3 Search Backend

Phase 3 adds the local FastAPI service that serves MemoryOS search, stats, recent captures, browser ingest, click logging, and index refresh.

## Run

```sh
scripts/run_backend.sh
```

Default URL:

```text
http://127.0.0.1:8765
```

The backend intentionally binds to localhost by default.

## Optional API Key

Enable API-key auth:

```sh
MEMORYOS_API_KEY="dev-secret" scripts/run_backend.sh
```

Then send:

```text
X-MemoryOS-API-Key: dev-secret
```

If `MEMORYOS_API_KEY` is unset, endpoints are open to local callers.

## Endpoints

### Health

```sh
curl http://127.0.0.1:8765/health
```

### Stats

```sh
curl http://127.0.0.1:8765/stats
```

Returns capture totals, app/source breakdowns, noise-label counts, latest capture timestamp, and whether an index artifact exists.

### Recent

```sh
curl "http://127.0.0.1:8765/recent?limit=25"
```

Optional filters:

```text
app_name=Safari
source_type=browser
```

### Refresh Index

Build or rebuild the Phase 2 search index:

```sh
curl -X POST http://127.0.0.1:8765/refresh-index \
  -H "Content-Type: application/json" \
  -d '{"backend":"tfidf"}'
```

Use the full semantic path after installing `ml/requirements.txt`:

```sh
curl -X POST http://127.0.0.1:8765/refresh-index \
  -H "Content-Type: application/json" \
  -d '{"backend":"sentence","model":"ml/models/memoryos-embedder"}'
```

### Search

```sh
curl -X POST http://127.0.0.1:8765/search \
  -H "Content-Type: application/json" \
  -d '{"query":"python traceback embedding search","top_k":10}'
```

If the index has not been built yet, this returns `409` with instructions to refresh the index.

Search retrieves up to 50 candidates by default, re-ranks them with the temporal re-ranker, and returns the requested top results with index backend, candidate count, and measured latency metadata. If a trained re-ranker artifact exists, it is used; otherwise MemoryOS uses a live heuristic based on similarity, recency, and historical dwell time.

### Browser Capture

The Chrome extension posts here:

```text
POST /capture/browser
```

Request body:

```json
{
  "url": "https://example.com",
  "title": "Example",
  "content": "Visible page text...",
  "timestamp": 1777017600000
}
```

### Click Logging

Phase 4 will use this endpoint to collect labels for the re-ranker:

```sh
curl -X POST "http://127.0.0.1:8765/click?query=python&capture_id=1&rank=1&dwell_ms=4200"
```

Clicks are positive labels for future re-ranker training. `dwell_ms` records how long the result was visible before the user opened it.

### Open Capture

Open a captured URL or file through the local macOS `open` command:

```sh
curl -X POST http://127.0.0.1:8765/open \
  -H "Content-Type: application/json" \
  -d '{"capture_id":1}'
```

### Noise Labeling

```sh
curl -X PATCH http://127.0.0.1:8765/captures/1/noise \
  -H "Content-Type: application/json" \
  -d '{"is_noise":0}'
```

Bulk label captures:

```sh
curl -X PATCH http://127.0.0.1:8765/captures/noise/bulk \
  -H "Content-Type: application/json" \
  -d '{"capture_ids":[1,2,3],"is_noise":0}'
```

### Privacy Settings

```sh
curl http://127.0.0.1:8765/privacy
```

```sh
curl -X PUT http://127.0.0.1:8765/privacy \
  -H "Content-Type: application/json" \
  -d '{"blocked_apps":["1Password"],"blocked_domains":["bank"],"excluded_path_fragments":["/.ssh/"]}'
```

### Export

```sh
curl http://127.0.0.1:8765/export
```

### Forget Captures

```sh
curl -X POST http://127.0.0.1:8765/forget \
  -H "Content-Type: application/json" \
  -d '{"from_timestamp":"2026-04-24T00:00:00Z","source_type":"browser","confirm":true}'
```

## Environment

| Variable | Default | Purpose |
| :-- | :-- | :-- |
| `MEMORYOS_HOST` | `127.0.0.1` | Bind address |
| `MEMORYOS_PORT` | `8765` | Port |
| `MEMORYOS_API_KEY` | unset | Optional local API key |
| `MEMORYOS_DB` | `~/Library/Application Support/MemoryOS/memoryos.db` | SQLite path |
| `MEMORYOS_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Web UI origins |
| `MEMORYOS_INDEX_INTERVAL_SECONDS` | `1800` | Background reindex interval while backend is running |
| `MEMORYOS_INDEX_BACKEND` | `auto` | Background index backend |
| `MEMORYOS_INDEX_MODEL` | unset | Optional sentence-transformer model path/name |

## Completion Notes

The backend is functional with the TF-IDF search fallback today. Full semantic search requires captured data plus the Phase 2 ML dependencies and trained/indexed artifacts.
