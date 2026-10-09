# Top-100 fund research app: first prototype plan

Status: **P0–P5 implemented and verified locally on 2026-10-08.**
The owner authorized laptop implementation and approved the concrete list/detail
design ("design is okay go on"). All 100 funds, real API-backed detail, charts
and verified local PDFs are implemented. See the
[screen review](../docs/notes/top100-fund-app-design.md) and
[completion evidence](../docs/notes/top100-fund-app-completion.md).
Prepared: 2026-10-08. Target repository: `/home/safa/Documents/project-50k`.

## Goal and first delivery

Build a local Turkish web app where the owner can inspect all 100 already-opened
funds at a fixed nominal cutoff, see separate peer-return and estimated-flow
findings, and open the exact evidence behind each comment.

The first delivery has two screens and one cutoff:
`2026-09-16T23:59:59+03:00` (`Europe/Istanbul`). All 100 selected funds appear,
including funds with missing or insufficient inputs. A date selector is a later
slice; this version must not imply that arbitrary historical dates work.

The app is an **internal archived research demonstration**, not a verified
historical alarm system. Keep the strict evidence store and `ReplayCursor`
unchanged. Current archive versions, category membership and universe selection
do not establish what was historically knowable before the liquidation order.

## Existing foundation and traceability

- `services/p50k/evidence_store.py` and `replay.py`: existing evidence foundation;
  unknown historical availability remains excluded from admitted replay.
- `research/events/2026-09-17-spk-liquidations/price_detectors/`: frozen D1 code,
  preregistration and thresholds; reuse the method without tuning it.
- `services/p50k/detectors/fund_flow.py`: existing Decimal endpoint-change
  arithmetic; its production admission/baseline checks remain unchanged.
- `raw/tefas/prices/`, `raw/kap/reports/`, `raw/kap/series/`: local inputs only.
- At planning time no Project-50K API or frontend existed. The local research
  adapter, actual list/detail app and separately labelled synthetic preview now
  exist; executed verification is recorded in the completion note.

Related requirements, with partial coverage only:

- **FR-036, FR-037:** peer mapping and fund anomaly arithmetic. Historical peer
  membership, actual investor cash and a validated flow baseline remain unresolved.
- **FR-073, FR-074, FR-078:** explanations, evidence, NAV/peer charts and fund detail.
  Feedback, AI assistant and full production event functionality are deferred.
- **FR-018, FR-019, FR-108, FR-109, NFR-038:** source/time provenance, immutable
  bundles and cutoff tests. Research filtering does not satisfy verified replay
  admission, historical version timing or rights clearance.
- **FR-111:** explicit internal demonstration mode.

Do not edit the frozen handoff or upgrade requirement-registry statuses.

## Screen specifications

### Fund list

- Show the fixed cutoff and the Turkish label `Tarihsel arşiv araştırması`.
- Show all 100 codes/names and category labels, with the later-snapshot basis
  disclosed. Do not use current investor counts as a pre-crisis risk input.
- Columns: fund, category, D1 finding, signed estimated-flow finding, short
  deterministic Turkish comment, and missing/stale-data indication.
- Search by code/name; filter by category, two findings, one finding and
  insufficient evidence. Filtering does not alter the underlying universe.
- Default order: two eligible crossings, one eligible crossing, unassessable,
  then no crossings; ties by fund code. This is descriptive finding order,
  not a risk score. A known finding with another missing input stays one finding
  with an explicit incomplete-assessment label.
- Show total, assessable and unavailable counts with explicit denominators.
- Selecting a fund opens its detail page while retaining filter state.

### Fund detail

- Fund identity, fixed cutoff, summary comment and separate finding states.
- Fund and category-peer return context, clearly labeled and normalized from a
  common valid chart baseline; preserve missing segments. Do not equate the
  chart's normalized cumulative lines with D1's rolling-median statistic.
- D1 statistic, frozen threshold, actual observation window and peer coverage.
- July-to-August monthly asset/NAV inputs, signed endpoint-change estimate and
  the fixed screen boundary. Label it an estimate, not reported investor cash.
- Metric period, recorded publication date/time, retrieval/version provenance,
  and unknown historical availability shown separately.
- Source disclosure links and a manifest-backed local PDF viewer where an
  original PDF exists. A missing PDF stays missing.
- An unavailable chart retains its explanation and evidence panel.

