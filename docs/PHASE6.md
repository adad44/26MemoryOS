# Phase 6 Polish and Launch

Phase 6 turns MemoryOS from phase-by-phase implementation into a documented, demo-ready local project.

## 6.1 Performance

Backend benchmark:

```sh
scripts/benchmark_backend.py --captures 500 --runs 20
```

Runtime process snapshot:

```sh
scripts/benchmark_runtime.sh
```

Current targets:

- Search latency: under 100 ms for the TF-IDF local fallback on small/medium personal datasets.
- Daemon idle CPU: under 2%.
- Backend and web servers bind to localhost.

The benchmark script seeds a temporary SQLite database, builds a TF-IDF index, and measures `/health`, `/stats`, `/recent`, and `/search`.

## 6.2 Privacy Controls

Implemented:

- App blocklist.
- Domain blocklist.
- Path-fragment exclusion list.
- Pause/resume capture flag from the menu bar app.
- Manual keep/noise labeling.
- JSON export.
- Filtered forget/delete endpoint.

Default privacy config lives at:

```text
config/privacy.example.json
```

Runtime privacy config is saved at:

```text
~/Library/Application Support/MemoryOS/privacy.json
```

The daemon reads this file at startup.

## 6.3 Documentation

Completed:

- `README.md`
- `docs/QUICKSTART.md`
- `docs/ARCHITECTURE.md`
- `docs/schema.sql`
- Phase reports: `docs/PHASE0.md` through `docs/PHASE7.md`
- `docs/DEPLOYMENT.md`
- `docs/DEMO_SCRIPT.md`
- Model cards in `docs/model-cards/`

## 6.4 Portfolio Packaging

Completed:

- Local-first architecture.
- GitHub-ready `.gitignore`.
- One-command installer plus reproducible scripts for build, launch, benchmark, export, and install.
- Model cards for planned ML artifacts.
- Demo script for a short walkthrough.

## Remaining Real-World Work

These require real user data or signing/distribution work:

- Train production noise classifier after labeling captures.
- Fine-tune embedding model after collecting enough captures.
- Train the production re-ranker after collecting click/dwell logs. Until then, live search uses the built-in temporal heuristic.
- Replace FSEvents deprecated run loop scheduling with dispatch-queue scheduling.
- Sign/notarize the menu bar app if distributing beyond local use.
