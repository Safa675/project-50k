# BlackSwan Phase 3 completion, 2026-10-10

Implementation `2158638` connects login, protected fund pages, evidence, AI proposal
storage, human review and the worker. Later verification fixes are additive; frozen
detector/calibration code is unchanged. Supports T1.6/T1.8/T3.1–T3.6. T3.1's paid
account/model smoke remains pending because the key file is absent. Chat and the
story/agent-team screens remain Phase 5 work, not claimed here.

Requirement references: FR-009/010/011/031/032/048/054/055/061/062/106/107/120/122,
NFR-009/012/013/015/020/022/023/027/030/031/032/034/077. Original IDs and the frozen
registry remain unchanged; own-auth/override behavior follows DEC-028.

## Changed files and behavior

- Auth modules, app/session dependencies/settings: Argon2id with pepper, hashed
  server sessions, signed login CSRF, Origin checks, 12-hour absolute/2-hour idle
  expiry, rotation/logout/password-change revocation and persisted email/IP
  throttling. Provisioning requires the owner; app users cannot assign roles.
- Egress, validator, client, decisions and decision routes: typed D7 allowlist;
  strict schema/citations/options, server-rendered numbers, wording guards,
  immutable packets/proposals/reviews, original value and human reason beside the
  effective value. Deterministic abstention is distinct from AI. INVALID output
  is blocked from rerunning rather than replayed as cached valid output.
- Migration 005, queue/AI worker: $20 internal buckets, worst-case reservations
  before calls, uncertain/expired settlement, at most 20 tuning attempts, exact
  cache dimensions, deduplicated leases, SKIP LOCKED claims, renewal and
  ownership-bound completion. Account access/model quality remain unverified.
- New web login, protected catalog/detail, daily gap-aware NAV chart/table,
  evidence/source displays, review queue and override form. Real empty/error
  states and integrity labels; server sessions guard reads. Proxy client-IP
  metadata is overwritten; API trusts only the resolved web-container peer.
- New synthetic auth/AI/decision/browser tests and guarded development seed;
  settings/migration tests updated. No new frontend dependency or paid account.

Requests use Responses, `store:false`, SDK retries zero, timeout 60 seconds,
strict JSON schema and bounded output. Changed models require explicit pricing.
Default reservation pricing conservatively uses the cache-write input rate and
standard output rate from the [official model page](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
checked 2026-10-10. [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
was checked too. No request was sent to OpenAI.

## Exact verification

Python uses `PYTHONPATH=services`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUTF8=1`.

| Command | Actual result |
|---|---|
| `.venv/Scripts/python.exe -m unittest discover -s tests/unit -p 'test_product_*.py' -v` | 164 tests in 12.802s; OK, 42 PostgreSQL skips (before two added concurrency checks) |
| `docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm -e P50K_DB_NAME=p50k_dev -e P50K_TEST_ENDPOINTS=true -e P50K_TEST_DATABASE=1 --volume ./tests:/app/tests:ro --volume ./services:/app/services:ro worker python -m unittest tests.unit.test_product_auth tests.unit.test_product_ai tests.unit.test_product_decisions -v` | 17 OK, zero skips; actual session/review/cap tests and mocked SDK boundary |
| Same isolated command, `python -m unittest tests.unit.test_product_ai -v`, after stopping only the smoke worker | 11 OK, zero skips; concurrent reservations, distinct claims and expired-lease ownership recovery |
| Same isolated command, `python -m unittest tests.unit.test_product_decisions -v` | 1 OK; proposal→override→cache→rejection; invalid retry/block never displaces review |
| Isolated migrate command with services/tests/db binds, `python -m unittest tests.unit.test_product_migrations -v` | 16 OK, zero skips; migration 005 applied |
| `npm run typecheck`; `npm test` in web | Exit 0; 4 proxy unit checks pass |
| `npm run test:browser` in web | 4 pass: login→catalog→detail/evidence→override→logout, mobile login and landing |
| `docker compose -f compose.yaml build api web` | Both production images build; final API/worker rebuilt |
| `docker compose -f compose.yaml -f compose.override.yaml -f compose.dev.yaml up -d --no-build --wait --wait-timeout 60` | Product services healthy; migrations successful |
| Linux `2158638`: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/bin/python -m unittest discover -s tests -t . -v` | 827 in 70.431s; OK, 44 explained skips (42 PostgreSQL, two Windows launcher checks); no research regression |
| Frozen detector `../../../../.venv/bin/python -m unittest test_detectors -v` | 9 pass |
| Frozen handoff `../../.venv/bin/python -m unittest discover -s tests -v` | 88 pass |
| Leak scan with `P50K_RAW_DIR` pointing at main raw; `git diff --check` | Zero hits; clean |

Count-only real-session/HTTP checks verified catalog 2,133, eight THF signals,
its candidate event and authenticated server-rendered web. The temporary session
was deleted afterward. One local admin account exists; credentials were generated
into ignored `secrets/local-admin-login.json` without displaying/inspecting them.
Anonymous funds return 401; real mock-row count is zero; 17,064 detector records remain.

Logs: Windows TEMP `p50k-phase3-final-20261010`; Linux
`/home/mirza/p50k-baseline-20261010/logs/phase3-*.log`. Browser artifacts are ignored,
synthetic only. The fallback keeps original 3060/8767/8768 listeners and main files.

## Limitations and next task

Real data is private localhost DELAYED, rights UNREVIEWED. Mocks/seed are restricted
to p50k_dev and labelled synthetic. Paid calls, live INVALID-rate measurement,
account/model smoke, chat and agent-team runs were not performed. Lexical validation
is a development guard, not validated claim-verification accuracy. Backup/restore
and image-layer scans remain freeze checks. No deployment/entitlement claim.

T0.2 key is absent; ten T1.7a human exact checks remain open. Closest identity is
approved, but events stay candidates with unknown availability. Safa/Barış asks,
K1–K6 and the do-not-claim list remain. Snapshots/KAP lists/SPK PDFs completed;
profiles/prices continue externally. Next: safe refresh import without widening
the fixed peer/category universe, read-only chat, then gated live tuning/pass when
Mirza supplies the key. Record scope amendments before computation. Keep the
load-bearing main checkout unchanged until K4.
