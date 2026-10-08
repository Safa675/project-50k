# Fixed-cutoff top-100 fund review: bounded joining protocol

Registered: 2026-10-08, before any newly joined real-data bundle is calculated.
Owner authorized laptop implementation of the existing app plan in chat.
Scope: private, local archived research; DEC-024, Turkish funds only.

## Authority and immutable inputs

The plan is `plans/2026-10-08-top100-fund-research-app.md`. Its fixed-date,
July/August, signed-flow, freshness and descriptive ordering choices are retained.
The earlier planning-only status is historical. The separate internal research
contract is authorized by the implementation request. G09 design review remains
pending until a concrete scaffold is reviewed; no competition or public-release
gate is cleared by this protocol.

The universe is exactly the 100 unique codes in `../top100_funds.txt`. Validate
membership before opening any fund input. Do not read or calculate the other
1,922 downloaded price files. Names/categories come only from the selected
snapshot records in the existing private SQLite database. No current investor
counts, liquidation outcomes or other outcome labels are finding inputs.

Bind each private bundle to the SHA-256 of this protocol, the universe, the
original stored `../price_detectors/results.json`, frozen detector source, new
runner/domain source, and every consumed source byte. Use the stored D1 category
thresholds; never run calibration or overwrite prior results. Implementation
source and protocol must be locally committed before the first real bundle run.

Inputs: selected `raw/tefas/prices/{CODE}.json`,
`raw/kap/series/{CODE}.json`, selected original report lists/acquisition metadata
and PDFs under `raw/kap/reports/{CODE}/`, and selected snapshot records. Missing
files remain unavailable. Do not download replacements or change input bytes.
Do not follow symlinks to arbitrary inputs or accept paths/URLs from an HTTP
client. Existing repository layout aliases are not a new input root.

## Cutoff and provenance

Nominal cutoff: `2026-09-16T23:59:59+03:00`, Europe/Istanbul. TEFAS dated rows
through September 16 are usable for this recorded-date filter only. Prices after
that date do not enter the calendar, calculations or charts. Missing, invalid,
nonfinite or nonpositive NAV remains missing; no gap filling or zero returns.

KAP publication timestamps must parse unambiguously and be at or before the
cutoff. Offset-free KAP provider timestamps are interpreted as Europe/Istanbul
with that interpretation disclosed separately. Missing, malformed or ambiguous
publication timing excludes that endpoint. Retrieval time and recorded
publication are different metadata; the later retrieval does not establish
historical availability of the archive version.

