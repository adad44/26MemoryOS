# MemoryOS Phase 1

This folder now contains the first-pass data capture layer:

- `daemon/`: Swift Package executable for local macOS capture.
- `extension/`: Chrome Manifest V3 extension that captures page title, URL, and visible text after 10 seconds.
- `scripts/browser_ingest_server.py`: local browser capture endpoint that writes to the same SQLite database.

## Run the Swift daemon

```sh
cd daemon
swift run memoryos-daemon
```

If Swift Package Manager is unavailable in the local Command Line Tools install, build directly from the project root:

```sh
scripts/build_daemon.sh
daemon/.build/memoryos-daemon
```

On first run, macOS should prompt for Accessibility permission. If it does not, open:

System Settings -> Privacy & Security -> Accessibility

Then allow the terminal app running the daemon.

The database defaults to:

```text
~/Library/Application Support/MemoryOS/memoryos.db
```

Override it with:

```sh
MEMORYOS_DB=/tmp/memoryos.db swift run memoryos-daemon
```

## Run browser ingest

In a second terminal:

```sh
python3 scripts/browser_ingest_server.py
```

Then load the unpacked extension from `extension/` in Chrome.

## Validate captures

```sh
sqlite3 "$HOME/Library/Application Support/MemoryOS/memoryos.db" \
  "SELECT app_name, source_type, COUNT(*) FROM captures GROUP BY 1, 2 ORDER BY 3 DESC;"
```

## Toolchain troubleshooting

If Swift build commands fail with an SDK/compiler mismatch, install or select matching Apple developer tools. This machine currently reports a Command Line Tools mismatch where the Swift compiler and macOS SDK were built from different Swift patch versions. A full Xcode install or refreshed Command Line Tools install should resolve that before compiling the daemon.

## Current screenshot fallback status

The daemon detects inaccessible windows by absence of Accessibility text. Window-specific screenshot capture/OCR is left as a hook because the production version should live in a signed app target with ScreenCaptureKit and Screen Recording permissions. That avoids brittle full-screen screenshots from a command-line executable.
