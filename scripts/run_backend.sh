#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

HOST="${MEMORYOS_HOST:-127.0.0.1}"
PORT="${MEMORYOS_PORT:-8765}"
PYTHON="${MEMORYOS_PYTHON:-python3}"

if [[ -x ".venv/bin/python" && -z "${MEMORYOS_PYTHON:-}" ]]; then
  PYTHON=".venv/bin/python"
fi

exec "$PYTHON" -m uvicorn backend.main:app --host "$HOST" --port "$PORT"
