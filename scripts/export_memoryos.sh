#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${MEMORYOS_API_URL:-http://127.0.0.1:8765}"
OUT="${1:-memoryos-export-$(date +%Y-%m-%d).json}"

curl -sS "$BASE_URL/export" -o "$OUT"
echo "Exported $OUT"
