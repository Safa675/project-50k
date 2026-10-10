# BlackSwan: understandable evidence and streamed explanations

2026-10-10, Europe/Istanbul. Requirements: DEC-033, T3.6, T5.2, T5.4, T5.5 and
the T5.6 stock-data presentation. This record follows the original Figma release.

## Changes

- Removed hashes, internal evidence IDs, detector codes, raw provider/storage
  names, availability enums and the operational rights warning from normal UI
  text, including expanded source panels. Audit records and protected APIs retain
  their original information. Preliminary-assessment limitations remain in plain
  language; rights status is unchanged in operational records/API metadata.
- Fund prices distinguish the latest observation from the last usable price.
  THF's latest observation is genuinely empty; its last usable price is dated
  2026-09-24. The headline now displays the usable dated observation. No missing
  chart point was filled and no old price is presented as current.
- The production stock data was present: all 30 instruments have 29 daily
  observations, 870 total, between 2026-09-01 and 2026-10-09. Stock pages now make
  the latest dated close prominent and use a legible chart with matching axes.
- Verified local issuer/manager logos cover 30/30 stocks and 2,113/2,133 funds.
  There are 30 company and 57 manager assets. Fund images are labelled as manager
  branding. Twenty entries retain their real code where branding could not be
  verified. Source URLs and hashes are in `web/public/asset-logos/provenance.json`.
- Added **Bu sonuca nasıl ulaştık?** disclosures beside results and on `/method`.
  They explain actual inputs, time windows, minimum history, comparison direction,
  missing data and limitations, then distinguish calculation, AI interpretation
  and human review. Stock support is explicitly price/company-record data only.
- Chat receives the meaning and stored reason for each observation, not just
  codes/numbers. Short model-local references resolve back to immutable evidence
  IDs before validation and storage. Citation links use human-readable titles.
- Chat streams complete validated paragraphs while the model is still generating.
  Raw token deltas are never exposed. The browser verifies paragraph order and
  equality with the final persisted answer; interrupted/rejected attempts clear
  their draft. Migration 011 retains emitted paragraphs in an append-only audit.
- Proposal prompts and rendered explanations are versioned. Earlier decisions,
  their original text and human reviews remain preserved. Packet selection now
  independently excludes future runs and ineligible evidence.

## Algorithms explained to users

The calculations remain the immutable registered fund protocol: category-relative
median daily-return differences over the recent 60-row window; their change from
the preceding disjoint 120-row window; lag-one return correlation; correlation
with the category's median return; observed history length; weekday staleness;
missing-price checks; and eligible confirmed regulatory records. The page explains
minimum observations and peers, the lower-bound direction of category correlation,
the 11:05 Istanbul publication assumption, unverified public holidays and current
category metadata. No score, threshold or calibration was changed by this work.

## Files

- Backend: `chat.py`, `chat_tools.py`, `chat_routes.py`, `chat_language.py`,
  `evidence_aliases.py`, `ai_client.py`, `decisions.py`, fund `models.py`,
  `queries.py`, `routes.py`, and `db/migrations/011_chat_stream_chunks.sql`.
- UI: fund/stock/detail/method/workflow pages, presentation helpers, source/evidence
  cards, decision panels, watchlists, `AssetLogo`, `MethodExplanation`, chat stream
  parser/drawer, and session controls. Exact paths are in the release Git diff.
- Synthetic regression tests, DEC-033 and the current agent/working notes.

## Completed checks before release integration

```text
cd web
npm run typecheck
Exit 0
npm test
4 files, 21 tests passed

docker compose -f compose.yaml build api web
Exit 0 (repeated after final prompt/session changes)

docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm -e P50K_DB_NAME=p50k_dev -e P50K_TEST_ENDPOINTS=true -e P50K_TEST_DATABASE=1 --volume ./tests:/app/tests:ro --volume ./services:/app/services:ro worker python -m unittest tests.unit.test_product_ai tests.unit.test_product_decisions tests.unit.test_product_chat tests.unit.test_product_chat_streaming tests.unit.test_product_api tests.unit.test_product_evidence_detail tests.unit.test_product_watchlists -q
69 tests in 5.747s; OK, zero skips

P50K_DB_NAME=p50k_dev docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm -e P50K_TEST_DATABASE=1 --volume ./tests:/app/tests:ro --volume ./services:/app/services:ro --volume ./db:/app/db:ro migrate python -m unittest tests.unit.test_product_migrations -q
16 tests in 4.501s; OK, zero skips

P50K_DB_NAME=p50k_dev docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm -e P50K_TEST_ENDPOINTS=true -e P50K_TEST_DATABASE=1 --volume ./tests:/app/tests:ro --volume ./services:/app/services:ro worker python -m unittest tests.unit.test_product_ai tests.unit.test_product_decisions -q
19 tests in 2.186s; OK, zero skips (final v3 proposal changes)

npm run test:browser -- tests/browser/chat.spec.ts --workers=1
5 passed in 8.5s, including a real HTTP stream held open after its first paragraph
```

