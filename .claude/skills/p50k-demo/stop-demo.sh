#!/usr/bin/env bash
# Stop the demo processes started by start-demo.sh in this repository (Linux/macOS).
# A recorded PID is signalled only while it is still this checkout's launcher; stale PID files are discarded.
set -uo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
for name in fixed dated; do
  pidfile="$repo/.claude/p50k-demo.$name.pid"
  [[ -f "$pidfile" ]] || continue
  pid="$(cat "$pidfile")"
  rm -f "$pidfile"
  if [[ "$(ps -o args= -p "$pid" 2>/dev/null)" != *"$repo/ops/local/run_"* ]]; then
    echo "Recorded $name PID $pid is no longer this checkout's launcher; left alone."
    continue
  fi
  # Each launcher leads its own process group; SIGINT makes it stop its children before exiting.
  kill -INT -- "-$pid" 2>/dev/null || kill -INT "$pid" 2>/dev/null || true
  for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
  kill -TERM -- "-$pid" 2>/dev/null || true
  echo "Stopped $name launcher ($pid)"
done