Every response/bundle retains:

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
immutable_bundle_id: content fingerprint
```

The underlying snapshot was collected in October; the basis label describes
that retrospective selection rather than claiming a historically dated universe.
Strict `ReplayCursor` and production admission are unchanged. All real
production decisions remain `ABSTAINED`, including arithmetic screen crossings.

## D1 calculation, coverage and freshness

Use the frozen `detectors.py` functions: log NAV returns on the shared calendar,
own-fund exclusion from the same-category peer median, at least 10 usable peers
per date, and median excess over the final 60 shared-calendar positions through
the cutoff with at least 50 usable excess observations. A category requires at
least 11 selected members and an existing finite stored D1 threshold.

A crossing is strictly greater than the stored category threshold. Equality is
no crossing. Missing category, calibration, coverage or cutoff observations
produce explicit reasons. Do not use an annual ever-fired flag for this view.

If the frozen statistic is finite but its latest contributing excess observation
precedes September 16, preserve that statistic and mark it `STALE`. A stale D1
cannot contribute to the eligible combined-finding count. Show window bounds,
usable observation count and peer coverage. Do not change the frozen method.

Chart context uses only cutoff-eligible dated rows, normalized to 100 at a common
valid fund/peer baseline within the displayed D1 window. Peer context excludes
the fund and uses the same minimum peer coverage. Missing returns remain gaps;
do not bridge missing observations or turn them into flat lines. Label normalized
cumulative context separately from D1's rolling median excess statistic. Missing
common baseline or chart coverage leaves an unavailable chart and evidence panel.

## Estimated July-to-August flow

Select exactly one eligible monthly (`AB`/MONTHLY) July 2026 endpoint and one
August 2026 endpoint, with both recorded publication times through the cutoff.
Multiple eligible reports for either month make the pair ambiguous/unavailable.
Exclude weekly reports and other months; do not substitute an earlier valid pair
or September endpoint. An endpoint published later is not eligible and its
numeric values or reference must not affect the dated finding.

Reuse Decimal `calculate_endpoint_change(A0, A1, P0, P1)`:
`residual = A1 - A0 * (P1/P0)` and `rate = residual/A0`.
Opening assets and both NAVs must be finite positive values; closing assets may
be zero but never negative. Financial outputs are decimal strings or null.

Fixed descriptive research screen: `abs(rate) >= 0.10`. Equality crosses.
Positive crossings are an estimated-inflow observation; negative crossings are
an estimated-outflow observation. Neither is a reported investor cash figure.
Display the distinct July/August period and both recorded publication times.

Known mismatched currency, units, fund/share scope, valuation basis, distribution,
unit changes or merger actions disable the flow finding. Missing field values or
invalid numbers disable arithmetic. Unknown accounting/action evidence remains
visibly conditional and never becomes verified comparability. Where the existing
extractor supplies no explicit currency/scope metadata, show that missing metadata
and the common-report-field assumption; do not invent a verified currency or
corporate-action clearance. An explicitly incompatible field overrides assumptions.
No production baseline policy is created or marked validated.

## Comments, combination, ordering and denominators

Deterministic tested Turkish templates use only eligible metrics and explicit
missing/stale reasons. They never infer fraud, safety, causality, buy/sell advice,
success rates or outcome labels. Keep D1 and flow windows distinct.

Eligible crossing means available arithmetic, crossing screen and fresh required
evidence. Count two eligible crossings, one eligible crossing, no eligible
crossings with an unavailable/stale component (unassessable), then two assessable
noncrossings. Order in those groups and then by fund code. A known crossing with
another unavailable component remains one finding with an incomplete-assessment
label. A stale crossing is shown separately but not counted as eligible.

Exactly 100 records remain present. Summary counts disclose denominator 100,
separate D1 and flow assessable counts, both-assessable count, each combined group
and missing/stale counts. Search and filters do not redefine the universe or
recompute thresholds. No numerical risk score is added.

## Sealing, sources and runtime boundary

Private output: `raw/research/fund-review-app/<fingerprint>/`. Canonical JSON,
manifest hashes and opaque source IDs bind the exact bundle. Creation is atomic;
an identical run reuses identical bytes. Reject corrupt, conflicting or mutated
sealed bundles and changed manifest-backed source bytes. Validate selected fund
codes and source IDs. The API cannot read arbitrary file paths or URLs.

Original PDFs may be copied byte-for-byte into the ignored sealed bundle or
bound by validated manifest paths and hashes. A missing original remains missing.
Only selected eligible evidence can be linked. List, detail, summary and source
routes bind the same bundle and cutoff. Use no-store responses and loopback-only
API/UI processes. Startup performs no data acquisition or recalculation.

No real financial quantities, named non-target findings, private SQLite, raw
files, screenshots of real values or baked data enter Git/build assets. Synthetic
tests use invented fund identifiers and values. Bilun source remains unchanged;
only approved generic building blocks and necessary notices are adapted.

## Verification fixed before calculation

Test frozen D1 equivalence; 50/49 observations; 10/9 peers; threshold equality;
missing calibration; stale finite output; flow positive/negative exact boundaries;
bad or missing numbers; publication cutoff; duplicate/month/cadence selection;
known incompatibility; unknown assumptions; ordering/comments/count identities.

Mutating future prices, reports and outcome labels cannot change dated metrics,
eligible references, charts, comments or order. Whole-source fingerprints may
change for a new bundle, but a sealed bundle is immutable. Independently reproduce
arithmetic and summary counts; check all 100 list/detail records. Test corruption,
unknown/unopened codes, source traversal, response validation, error/no-store
behavior, filters/navigation, missing PDFs, gapped charts, keyboard and mobile.

Run existing root, frozen price and frozen handoff regressions plus locked API,
frontend typecheck/unit/build and actual browser checks. Report only executed
results, provenance limitations and partial requirement coverage. Do not modify
the frozen registry. No database migration, external notification, deployment,
spending, account creation, public hosting or repository push is part of this run.