Desktop/mobile review covered source panels opened, absent internal identifiers,
visible stock charts/latest prices, logo decoding and document overflow. The first
full browser run passed 15/16 and exposed a real review/logout issue: server and
browser timezones rendered review timestamps differently, causing React hydration
recovery and closing the account menu. Timestamps now explicitly use Istanbul
time, logout waits for hydration, and the regression checks a differing server/
browser timezone. Final integrated rerun and Linux results will be recorded below.
Three official SVGs had CRLF source bytes; only their line endings were normalized
to LF. Provenance retains both source hashes and served-file hashes. All 87 asset
hashes match; their graphical content is unchanged.

Final browser run against the built images on isolated PostgreSQL:

```text
npm run test:browser -- --workers=1
16 passed (27.3s)
```

This includes the fixed review/logout flow, no hydration errors with the browser
in Istanbul and Docker in UTC, actual paragraphs visible before HTTP completion,
method disclosures, charts, feedback, notifications and mobile layouts. Code
checkpoint: `84438f7`. The pre-commit leak scan checked 144 changed paths and
returned zero private-path, real-price, fund-name and non-target-code hits.

Linux verification in the clean isolated clone at `84438f7`:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/bin/python -m unittest discover -s tests -t . -v
904 discovered in 88.061s; OK (skipped=73)
831 executed passes; 71 PostgreSQL checks and 2 Windows launcher checks skipped

cd research/events/2026-09-17-spk-liquidations/price_detectors
../../../../.venv/bin/python -m unittest test_detectors -v
9 passed in 0.676s; zero skips

cd docs/handoff-v0.5
../../.venv/bin/python -m unittest discover -s tests -v
88 passed in 0.008s; zero skips
```

PostgreSQL skips are not passes; the separate executed database suites are listed
above. Logs remain outside Git at
`/home/mirza/p50k-baseline-20261010/logs/release-84438f7-*.log`.
The local rollout on 3070/8770 is healthy with eleven migrations, live AI mode,
2,133 funds, 870 stock observations and zero mock decisions. The fallback
processes on 3060/8767/8768 are unchanged.

The fresh backup/restore rehearsal verified 39 tables and eleven migrations,
including the paragraph-audit table and new live proposals. Retained artifact:
`backups/p50k-20261010T180646Z-c6a0b94390324035849de26df9ea8875.dump`.
The first attempt exposed an initialization-readiness race in the isolated
restore container. A narrow TCP readiness check now waits for PostgreSQL's final
server instead of its temporary initialization socket; the corrected script
completed a full restore. All attempts and hashes are preserved in
[the backup report](blackswan-backup-restore-rehearsal.md). No product volume was
removed. The Sunday freeze/cold-boot rehearsal remains separate.

## Live quality checks

The initial chat v3 pilot produced two valid responses and withheld one unknown
reference. Model-local aliases corrected that failure mode in chat v4. Its three
real-data questions all passed citation/numeric validation and answered distinct
questions about missing prices, unavailable comparisons and stale prices.
First checked paragraph: 2.518–2.827 seconds; total: 4.279–4.824 seconds.
These are three observed local timings, not a latency guarantee or an accuracy
evaluation. Private detailed transcripts stay outside Git in Windows TEMP.

The v2 proposal pilot returned four supported valid outcomes with no retry, but
three had repetitive wording caused by inline sentence placeholders. That version
was not accepted as the final wording. V3 requires qualitative explanation once,
separate citations and no inline evidence placeholders. Its live retune passed
8/8 cases from eight categories on the first attempt: two data issues, three
non-material results, two material results and one insufficient-evidence result.
All eight were reviewed for readable wording and support from the provided facts.
No retries or invalid output occurred. Cost was USD 0.049235; latency 3.562–7.040
seconds (mean 4.830). The price-trigger examples covered the consecutive-return
relationship; not every trigger family received a live example. This small
development sample is not validated financial performance or general accuracy.

At 20:59 Istanbul the tuning ledger had used 15/20 attempts, spent USD 0.09712 of
its USD 1 bucket, and held no reservation. Total AI booked across the product was
USD 0.267445, with zero unsettled reservations and no queued/running jobs. No bulk
batch was run. Detailed transcripts and sample identities remain outside Git in
Windows TEMP; only aggregate measurements are recorded here.

Streaming follows the Responses API's semantic event contract and structured
output fields, with additional application validation before display.
[Official streaming documentation](https://developers.openai.com/api/docs/guides/streaming-responses)
and [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## Backend progress and remaining scope

Planning estimate: approximately **85% of the local hackathon backend**. This
is an engineering estimate, not a test-pass percentage or production-readiness
claim. Working areas include auth/roles, PostgreSQL, real ingestion, point-in-time
queries, immutable fund calculations, stock-data APIs, reviewed AI proposals,
bounded chat, worker/budget controls and verified backup/restore.

Remaining work includes the measured wider AI quality gate, separate batch-budget
and single-call batch wiring, the appropriately sized pass, optional challenger/
committee, and the freeze/cold-boot/demo rehearsal. Stock anomaly classification
and stock AI are unimplemented. Bank production integrations, redistribution
rights and validated predictive performance are not claimed.

Data mode is real local delayed source data; tests use synthetic data. Frozen
protocols, detectors, registered research sources and fallback demo files remain
unchanged. The next task is the measured quality/batch gate and final rehearsal,
not changing the registered calculations to improve the historical result.
