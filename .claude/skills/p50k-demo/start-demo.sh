#!/usr/bin/env bash
# Start the local Project 50K demo on Linux/macOS: fixed-date API (8767) + frontend (3060) and the dated API (8768).
# Usage: start-demo.sh <fixed-bundle-dir> <dated-index-dir>   (or .claude/p50k-demo.local.json)
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$repo"
# Absolute paths put this checkout into the launchers' command lines, which stop-demo.sh checks.
py="$repo/.venv/bin/python"
[[ -x "$py" ]] || { echo "Missing $py; run uv sync --locked --extra api --extra api-test --extra research" >&2; exit 2; }
fixed="${1:-}"; dated="${2:-}"
if [[ -z "$fixed" || -z "$dated" ]] && [[ -f .claude/p50k-demo.local.json ]]; then
  fixed="${fixed:-$("$py" -c 'import json;print(json.load(open(".claude/p50k-demo.local.json"))["fixed_bundle"])')}"
  dated="${dated:-$("$py" -c 'import json;print(json.load(open(".claude/p50k-demo.local.json"))["dated_index"])')}"
fi
[[ -n "$fixed" && -n "$dated" ]] || { echo "Pass <fixed-bundle-dir> <dated-index-dir> or create .claude/p50k-demo.local.json" >&2; exit 2; }
[[ -f frontend/.next/BUILD_ID ]] || { echo "Missing frontend build; run npm run build in frontend/" >&2; exit 2; }
for port in 3060 8767 8768; do
  if (exec 3<>"/dev/tcp/127.0.0.1/$port") 2>/dev/null; then echo "Port $port is in use; stop it first (stop-demo.sh)" >&2; exit 1; fi
done
mkdir -p .claude/demo-logs
# Job control gives each launcher its own process group and keeps SIGINT deliverable, so stop-demo.sh can
# interrupt a launcher and let it stop its API and frontend children.
set -m
export PYTHONDONTWRITEBYTECODE=1 NEXT_TELEMETRY_DISABLED=1 P50K_DATED_API_ORIGIN=http://127.0.0.1:8768
nohup "$py" "$repo/ops/local/run_dated_app.py" --index "$dated" --api-port 8768 > .claude/demo-logs/dated.log 2>&1 &
echo $! > .claude/p50k-demo.dated.pid
nohup "$py" "$repo/ops/local/run_app.py" --bundle "$fixed" --mode production > .claude/demo-logs/fixed.log 2>&1 &
echo $! > .claude/p50k-demo.fixed.pid
for url in http://127.0.0.1:8767/research/v1/health http://127.0.0.1:8768/research-dated/v1/dates http://127.0.0.1:3060/; do
  ok=0
  for _ in $(seq 1 180); do curl -fsS -o /dev/null "$url" 2>/dev/null && { ok=1; break; }; sleep 0.5; done
  if [[ $ok == 1 ]]; then echo "OK  $url"; else echo "FAILED $url (see .claude/demo-logs)" >&2; exit 1; fi
done
echo "Demo running: http://127.0.0.1:3060/ and http://127.0.0.1:3060/dates"
