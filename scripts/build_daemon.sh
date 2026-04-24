#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../daemon"
mkdir -p .build

swiftc \
  -I Sources/CSQLite \
  -Xcc -fmodule-map-file=Sources/CSQLite/module.modulemap \
  Sources/MemoryOSDaemon/*.swift \
  -o .build/memoryos-daemon \
  -framework AppKit \
  -framework ApplicationServices \
  -framework CoreServices \
  -framework PDFKit \
  -lsqlite3

echo "Built daemon/.build/memoryos-daemon"