Turkish comments come from tested templates and source-linked metrics. They
must distinguish a crossing, no crossing, stale evidence and insufficient data.
No buy/sell advice, safety verdict, fraud probability or invented explanation.

## Frozen calculation and joining policy

Commit a new bounded protocol before computing any new joined real-data output.
The protocol will bind the universe, code, source versions, stored thresholds,
cutoff, period selection, ordering, templates and counting rules.

1. **Universe:** only `top100_funds.txt`. Check membership before opening a fund's
   inputs. No statistics or reads of the 1,922 unopened price files.
2. **D1 at the cutoff:** use the frozen median excess-return method over the last
   60 positions in the shared TEFAS date calendar, not 60 consecutive calendar
   days; require at least 50 usable observations, at least 10 eligible peers and the
   original stored category threshold. Crossing is strictly above the threshold;
   equality is not a crossing. Do not recalibrate or use annual ever-fired flags.
   Missing calibration or category inputs produce an unavailable finding.
3. **D1 freshness:** retain the frozen statistic even if finite with a missing
   final observation. The new joining policy requires its latest contributing
   excess observation to be September 16. Otherwise show it as stale and disable
   the two-finding combination; do not alter the frozen detector.
4. **Flow context:** select only comparable consecutive July and August 2026
   monthly reports. Both recorded publication times must be unambiguously at or
   before the cutoff. Missing publication timing, missing endpoint, duplicate
   eligible report, invalid number or incompatible units/scope yields unknown.
   Do not substitute a weekly report, September report or earlier valid pair.
5. **Arithmetic:** reuse `A1 - A0 * (P1 / P0)` and its opening-asset ratio. The
   research screen remains `abs(rate) >= 0.10`. Positive and negative crossings
   have distinct inflow/outflow-estimate labels. Unknown action/distribution status
   remains an explicit qualification of conditional research arithmetic. Known
   noncomparable actions disable the finding; unknown status is never marked
   verified. Actual cash flows and the production baseline remain unverified.
6. **Combination:** two eligible crossings in this fixed-date view produce a
   descriptive two-finding comment. D1 and flow cover different windows, which
   must both be shown. Do not treat them as identical-period observations or claim
   that combining them improves detection before measuring it.
7. **Future invariance:** future observations, reports and post-order outcome
   labels cannot enter metrics, comments, charts or finding order. The liquidation
   list is not an input to the finding/comment rules. Current category/universe
   selection is a separately disclosed retrospective assumption.

All real production detector decisions remain `ABSTAINED`. The research screen
is a private arithmetic observation, not a production `TRIGGERED` event.

## Research data contract

Keep a separate `/research/v1` API; do not pretend the responses are the frozen
public-event contract or alter `contracts/openapi.yaml` under the handoff.

Every response carries:

```text
origin: HISTORICAL_REPLAY
analysis_mode: EXPLORATORY_ARCHIVE
cutoff_at: 2026-09-16T23:59:59+03:00
cutoff_semantics: RECORDED_SOURCE_DATE_FILTER
point_in_time_verified: false
historical_availability: UNKNOWN
rights_status: UNKNOWN
universe_basis: OCTOBER_2026_INVESTOR_SNAPSHOT
category_basis: CURRENT_SNAPSHOT
immutable_bundle_id: <content fingerprint>
```

Each finding carries `arithmetic_status: AVAILABLE|UNAVAILABLE`,
`research_screen: CROSSING|NO_CROSSING|UNKNOWN`, `freshness: FRESH|STALE|UNKNOWN`,
`production_status: ABSTAINED`, missing reasons, metric period, units, input
references, source hashes and publication/availability provenance. Serialize
Decimal financial quantities as strings; unavailable quantities are null.

Recorded publication filtering does not promote an unknown historical archive
version into admitted replay. Unknown publication timing disables that dated
finding; unknown version availability remains visibly unverified research.

The immutable private bundle and financial results live under
`raw/research/fund-review-app/<fingerprint>/`, never in tracked frontend source,
fixtures, screenshots or build assets. Tests use synthetic data only.

## Bilun reuse and application architecture

Reuse source from Bilun commit `cafa27bc`, with source attribution and applicable
notices retained. Do not copy its whole package/lock or installed dependencies;
the audit found installed-package drift. Resolve supported dependencies against
official documentation at initialization and commit the resulting lockfiles.

