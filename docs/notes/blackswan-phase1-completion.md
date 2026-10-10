# BlackSwan Phase 1 completion, 2026-10-10

## Scope and requirements

Delivered T1.1, T1.3, T1.4, T1.2, T1.5 and T1.7 in the prescribed order. Download
runners from T2.6 were advanced after Mirza explicitly authorized immediate collection.
DEC-031 records D7 and the takeover answers. T0.2 key readiness and T1.7a ten
exact-name human checks remain open. The closest-name identity is confirmed.

Requirement support: FR-017/018/020/021/023, NFR-001/022/023/048/049/075/076/077/079,
and FR-120/122 evidence/decision storage groundwork. These are slice references;
end-to-end product requirements are not declared complete. The frozen registry stays unchanged.

## Changed files

- `.gitignore`, `.dockerignore`, `pyproject.toml`, `uv.lock`; secret-read hook and
  its registration/tests; leak scanner and its synthetic tests.
- `compose.yaml`, dev/AI overlays and read-only override example; Dockerfiles,
  credential generation and isolated smoke script under `ops/docker/`.
- `db/README.md`, two plain SQL migrations; `services/p50k/product/` settings,
  logging, database/migration runner, API health/default deny, heartbeat worker,
  archive reader, staging importer, CLI and public-source download runners.
- New locked Next.js `web/` with Turkish public page, real database readiness,
  Host checks, bounded cookie/CSRF/SSE proxy, unit/browser checks.
- Product synthetic Python tests; `ops/local/check-product-proxy.py` and
  `start-product-downloads.ps1`; DEC-031, plan, current state and team asks.

All new source files use LF. No frozen handoff, detector, protocol, registered
source or main-checkout file was edited. The local ignored override holds host
paths; private data and credentials are excluded from images and commits.

## Runtime and import results

`docker compose up` starts PostgreSQL 18.6, migrations, API, worker and web.
The PostgreSQL volume mounts at `/var/lib/postgresql`. Host ports bind loopback
3070/8770; `compose.dev.yaml` exposes 5433. The fallback demo retains its original
3060/8767/8768 listeners. Runtime passwords are generated locally without displaying
them. The optional AI overlay mounts the key only to API/worker; AI remains off.

| Table/check | Actual count |
|---|---:|
| Funds | 2,133 |
| Dated price rows | 1,725,078 |
| Positive prices | 1,673,412 |
| Missing price rows | 51,666 |
| Snapshots | 1,173 |
| KAP document entries | 1,292 |
| KAP parsed-report index rows | 1,255 |
| Candidate SPK events | 131 |
| Confirmed SPK events | 0 |

Actual first import inserted these rows. Actual repeat imports inserted zero
observations and retained nulls. Both sources and input inventory are hashed;
changed bytes, active SQLite journals, future-dated rows and conflicting PDF
attachment revisions abort the transaction. Known publication dates never become
invented precise timestamps. Current categories/status remain current metadata.

The archive reader uses Decimal; zero NAV becomes NULL. Positive TEFAS row
availability follows the explicit 11:05 Istanbul assumption; missing rows become
known at archive acquisition. KAP timestamps retain the Istanbul interpretation
and cadence. SPK publication time is unknown and stays NULL; unconfirmed events
cannot become detector or insurance evidence.

## Exact verification commands and results

From the worktree unless noted; Python uses `PYTHONPATH=services`,
`PYTHONDONTWRITEBYTECODE=1` and `PYTHONUTF8=1`.

