#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP_DIR="$ROOT/menubar/dist/MemoryOS.app"
BIN_DIR="$APP_DIR/Contents/MacOS"
RES_DIR="$APP_DIR/Contents/Resources"
BUILD_DIR="$ROOT/menubar/.build/release"

mkdir -p "$BUILD_DIR"
swiftc \
  "$ROOT"/menubar/Sources/MemoryOSMenuBar/*.swift \
  -o "$BUILD_DIR/memoryos-menubar" \
  -framework AppKit \
  -framework ApplicationServices \
  -framework CoreGraphics \
  -framework SwiftUI

rm -rf "$APP_DIR"
mkdir -p "$BIN_DIR" "$RES_DIR"
cp "$ROOT/menubar/.build/release/memoryos-menubar" "$BIN_DIR/MemoryOS"

cat > "$APP_DIR/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>MemoryOS</string>
  <key>CFBundleIdentifier</key>
  <string>com.memoryos.menubar</string>
  <key>CFBundleName</key>
  <string>MemoryOS</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>0.1.0</string>
  <key>CFBundleVersion</key>
  <string>1</string>
  <key>LSMinimumSystemVersion</key>
  <string>13.0</string>
  <key>LSUIElement</key>
  <true/>
  <key>NSDesktopFolderUsageDescription</key>
  <string>MemoryOS watches Desktop files you edit so they can be searched locally.</string>
  <key>NSDocumentsFolderUsageDescription</key>
  <string>MemoryOS watches Documents files you edit so they can be searched locally.</string>
  <key>NSDownloadsFolderUsageDescription</key>
  <string>MemoryOS watches Downloads files you edit so they can be searched locally.</string>
</dict>
</plist>
PLIST

echo "Built $APP_DIR"