- Copy generic `DataTable.tsx`, `Toolbar.tsx`, `Chip.tsx`, `Stat.tsx`,
  `EmptyState.tsx`, `form.ts` and `cn.ts` from
  `/home/safa/Documents/Bilun/frontend/src/components/primitives/` and
  `/home/safa/Documents/Bilun/frontend/src/lib/` as appropriate.
- Extract only their required CSS tokens/table styles. Set a Project-50K theme;
  keep Bilun branding, sidebar/body offsets, patient/chat styles and domain-bound
  primitive exports out of the new app.
- Adapt the narrow JSON transport/error pattern from Bilun's `apiClient.ts` and
  same-origin proxy pattern from `next.config.ts`. New responses require runtime
  shape validation, not an unchecked TypeScript cast.
- Build new fund charts with the handoff's Lightweight Charts choice. Bilun's
  SUT pie chart is not a reusable fund/peer time-series component.
- Frontend: Next.js App Router, TypeScript, Tailwind/custom tokens, next-intl.
- Backend: thin FastAPI/Pydantic read-only adapter over a validated research
  bundle. Retain Project-50K arithmetic/evidence code as the domain foundation.
- App startup performs no downloads, detector recalibration, Bilun imports,
  health-data/cache rebuilds, database migration or account provisioning.

Run both processes on loopback only. Proxy browser `/api/research/...` requests
to the independent API. Allow only the local UI origin; private responses use
no-store caching. Validate selected fund codes and opaque manifest-backed source
IDs; never accept arbitrary filesystem paths or URLs. Do not modify or bypass
production authentication to make a demo run.

## Implementation slices and proposed file changes

The following file plan records the approved scope. P0–P5 are complete for the
private local prototype; production and public-release gates remain separate.

### P0 — protocol and screen review

- Add `research/events/2026-09-17-spk-liquidations/fund_review_app/PROTOCOL.md`.
- Add `docs/notes/top100-fund-app-design.md` with the two-screen hierarchy,
  Turkish copy, responsive/empty/stale/error states and selected Bilun primitives.
- Confirm the recorded research-contract exception and owner layout review before
  full UI implementation. Both were recorded before P3/P4; formal G09 audit work
  remains separate from the owner's concrete layout approval.
- Commit the protocol before new real joined calculations. No detector tuning.

### P1 — immutable research bundle and comments

- Add `research/events/2026-09-17-spk-liquidations/fund_review_app/run.py`.
- Add `services/p50k/research_reviews/{__init__,contracts,bundle,comments}.py`.
- Add synthetic `tests/unit/test_fund_review_bundle.py` and
  `test_fund_review_comments.py`.
- Produce exactly 100 records, explicit unavailable states, hashes and per-input
  provenance; independently verify arithmetic, alignment and summary counts.

### P2 — local read-only API

- Add `services/p50k/api/{__init__,app,research_routes}.py` and API contract tests
  under `tests/unit/test_research_api.py`.
- Routes: health, research summary, fund list, fund detail and manifest-backed
  source PDF. Each returns or binds the same immutable bundle/cutoff.
- Add a minimal `pyproject.toml`/dependency lock and a documented local launcher.
  Preserve standard-library-only core tests; document API-test dependencies.

### P3 — fund list

- Add `frontend/package.json`, lockfile, TypeScript/Next/CSS/test configuration.
- Add `frontend/src/app/{layout,page}.tsx`, selected copied primitives, a typed
  research API client and new list/search/filter/comment components.
- Show all 100 funds, state labels, source-date limitations and error/retry states.

### P4 — fund detail and evidence

- Add `frontend/src/app/funds/[code]/page.tsx`, fund/peer chart components,
  estimated-flow panel and source/evidence components.
- Add synthetic component/contract tests and browser end-to-end checks under
  `frontend/tests/`. Use one chart library; preserve gaps and precise unit labels.

### P5 — integrated verification and handoff

- Add `docs/notes/top100-fund-app-completion.md` with exact commands/results,
  partial requirement coverage, source modes, limits and remaining gates.
- Update the repository README with the local run procedure and missing-data
  setup; no database or real-data migration is required.
- Next proposed slice: a date selector with separately preregistered per-date
  period/freshness selection and invariant tests. Do not silently enable it here.

## Acceptance tests