| Command | Actual result |
|---|---|
| `uv lock`; `uv sync --locked --extra api --extra api-test --extra research --extra product` | Exit 0; OpenAI 3.28.0, psycopg 3.3.6/pool 3.3.3, argon2-cffi 25.1.0 locked |
| `.venv/Scripts/python.exe -m unittest discover -s tests/unit -p 'test_product_*.py' -v` | 78 tests; OK, 14 PostgreSQL-only skips; these skips are not passes |
| `docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm -e P50K_DB_NAME=p50k_dev -e P50K_TEST_ENDPOINTS=true -e P50K_TEST_DATABASE=1 -v ./tests:/app/tests:ro -v ./services:/app/services:ro -v ./db:/app/db:ro migrate python -m unittest tests.unit.test_product_migrations -v` | 16 passed, zero skips; includes 11 actual database checks |
| `docker compose -p p50k-smoke -f compose.yaml run --rm --no-deps -e P50K_DB_NAME=p50k_dev -e P50K_TEST_ENDPOINTS=true -e P50K_TEST_DATABASE=1 -v ./tests:/app/tests:ro -v ./services:/app/services:ro worker python -m unittest tests.unit.test_product_import_database -v` | 3 passed, zero skips; COPY/nulls/idempotency, rollback and attachment conflict |
| `docker compose -f compose.yaml build api web` | Both images built; API rebuilt after final importer changes |
| `docker compose -f compose.yaml -f compose.override.yaml -f compose.dev.yaml config --no-interpolate --quiet` | Exit 0 |
| `powershell -NoProfile -ExecutionPolicy Bypass -File ops/docker/check-smoke.ps1 -KeepRunning` | Exit 0; isolated healthy services; Cookie/Set-Cookie, Origin/CSRF and 10 individually streamed one-second SSE events for both loopback origins |
| `npm run typecheck`; `npm test`; `npm run test:browser` in `web/` | Exit 0; 4 unit tests and 2 browser checks pass |
| `node --test .claude/hooks/hooks.test.mjs .claude/hooks/protect-secret-reads.test.mjs` | 10 passed |
| `.venv/Scripts/python.exe -m unittest tests.unit.test_registered_sources_lock -v` | 4 passed |
| `docker compose -f compose.yaml -f compose.override.yaml run --rm --no-deps worker python -m p50k.product.cli import-archive --raw-dir /inputs/raw --snapshot-db /inputs/snapshots-local.sqlite3 --snapshot-db /inputs/snapshots-forward.sqlite3 --event-map /inputs/spk-mapping.json` | Actual real import and zero-insert repeats succeeded; counts above |
| `.venv/Scripts/python.exe .claude/skills/p50k-leak-scan/leak_scan.py`, with `P50K_RAW_DIR` pointing to main `raw/` | Exit 0; no private-path/value/name/ticker hits; re-run on staged files before every commit |
| `git diff --check` | Clean |

Takeover baseline at `19989c5`: WSL2 CPython 3.13.15/uv 0.12.17 locked environment.
Exact Linux commands: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/bin/python -m unittest discover -s tests -t . -v`;
from frozen detector directory, `../../../../.venv/bin/python -m unittest test_detectors -v`;
from handoff, `../../.venv/bin/python -m unittest discover -s tests -v`.
Results: 663, 9 and 88 pass, zero skips. Windows root baseline: 663 tests,
6 failures/30 errors/1 skip; UTF8/autocrlf-disabled diagnostic has only the three
documented residual names (1 failure/2 errors/1 skip). No diagnostic regression.
Main frontend baseline: typecheck/build exit 0, 118 unit tests, 65 browser tests
on spare port 3061 pass. The final product-commit Linux result is recorded below
after it runs; the baseline alone is not claimed as final regression verification.

Full logs stay outside git: Windows TEMP `p50k-takeover-baseline-20261010`,
`p50k-codex-frontend-baseline-20261010`, `p50k-product-infra-20261010`,
`p50k-phase1-final-20261010`; Linux `/home/mirza/p50k-baseline-20261010/`.

## Downloads, limitations and next task

SPK 2024–2026 collection finished with 194 discovered PDFs. KAP uses the official
public directory, covers the authorized missing TEFAS-traded cohort and is running.
TEFAS profiles and 12-month prices wait for the legacy all-fund snapshots to finish.
The launcher discovers collectors; per-host locks prevent duplicate new streams.
Redirect hops are individually paced/logged; cached replies must match source,
method, status, payload and SHA. TLS verification is on. Three consecutive failures
stop a runner; each job resumes from verified external files.

Data mode: real archived/current published data on localhost, `DELAYED`, rights
`UNREVIEWED`; synthetic tests only in isolated `p50k_dev`. No paid AI call, deployed
service, backup restore rehearsal or final image-layer secret scan was performed.
Own auth, detectors, AI validator/egress/decisions, review UI and chat belong to
later phases; this public page grants no fund access. The worker provides a real
database heartbeat, not the Phase 3 AI queue. No detector accuracy or lead-time
claim follows from this work.

Next recommended task: Phase 2, beginning with the v2 detector protocol committed
alone before computation, then detectors and the authenticated-ready API. Retain
K1–K6, Safa's story/legal/source asks, Barış's tokens/design asks and all do-not-claim
rules. Main remains untouched until demo decoupling; integration merges use a
separate checkout and merge commits only.
