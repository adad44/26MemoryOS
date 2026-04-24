#!/usr/bin/env bash
set -euo pipefail

echo "| Process | PID | CPU % | RSS MB | Command |"
echo "| :-- | --: | --: | --: | :-- |"

patterns=(
  "memoryos-daemon"
  "MemoryOS.app/Contents/MacOS/MemoryOS"
  "uvicorn backend.main:app"
  "vite --host 127.0.0.1"
)

for pattern in "${patterns[@]}"; do
  while read -r pid; do
    [[ -z "$pid" ]] && continue
    ps -p "$pid" -o comm=,%cpu=,rss=,command= | awk -v pid="$pid" -v pattern="$pattern" '{
      cpu=$2
      rss=sprintf("%.1f", $3 / 1024)
      command=""
      for (i=4; i<=NF; i++) command=command $i " "
      printf("| %s | %s | %s | %s | `%s` |\n", pattern, pid, cpu, rss, command)
    }'
  done < <(pgrep -f "$pattern" || true)
done
