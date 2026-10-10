---
name: p50k-demo
description: Start, stop, restart or health-check the local Project 50K demo (fixed-date app on 3060 with its API on 8767, and the dated D1 API on 8768). Use when asked to run, restart or check the demo, or after resealing bundles or rebuilding the frontend.
---

# Local demo stack

Everything binds to 127.0.0.1 and serves sealed bundles only; startup computes and downloads nothing.

| Process | Port | Started by |
|---|---|---|
| Fixed-date research API (`/research/v1`) | 8767 | `ops/local/run_app.py --bundle <fixed bundle>` |
| Frontend (`/`, `/funds/...`, `/dates`, `/dates/funds/...`) | 3060 | the same launcher (`--mode production` needs `frontend/.next`) |
| Dated D1 API (`/research-dated/v1`) | 8768 | `ops/local/run_dated_app.py --index <dated index>` |

Both launchers take an exact sealed directory and never pick the newest one. The fixed bundle is the
concentration-extended `fund-review-app` bundle; the dated index is under `raw/research/fund-review-dated/index/`.
Bundles are tied to the machine and paths they were sealed with, and re-hash the registered files of the checkout
they were sealed in on every load. On the team's Windows machine the demo runs from the dated-view clone while its
fixed bundle belongs to the main checkout, so while the demo runs, leave the main checkout's branch, registered files
and `raw/snapshots/fund_snapshots.sqlite3` alone, and never run `npm run build` in the dated-view clone.

## Start or restart

Run the scripts from the root of the checkout that runs the demo. Windows:

```powershell
powershell -ExecutionPolicy Bypass -File .claude/skills/p50k-demo/start-demo.ps1 -FixedBundle <dir> -DatedIndex <dir> [-Restart]
```

Linux/macOS:

```sh
.claude/skills/p50k-demo/start-demo.sh <fixed-bundle-dir> <dated-index-dir>
```

Instead of arguments, the scripts read `.claude/p50k-demo.local.json` (gitignored):
`{"fixed_bundle": "<dir>", "dated_index": "<dir>"}`. They refuse busy ports. `-Restart` (Windows) first stops
demo processes that belong to this repository only. They wait for `/research/v1/health`, `/research-dated/v1/dates`
and `/`, then print the URLs. Logs go to `.claude/demo-logs/` (gitignored).

Before a production start, build once: `cd frontend && NEXT_TELEMETRY_DISABLED=1 npm run build`.

## Stop

`powershell -ExecutionPolicy Bypass -File .claude/skills/p50k-demo/stop-demo.ps1` or
`.claude/skills/p50k-demo/stop-demo.sh`. They stop only processes that still run this checkout's launchers, API or
frontend. They check the recorded PIDs first, so a stale PID file after a reboot cannot kill an unrelated process.
A demo running from another checkout is left alone and reported.

## Health check without restarting

```sh
curl -s http://127.0.0.1:8767/research/v1/health
curl -s http://127.0.0.1:3060/api/research-dated/v1/dates     # through the frontend proxy
```

Expect HTTP 200 with `Cache-Control: no-store`. A 503 `BUNDLE_INVALID` means a source or registered code file
changed after sealing; see `/p50k-seal-dated`.

## Rules

Real archived data may be shown only in the private local demo (DEC-027). No LAN or public exposure,
deployment, screenshots in git, or synthetic data in the demo itself. `/preview` and `/preview/dates` are
development scaffolds.
