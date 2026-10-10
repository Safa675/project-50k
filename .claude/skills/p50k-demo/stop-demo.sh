#!/usr/bin/env bash
# Stop the demo processes started by start-demo.sh in this repository (Linux/macOS).
set -uo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
for name in fixed dated; do
  pidfile="$repo/.claude/p50k-demo.$name.pid"
  [[ -f "$pidfile" ]] || continue
  pid="$(cat "$pidfile")"
  # Each launcher leads its own process group; SIGINT makes it stop its children before exiting.
  kill -INT -- "-$pid" 2>/dev/null || kill -INT "$pid" 2>/dev/null || true
  for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
  kill -TERM -- "-$pid" 2>/dev/null || true
  rm -f "$pidfile"; echo "Stopped $name launcher ($pid)"
done
