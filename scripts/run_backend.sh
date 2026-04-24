#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

HOST="${MEMORYOS_HOST:-127.0.0.1}"
PORT="${MEMORYOS_PORT:-8765}"

exec python3 -m uvicorn backend.main:app --host "$HOST" --port "$PORT"
