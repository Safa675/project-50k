# Disclosed-security concentration in the local fund app

Owner-authorized on 2026-10-09. Implemented as a bounded local research extension.

Add descriptive AN-FND-006 / FR-038 research to the approved local top-100 app.
FR-018/019 source dates, FR-078 fund-page context and NFR-038 cutoff checks are
partial contributions; no frozen requirement status or release gate is upgraded.

The first slice reads the supported monthly security tables from existing KAP
PDFs, computes identified-security top-1/top-5/top-10 and HHI with explicit
portfolio coverage, and displays them on the list/detail pages. Company/issuer
mapping is unknown. Partial scope cannot become a full-fund concentration claim.
No concentration alarm threshold is selected from the already studied outcomes.

Implementation plan:

- New geometry-aware provider and synthetic parser tests.
- New descriptive concentration arithmetic and sealed extension modules; preserve
  all v1 manifested calculation sources and the original bundle.
- New registered offline runner using selected existing monthly sources only.
- Strict API/client extension, neutral list metric, dated detail/source panel.
- Synthetic arithmetic, replay, source, API and UI tests, followed by independent
  private arithmetic/source checks and actual local browser verification.

Ambiguities resolved before implementation: securities versus issuers, identified
  subset versus full portfolio, monthly versus weekly cadence, stale snapshots,
  repeated lots/totals, signed holdings, derivative notionals, missing source
  identities, unknown historical versions and undefined alarm threshold. The
registered [protocol](../../research/events/2026-09-17-spk-liquidations/fund_concentration_app/PROTOCOL.md)
records the conservative interpretation. Unsupported evidence remains unknown.

## Implemented behavior

The list retains all 100 funds and adds the largest-five share alongside readable
portfolio coverage. The detail page shows largest-one/five/ten shares, HHI,
aggregated ISIN positions, source rows, the monthly period, publication timestamp,
snapshot age, limitations and the exact original PDF. Existing finding filters,
D1/flow results, comments, charts, assessment counts and ordering are unchanged.

The new runtime was committed before calculation. A first diagnostic run exposed
an overbroad period check that treated inception dates as reporting periods.
The committed repair reads only the audited monthly masthead and rejects missing,
contradictory or future periods. Exact printed fund codes establish identity when
names are abbreviated; contradictory codes cannot be bypassed by body text.

The registered run produced **20 PARTIAL, 80 UNAVAILABLE and 0 AVAILABLE**
concentration records. These are data-coverage statuses, not risk classifications
or fraud detection accuracy. No security-subset result represents the whole fund.
Unsupported layouts, unreconciled tables, negative positions, ambiguous
attachments and absent selected reports remain unavailable. No older successful
report silently substitutes for a selected source that failed.

An independent private scanner reproduced every readable fund's ISIN aggregation,
position count, largest-one/five/ten shares, HHI, coverage and ordering from the
original PDFs using Fraction arithmetic. **20/20** metric sets and source
period/publication checks matched; **206/206** returned contributing row values
matched the original PDF coordinates. No audit issue was found. All 100 original
record cores and original summary fields were compared and remained identical.

Changed implementation areas: `services/p50k/providers/security_holdings.py`,
`services/p50k/research_reviews/concentration.py` and `bundle_v2.py`, the new
registered runner, API models/routes/app, frontend contract/client/list/detail and
`ConcentrationPanel.tsx`. `FundList.tsx`/`Shell.tsx` also preserve the latest
filter choices through rapid edits, genuine history traversal and home navigation.
Tests use authored synthetic positions and reports.

## Verification

Executed on the laptop with the locked local runtimes:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/bin/python -m unittest discover -s tests -t . -v
# 584 tests, OK
```

From `research/events/2026-09-17-spk-liquidations/price_detectors`:

```sh
PYTHONDONTWRITEBYTECODE=1 /home/safa/Documents/project-50k/.venv/bin/python -m unittest test_detectors -v
# 9 tests, OK
```

From `docs/handoff-v0.5`:

```sh
PYTHONDONTWRITEBYTECODE=1 /home/safa/Documents/project-50k/.venv/bin/python -m unittest discover -s tests -v
# 88 tests, OK
```

The focused final provider/concentration/runner/API suite additionally passed
**81 tests**. Frontend `npm test`: **60 passed**; `npm run typecheck`: exit 0.
`NEXT_TELEMETRY_DISABLED=1 npm run build`: exit 0. Frontend
`npm run test:browser`: **31 passed** on the production build, including mobile
coverage/source details, exact PDF identity, missing results, filter/history
behavior and preserved two-finding semantics. The first browser run had 28 passes
and two failures: an obsolete two-cell missing-value assertion and a reproduced
Next.js URL restore race. Both were corrected; assertions were not weakened.

The actual sealed result passed the strict API contract for all 100 funds.
The local browser rendered the real list and partial concentration detail and
verified/rendered the exact nine-page PDF. Actual same-origin HTTP probes passed
for the complete list, summary, three bounded details and the PDF's response
hash/bundle binding. Private result fingerprints and full-precision ratios were
absent from static JavaScript assets. No source inputs were copied into builds.

All **2,088** baseline original input/reference files retained their SHA-256,
including the local snapshot SQLite and previous bundle. All **216** frozen
handoff manifest entries retained their SHA-256. The application serves the new
sealed local result at `http://127.0.0.1:3060/`; collection does not run at startup.

## Data mode and remaining scope

Private local archive research, cutoff 2026-09-16 23:59:59 Istanbul. Recorded source
dates are filtered; historical-version availability is UNKNOWN, point-in-time
verification is false, rights are UNKNOWN and production status is ABSTAINED.
The October-selected universe and current category labels retain their prior
limitations. Real inputs and outputs remain ignored/private under `raw/`.

Company/issuer aggregation, fund look-through, derivatives exposure, daily
position changes and historical concentration changes are unverified. There is
no registered concentration alarm threshold and no measured fraud success/error
rate. FR-038 is a descriptive research contribution; frozen requirements and
release gates are not marked complete. FR-108/109 are not satisfied by this slice.

The next recommended slice is to expand the reader to additional monthly report
layouts with synthetic reconciliation/source tests, then review issuer mapping
before claiming company concentration. No new collection, spending, public
release or push is included.
