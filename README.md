# MemoryOS

MemoryOS is a local-first personal knowledge engine for macOS and web. It captures useful context from active windows, browser pages, and local files into SQLite, then later uses ML embeddings and vector search to make that history searchable.

Current status: Phase 0 is complete and Phase 1 has a working baseline scaffold.

## Roadmap

| Phase | Name | Status |
| :-- | :-- | :-- |
| 0 | Setup & Architecture | Complete |
| 1 | Data Capture Layer | Baseline implemented |
| 2 | ML Pipeline | Code complete; needs captured/labeled data |
| 3 | Search Backend | Not started |
| 4 | Web Interface | Not started |
| 5 | Mac Menu Bar App | Not started |
| 6 | Polish & Deploy | Not started |

## Project Structure

```text
memoryos/
├── daemon/          # Swift background capture process
├── extension/       # Chrome browser extension
├── ml/              # Python ML training and inference
│   ├── data/        # Raw and processed local training data
│   ├── models/      # Saved model weights and indexes
│   ├── train/       # Training scripts
│   └── serve/       # Inference helpers
├── backend/         # Future FastAPI search backend
├── web/             # Future React frontend
├── docs/            # Architecture, schema, and phase notes
└── scripts/         # Local helper scripts
```

## Phase 1 Quick Start

Build the daemon:

```sh
scripts/build_daemon.sh
```

Run it:

```sh
daemon/.build/memoryos-daemon
```

Run browser ingest in a second terminal:

```sh
python3 scripts/browser_ingest_server.py
```

Then load `extension/` as an unpacked Chrome extension.

More detail is in [docs/PHASE1.md](docs/PHASE1.md).

## Local Data

The default SQLite database location is:

```text
~/Library/Application Support/MemoryOS/memoryos.db
```

Override it for testing:

```sh
MEMORYOS_DB=/tmp/memoryos.db daemon/.build/memoryos-daemon
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [SQLite schema](docs/schema.sql)
- [Phase 1 notes](docs/PHASE1.md)
- [Phase 2 notes](docs/PHASE2.md)
- [Roadmap source](MemoryOS_Roadmap-2.md)
