#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${MEMORYOS_REPO_URL:-https://github.com/adad44/MemoryOS.git}"
BRANCH="${MEMORYOS_BRANCH:-main}"
SOURCE_DIR="${MEMORYOS_SOURCE_DIR:-$HOME/Library/Application Support/MemoryOS/source}"

die() {
  printf "MemoryOS install error: %s\n" "$1" >&2
  exit 1
}

log() {
  printf "\n==> %s\n" "$1"
}

[[ "$(uname -s)" == "Darwin" ]] || die "MemoryOS currently installs on macOS only."
command -v git >/dev/null 2>&1 || die "git is required. Install Apple's command line tools or Git, then rerun this command."

if [[ -d "$SOURCE_DIR/.git" ]]; then
  log "Updating MemoryOS source in $SOURCE_DIR"
  git -C "$SOURCE_DIR" fetch --depth 1 origin "$BRANCH"
  git -C "$SOURCE_DIR" checkout -q "$BRANCH"
  git -C "$SOURCE_DIR" reset --hard -q "origin/$BRANCH"
else
  log "Downloading MemoryOS to $SOURCE_DIR"
  mkdir -p "$(dirname "$SOURCE_DIR")"
  git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$SOURCE_DIR"
fi

log "Running the MemoryOS installer"
exec "$SOURCE_DIR/scripts/install_memoryos.sh" "$@"
