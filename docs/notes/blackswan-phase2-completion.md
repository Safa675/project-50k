# BlackSwan Phase 2 completion, 2026-10-10

T2.1/T2.2/T2.4 delivered; T2.6 downloads were advanced during Phase 1 on Mirza's
explicit request. Supports FR-003/018/019/031/032/037/048/054/074/120/122 and
NFR-001/022/023/035/038. The frozen requirements registry remains unchanged.

## Protocol and implementation

The immutable all-fund v2 protocol was committed alone at `e9b7ba7`, before any
all-fund computation. Implemented at `b75e3ff`; API and public runner fixes at
`c8bd652`. Changed files: the new `all_funds_v2/PROTOCOL.md`; new detector math,
pipeline and guarded entry point; migrations 003/004; API models, queries and
routes; CLI/app registration; Docker protocol inclusion; synthetic unit and
PostgreSQL tests; the existing migration tests' temporary version filenames;
and the leak scanner's external price-file path coverage.

One immutable category calibration uses only rows before 2025-10-06 and the
saved listing's `fonTurAciklama`. Overnight reruns reuse it. Evidence and signals
are append-only, and completed runs reject later inserts even by the owner.
Current return/peer admission, missing gaps, zero variance, publication cutoffs,
confirmation time and conflicting revisions fail closed. D5 is a visible-history
attribute, not an anomaly. The public runner rejects dates before its calibration.

## Actual real-data run

Cutoff `2026-10-10T13:18:55+00:00`; last eligible price date `2026-10-07`.
Run `b9fa5111-327b-447e-bc74-3bf98f1fe0bc` contains 17,064 signal/evidence records:
eight for every one of 2,133 funds. A second identical command reused that run;
the database still contains one calibration and one completed detector run.

Aggregate checks found zero missing per-fund results, evidence-binding errors,
future evidence, triggered evidence with unknown availability, or nondevelopment
results. D5 never triggers. All 2,133 regulatory results abstain because confirmed,
eligible events are not yet available. The 131 candidate timeline records remain
visible for private review, with unknown availability and zero regulatory triggers.
Staleness warnings reflect the older archive date, not a provider outage claim.

All 17,064 signal DTOs serialize correctly; actual evidence dates remain separate
from the shared run date. Catalog pagination covers all 2,133 funds; bounded global
signal pagination covers all results. Charts preserve nulls and ambiguous tied
revisions. Fund/API/docs routes remain default-deny until Phase 3 session auth.

## Exact verification

Windows Python uses `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services PYTHONUTF8=1`.

| Command | Result |
|---|---|
| `.venv/Scripts/python.exe -m unittest tests.unit.test_product_detectors_math tests.unit.test_product_detector_pipeline -v` | 33 tests OK, zero skips |
| `.venv/Scripts/python.exe -m unittest tests.unit.test_product_detector_runner tests.unit.test_product_api -v` | 23 tests OK, 8 PostgreSQL skips |
| `docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm -e P50K_DB_NAME=p50k_dev -e P50K_TEST_ENDPOINTS=true -e P50K_TEST_DATABASE=1 --volume ./tests:/app/tests:ro --volume ./services:/app/services:ro --volume ./db:/app/db:ro migrate python -m unittest tests.unit.test_product_detector_database tests.unit.test_product_detector_runner_database tests.unit.test_product_migrations tests.unit.test_product_api.ProductReadDatabaseTests -v` | Initial 34 tests OK, zero skips; the final API PostgreSQL class separately passes all 8 tests |
| `docker compose -f compose.yaml run --rm --no-deps worker python -m p50k.product.cli run-detectors --cutoff 2026-10-10T13:18:55+00:00` | First real run completed; second reused the same run |
| `docker compose -f compose.yaml build api`; `docker compose -f compose.yaml -f compose.override.yaml -f compose.dev.yaml up -d --no-build --wait --wait-timeout 60` | Build/migrations/runtime healthy |
| Linux pinned uv `sync --locked --python 3.13.15 --extra api --extra api-test --extra research --extra product`; `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/bin/python -m unittest discover -s tests -t . -v` at `c8bd652` | 810 tests in 70.856s; OK, 37 expected skips (35 separate PostgreSQL checks and two Windows-only launcher checks); no research regression |
| Frozen detector `../../../../.venv/bin/python -m unittest test_detectors -v` | 9 pass |
| Frozen handoff `../../.venv/bin/python -m unittest discover -s tests -v` | 88 pass |
| Leak scanner with `P50K_RAW_DIR` pointing to main `raw/`; `git diff --check` | Zero leak hits; clean diff |

Full logs are external: WSL `/home/mirza/p50k-baseline-20261010/logs/phase2-*.log`
and Windows TEMP `p50k-phase2-final-20261010`. Database/DTO checks emitted only
counts and identifiers, not price values, thresholds or other-fund names.

## Data mode, limits and next work

Real current archived data is `DELAYED`, rights `UNREVIEWED`, with development
labels. No validated accuracy, lead time, independent holdout, fraud inference or
investment advice is claimed. Category history, currency comparability, holiday
calendar and inferred publication time remain disclosed protocol limits.

T0.2 key readiness and the ten T1.7a exact-name human checks remain open. SPK has
194 downloaded PDFs; KAP and snapshots continue; profiles/prices queue behind the
snapshot collector. New downloaded funds must not silently change the v2 peer
universe/category source; importing later data needs that explicit boundary.

Phase 3 has started in parallel: login/session auth, real fund screens, AI egress,
validation, budgets, decisions, review and queue. Authenticated HTTP/browser behavior
and paid AI calls were not verified by this phase. K1–K6 and every team ask remain
carried forward. Main checkout and the sealed fallback demo are untouched.
