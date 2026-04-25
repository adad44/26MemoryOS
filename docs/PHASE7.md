# Phase 7: Local User Model

Phase 7 adds a local LLM-powered user model. It reads recent non-noise captures, asks a local Ollama model to extract structured beliefs, stores those beliefs in SQLite, and displays the result in the web UI's You tab.

All processing stays on the Mac. The backend talks to Ollama at:

```text
http://localhost:11434
```

## Requirements

- Ollama installed locally. The one-command installer handles this through Homebrew.
- The `mistral` model pulled locally. The installer pulls it unless `--skip-model-pull` is used.
- Enough captures for useful extraction. The system still runs with sparse data, but the model improves as MemoryOS collects more context.

Check Ollama:

```sh
which ollama
ollama pull mistral
ollama run mistral "respond with only the word: ready"
curl http://localhost:11434/api/tags
```

## Apply Schema

The Phase 7 tables are part of the normal MemoryOS SQLite initialization. You can also run the explicit migration entrypoint:

```sh
python3 backend/db_phase7.py
```

Expected tables:

```text
beliefs
user_model
abstraction_runs
```

## Run Once For Debugging

The installer starts Ollama as a login service. For a manual debug run, make sure Ollama is reachable:

```sh
curl http://localhost:11434/api/tags
```

Then run abstraction:

```sh
python3 backend/abstraction_engine.py
```

If Ollama is not running, the run is recorded as failed in `abstraction_runs` and no captures leave the machine.

The Ollama client requests JSON output and allows up to 300 seconds by default because local models can be slow on first or larger abstraction runs.

## Run Every 6 Hours

The one-command installer registers `com.memoryos.scheduler`. For a foreground debug run:

```sh
scripts/start_scheduler.sh
```

It runs once immediately, then every 6 hours.

## Backend Endpoints

- `GET /user-model`: latest model summary.
- `GET /beliefs`: structured beliefs.
- `DELETE /beliefs/{topic}?confirm=true`: delete an incorrect belief.
- `POST /run-abstraction`: trigger a background abstraction run.
- `GET /abstraction-runs`: run history.
- `GET /abstraction-status`: Ollama/model/running status.

## Web UI

Open the You tab.

- Run Now starts a local abstraction run.
- Ollama status shows whether the local model server is reachable.
- Current Model shows the latest generated summary.
- Beliefs lists interests, knowledge, gaps, patterns, and projects.
- Abstraction Runs shows recent successful or failed runs.

Deleting a belief is local-only and requires confirmation in the UI.
