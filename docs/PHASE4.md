# Phase 4 Web Interface

Phase 4 adds a React/Vite/Tailwind web UI for the local MemoryOS backend.

## Run

Start the backend:

```sh
scripts/run_backend.sh
```

Start the web app:

```sh
cd web
npm install
npm run dev
```

Default URL:

```text
http://127.0.0.1:5173
```

## Views

### Search

- Debounced semantic search.
- Result cards with title, app, source, timestamp, snippet, score, and label state.
- Open action for URLs and file paths.
- Click logging through `POST /click`.

### Recent

- Latest captures from `GET /recent`.
- App and source filters.

### Label

- Keep/noise/manual clear controls.
- Uses `PATCH /captures/{id}/noise`.

### Stats

- Capture totals.
- Index availability.
- App/source breakdowns.
- Keep/noise/unlabeled counts.
- Index refresh through `POST /refresh-index`.

### Settings

- Backend URL.
- Optional API key.
- Backend health check.
- Privacy blocklists.
- JSON export.
- Filtered forget/delete controls.

## Environment

| Variable | Default | Purpose |
| :-- | :-- | :-- |
| `VITE_API_URL` | `http://127.0.0.1:8765` | Backend URL |

The UI stores backend URL and API key in browser local storage.

## Completion Notes

The app is built as an operator console for collecting and improving real data. It intentionally includes labeling and index refresh controls because those are needed before the ML models become useful.
