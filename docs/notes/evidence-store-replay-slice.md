# Slice A: fund evidence store and point-in-time replay

Approved by the owner in chat on 2026-10-08, after PR #3 was merged.
Scope: DEC-024, Turkish investment funds only. This is a local data foundation;
the application, detector service, public API and external delivery remain later work.

## Requirement coverage

- **FR-018:** original source timestamps are retained separately from normalized,
  timezone-aware UTC instants. A date alone does not become an invented timestamp.
- **FR-019:** retain source observation/retrieval times, successful import time,
  source fingerprints and bundle metadata. Missing upstream receipt times stay unknown.
- **FR-032:** load the existing daily price format; preserve Decimal precision and
  missing NAV. Zero NAV is missing. Intraday NAV input is rejected.
- **FR-108:** seal content-addressed bundles with provenance, source hashes and
  explicit rights/origin. **Partial:** real-data rights are not cleared.
- **FR-109:** bind a cursor to a sealed bundle and cutoff; exclude future or unknown
  availability and select eligible source versions. **Partial:** later application
  paths must also bind web research, holdings and notification behavior to replay.
- **NFR-038:** test cutoff invariance under changes to future observations and
  revisions. **Partial:** detector-level integration remains a later slice.

The frozen handoff and all 284 registry statuses are unchanged. Passing synthetic
tests does not establish historical performance or complete these requirements.

## Time and source policies

The internal observation records keep effective, publication, availability,
observation and ingestion times separate. Original strings, date-only periods,
source identifiers, units, versions and limitations are retained. Unknown times
may be stored internally; an unknown historical availability cannot enter replay.
These internal records are not a public `evidence.schema.json` response.

### TEFAS price files

The source row date is retained as a source date. It is not silently shifted by a
calendar day to infer valuation time. The roughly 11:05 publication observation in
the provider spike is not applied to the historical series.

The downloaded version is known no earlier than its recorded `retrieved_at`.
Earlier historical availability is not established by the existing format.
Missing or invalid retrieval times cannot be replaced with the import clock.
Only dated daily NAV is supported; no intraday candles or gap filling.

### TEFAS snapshot database

The source database is opened read-only. Only explicitly selected funds are read.
Its inferred `as_of` and rule are retained as metadata. Latest size, units,
investors and category are available no earlier than `retrieved_at`; matching a
NAV does not backdate them. Current categories and the current top-100 selection
do not establish historical category membership or universe membership.

### KAP parsed series

Retain the selected disclosure ID, source `published_at`, reporting period and
cadence. Existing `kap_series.py` may have discarded older disclosures when
choosing one row per period. The selected JSON does not prove the receipt/version
history of the original report; its timezone interpretation was also an assumption
in the spike. Consequently the existing parsed format is stored with `UNKNOWN`
historical availability and excluded from replay. No missing version, receipt time
or weekly effective timestamp is reconstructed. Admitting archive-verified KAP
versions is a subsequent data task, not an automatic relaxation of the cutoff.

### Origins, rights and fingerprints

Real local inputs retain `HISTORICAL_REPLAY` origin and `UNKNOWN` rights.
Explicitly marked synthetic fixtures retain `SYNTHETIC` origin and rights. A CLI
flag cannot relabel unmarked real inputs as synthetic. Real provider values do not
enter Git or public output.

Whole-file SHA-256 hashes belong to the bundle source manifest. Each observation
has its own record-level source version so changing a future input row does not
change the identity of earlier evidence. Re-importing identical content is
idempotent and preserves the first successful import metadata. Identical records
shared by later bundles retain their first ingestion time. Bundle content is
verified before replay; conflicting equally timed revisions are not silently
resolved by ingestion order or hash order.

## Local import boundary

The import job accepts explicit price/KAP file paths and an optional snapshot
database, an explicit selected fund list, and a separate destination. It performs
no network requests, statistics or detector evaluation. The production CLI limits
selection to the committed `top100_funds.txt`; it does not sweep the unopened funds.
JSON files must be named `CODE.json`, with a matching `fund` inside. Synthetic JSON
must explicitly declare `origin: SYNTHETIC`; a synthetic SQLite fixture declares
that origin in `evidence_import_metadata(key, value)`. Unmarked inputs cannot be
relabelled by a flag. JSON provider markers must match the selected TEFAS or KAP
adapter. Price row dates cannot be later than the recorded retrieval's Istanbul
calendar date; equivalent UTC and offset timestamps receive the same validation.

Currency is retained where the input explicitly supplies it. Missing currency
is `UNKNOWN_CURRENCY`, not an assumed TRY denomination. Counts, percentages and
fund units retain their dimensional units; later calculations must first establish
compatible currencies.

The output must be outside the repository and must not alias an input, including
symlinks/hardlinks. A live SQLite WAL is rejected rather than fingerprinting an
incomplete source snapshot. Imports are transactional; failures do not publish a
partial bundle. Existing source files/databases are not migrated or overwritten;
an existing unrelated target database is rejected.

Example from the repository root (local input paths only; no data values):

```sh
PYTHONPATH=services python -m p50k.jobs.import_evidence \
  --funds THF TP2 \
  --price-file research/events/2026-09-17-spk-liquidations/raw/prices/THF.json \
  --price-file research/events/2026-09-17-spk-liquidations/raw/prices/TP2.json \
  --kap-file research/spikes/2026-10-06-tefas/raw/kap_series/THF.json \
  --kap-file research/spikes/2026-10-06-tefas/raw/kap_series/TP2.json \
  --out ~/.local/share/project-50k/evidence.sqlite3
```

This command is documentation, not a claim that a real-data import was executed.
Importing data cannot clear G03 rights or make an unknown archive admissible.

## Acceptance boundary

Synthetic tests cover exact/equivalent cutoffs, malformed/naive timestamps,
unknown/future availability, future publications and revisions, future value
invariance, null/zero NAV, complete provenance, Decimal precision, bundle integrity,
idempotency, import rollback, source database preservation, allowlists and output
path isolation. The three existing offline suites remain regression checks.

Actual verification on 2026-10-08 with Python 3.13.13:

```sh
# Repository root
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services python -m unittest discover -s tests -t . -v
# Ran 129 tests in 0.115s; OK; exit 0

# research/events/2026-09-17-spk-liquidations/price_detectors
PYTHONDONTWRITEBYTECODE=1 python -m unittest test_detectors -v
# Ran 9 tests in 0.295s; OK; exit 0

# docs/handoff-v0.5
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
# Ran 88 tests in 0.003s; OK; exit 0
```

Total: 226 passing tests, including 48 new slice-A methods. An independent review
also ran those 48 methods successfully. A separate subprocess smoke test invoked
the actual import CLI twice against a temporary, explicitly marked synthetic
price file: both exit codes were 0, the bundle ID was identical, the cursor returned
zero records before availability and two at availability, and null NAV was retained.
The temporary database and fixture were removed after verification.

All 216 frozen manifest entries still match their bytes and SHA-256 fingerprints.
All six new Python files parse successfully. No real local-data import, download or
detector evaluation was executed for this slice.

Not validated here: provider rights, historical TEFAS publication times, complete
KAP revision archives, live ingestion, detector accuracy, API/UI, external email,
deployment, competition eligibility or the pending company-level evaluation split.

Next task: admit verified source versions/timestamps where available, then propose
slice B against the same bundle/cursor boundary. Do not evaluate unopened funds or
change frozen detector registrations as part of this slice.