- All 100 rows and detail routes exist even with absent files, bad numbers,
  insufficient peers or missing reports. Missing NAV is never a zero return.
- D1 synthetic equivalence with frozen code; 50/49 observations, 10/9 peers,
  strict threshold equality, missing calibration and finite-but-stale output.
- Exact positive/negative flow boundary crossings and signed Turkish comments;
  null/nonfinite/zero NAV, incompatible units and unsupported actions stay unknown.
- Missing July/August, duplicates, weekly/September reports, missing publication
  time and late publication cannot enter the selected monthly finding.
- A past annual D1 alarm cannot create a current two-finding comment. Missing or
  stale evidence cannot be converted into a negative finding or a safety verdict.
- Mutating future values/reports/outcome labels leaves all cutoff metrics,
  comments, eligible record references, charts and ordering unchanged. Whole-file
  hashes and bundle fingerprints may differ for a newly constructed bundle;
  existing sealed bundles remain immutable and reject changed source bytes.
  Strict `ReplayCursor`
  still excludes unknown availability and the production flow evaluator abstains.
- Reject unopened fund codes before source reads; reject corrupt bundle hashes,
  missing fingerprints, unknown source IDs and path/URL traversal.
- API/runtime response validation rejects malformed numeric/status/unit fields;
  list and detail show the same bundle, cutoff, values and missing reasons.
- Browser checks cover search, category/finding filters, navigation/back, no
  matching search results, API unavailable, absent PDF, and gapped charts.
- Keyboard navigation, visible focus, mobile layout, contrast and natural
  Turkish copy are reviewed. Significance is not conveyed by color alone.
- Offline operation after bundle creation; no real finance values in Git/build
  assets, no Bilun source/data changes and no outbound delivery or deployment.

Run the existing regressions after relevant implementation changes:

```sh
# Repository root
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services /home/safa/miniforge3/bin/python3 -m unittest discover -s tests -t . -v

# research/events/2026-09-17-spk-liquidations/price_detectors
PYTHONDONTWRITEBYTECODE=1 /home/safa/miniforge3/bin/python3 -m unittest test_detectors -v

# docs/handoff-v0.5
PYTHONDONTWRITEBYTECODE=1 /home/safa/miniforge3/bin/python3 -m unittest discover -s tests -v
```

Add the new API/TypeScript/unit/browser/build commands to the implementation
record with actual locked tools. A test named in this plan is planned, not passed.

## Decisions and boundaries before implementation

- The initial request to write this plan did not authorize implementation.
  Subsequent owner requests authorized implementation on the laptop, and the
  concrete list/detail layout was approved before P3/P4. The fixed cutoff,
  July/August pairing, freshness, finding order and internal research contract
  were implemented as specified.
- Owner layout approval is recorded; formal G09 audit/designer work remains
  incomplete. Preserve G01 competition eligibility and all source-rights/public-
  release gates; private implementation clears none of them.
- Bilun `LICENSE` is proprietary while its Python project metadata declares MIT;
  do not propagate that inconsistent metadata or infer public redistribution rights.
  Any later public distribution requires an explicit applicable license decision.
- Public hosting, LAN exposure, accounts, spending, production auth, push/merge,
  public real-data release and notifications are separate owner decisions.
- The unresolved development/test split stays unresolved. No new target-based
  tuning, holdout opening, fraud accuracy or false-alarm claim is authorized.
- Scope/currency/actions, historical categories/universe, archive revisions and
  the AN-FND-002 baseline remain evidence limitations, not silently true assumptions.

## Definition of done and current record

The local app starts with documented commands, shows the same fixed-date bundle
for all 100 list/detail records, explains available and unavailable findings,
opens eligible sources and passes the relevant regression/browser checks.
Completion includes the exact verification output and unresolved limitations.

The approved local prototype is implemented. Verification passed: 600 Python
regression tests across the root and frozen suites, 47 frontend unit tests,
26 production-build browser tests, typecheck and optimized build. Actual
100-record API/source consistency and private input/frozen-manifest hashes were
also checked. Full commands, results and limits are in the completion note.
Data mode remains `HISTORICAL_REPLAY` + `EXPLORATORY_ARCHIVE`; rights remain
UNKNOWN; migrations: none. Frozen handoff, detector thresholds and original
private archives are unchanged. The optional date-selector slice is not included.
