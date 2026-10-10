---
name: p50k-verify
description: Run Project 50K's full verification (Python service suite, frozen detector and handoff suites, frontend typecheck, unit tests, build and browser tests) and separate real regressions from known Windows platform failures. Use before committing or merging, after pulling, or when asked whether the repository is healthy.
---

# Verify Project 50K

Report exact commands and their final summary lines. Never report a test as passed that you did not run,
and never count a skip as a pass.

## Setup (only if missing)

- LF checkout: `.gitattributes` forces LF; convert an older CRLF checkout as in `docs/notes/agent-tooling.md`.
  A CRLF working tree breaks the sealed-bundle and protocol byte checks and the frozen handoff MANIFEST hashes.
- `uv sync --locked --extra api --extra api-test --extra research` and `npm ci --prefix frontend`.
- Interpreter `PY`: `.venv/bin/python` (Linux/macOS) or `.venv/Scripts/python.exe` (Windows). On Windows the
  bare `python` command is usually the Microsoft Store stub.

## Python (repository root)

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services $PY -m unittest discover -s tests -t . -v
(cd research/events/2026-09-17-spk-liquidations/price_detectors && PYTHONDONTWRITEBYTECODE=1 ../../../../$PY -m unittest test_detectors -v)
(cd docs/handoff-v0.5 && PYTHONDONTWRITEBYTECODE=1 ../../$PY -m unittest discover -s tests -v)
```

Expect the frozen suites to report 9 and 88 tests OK. On Linux the root suite passes completely.

On Windows the documented root command has known platform failures that are not regressions:
missing `tzdata` for `ZoneInfo("Europe/Istanbul")`, CRLF fixtures in tests' temporary git repos, the cp1252
console, SQLite file locks in two evidence-store tests and `SO_REUSEADDR` in the v1 launcher test. Also run the
diagnostic variant and compare failing test names, not just counts:

```sh
uv pip install --target "$TEMP/p50k-tzdata" tzdata     # once; outside the repository
PYTHONDONTWRITEBYTECODE=1 PYTHONUTF8=1 GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.autocrlf GIT_CONFIG_VALUE_0=false \
  PYTHONPATH="services;$TEMP/p50k-tzdata" $PY -m unittest discover -s tests -t . -v
```

The diagnostic variant should leave only these three Windows residuals:
`test_evidence_store` foreign-database tests (2 errors, WinError 32) and
`test_local_launcher.test_active_listener_rejected_and_remains_usable` (1 failure). Anything else is a finding.

## Frontend (`frontend/`)

```sh
npm run typecheck
npm test
NEXT_TELEMETRY_DISABLED=1 npm run build
```

Browser tests need a production server; `playwright.config.ts` has no `webServer` and uses
`http://127.0.0.1:3060` with the system Chrome channel. If port 3060 is free:
`node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3060` in the background, then
`npm run test:browser`, then stop the server.

If 3060 is busy (for example a running demo), never stop that process. Start the server on a spare port and use
the mapped config in this skill, which keeps the browser origin at 3060 but routes Chrome to the spare port:

```sh
node node_modules/next/dist/bin/next start --hostname 127.0.0.1 --port 3061 &
P50K_SPARE_PORT=3061 npx playwright test --config "${CLAUDE_SKILL_DIR}/playwright-spare-port.config.mjs"
```

Stop the spare server afterwards and confirm the port is free.

## Hooks

`node --test .claude/hooks/hooks.test.mjs` (repository root) checks what the project hooks block and allow.
Run it after changing anything in `.claude/hooks/` or `.claude/settings.json`.

## Before committing

- `git diff --check`, no CRLF in new files, and `/p50k-leak-scan` with zero hits.
- Files bound into sealed bundles unchanged unless a reseal is intended (see `/p50k-new-research-slice`).
