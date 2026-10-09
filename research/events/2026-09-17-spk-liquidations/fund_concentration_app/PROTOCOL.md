# Descriptive disclosed-security concentration for the local fund app

Registered on 2026-10-09 before any real concentration result is calculated.
The owner authorized adding AN-FND-006 to the existing local application in chat.
Scope: FR-038, FR-018/019, FR-078 and NFR-038 research contributions, not completed
public-product requirements or a validated fraud detector. DEC-024 applies.

## Universe and preservation

Use exactly the 100 opened codes in `../top100_funds.txt`. Check membership before
reading a fund input. Do not open the other 1,922 downloaded price files. No new
download, remote deployment, notification, account, spending or push is included.
Source PDFs and parsed numeric output stay private under ignored `raw/`.

The input is the existing sealed `p50k.fund-review.v1` bundle. Extend its records
without recalculating or changing D1, flow, charts, comments, assessments, finding
counts or ordering. Existing two-finding filters continue to describe D1 and flow
only. The old bundle and its manifested runtime files remain unchanged. A new
versioned concentration extension, protocol/code/source hashes and base-bundle
identity are included in a newly sealed content-addressed bundle.

Locally commit this protocol and every concentration runtime source before the
first real run. Registration fails if working bytes differ from committed HEAD.
No outcome label, SPK list, subsequent price or current investor count enters
selection, parsing, concentration or comparison. Existing development outcomes
cannot choose a threshold. The catalog supplies no concentration alarm threshold;
the extension is `NOT_SCREENED`, with production status `ABSTAINED` throughout.

## Snapshot selection and timing

Retain the existing cutoff `2026-09-16T23:59:59+03:00` and its recorded-source-date
filter, historical availability UNKNOWN, point-in-time verification false and
rights UNKNOWN. Acquisition time does not prove the original version existed at
the cutoff. Current category and October-selected universe labels remain.

For each fund, select the latest monthly (`AB`) reporting period whose month-end
and unambiguous recorded publication timestamp are both at or before the cutoff.
Select the immediately preceding eligible monthly period separately for optional
comparison. Multiple eligible disclosures for one selected period are ambiguous.
Do not choose an older successfully parsed report when the selected latest source
is missing or unsupported. Do not silently replace monthly data with weekly data.
Offset-free provider dates use the existing disclosed Istanbul-time assumption.

Use the original KAP list and matching original PDF under `raw/kap/reports/`.
Missing list, timing, identity, attachment or PDF remains unavailable. Show report
month-end, publication timestamp, age in calendar days, cadence and source links.
Older monthly reports are identified by age; no empirical freshness threshold is
invented. Weekly holdings and historical revisions are outside this first slice.

## Parser and economic scope

The first reader supports the audited 950-by-1200 monthly KAP table profile.
Read only section III through its portfolio-value footer before section IV.
Later purchase/sale tables cannot supply current holdings. Preserve native
instrument labels, ISIN, row values, source page/rectangle and signed rows.
Group/class totals are reconciliation rows, not additional holdings. Repeated
totals cannot be double-counted. Validate the source portfolio footer against the
section-IV portfolio value and position/group sums within printed rounding bounds.
Unsupported layouts and ambiguous or contradictory rows have explicit reasons.

Eligible instruments are identified spot equities, bonds, fund units and other
verified securities. Aggregate identical ISIN lots; never infer issuer identity,
corporate-group membership or beneficial owner from an ISIN. This is security
concentration, not yet company concentration. Repo collateral, deposits, cash,
money-market transactions and derivatives do not become owned security positions.
Keep their presence and unidentified rows visible. Derivative notionals never
become asset value or collateral P&L. Do not absolute-value negative positions.

## Arithmetic and completeness

For a reconciled, nonnegative readable table, let S be the sum of strictly
positive eligible identified security values. Each security weight is value/S.
Compute top-1, top-5 and top-10 weights and HHI=sum(weight squared), using isolated
high-precision Decimal arithmetic. These describe the identified-security subset.
Always display that denominator alongside its coverage S/reported portfolio value.
Do not present a subset HHI or top-five share as a full-fund concentration metric.
Ties are ordered by ISIN for reproducibility. Printed zero rows add no exposure.

`AVAILABLE` requires a fully reconciled positive spot portfolio with no positive
unidentified/nonsecurity exposure or derivatives. `PARTIAL` permits valid subset
arithmetic with explicit missing/nonsecurity/derivative coverage qualifications.
Negative positions, reconciliation problems, nonpositive/invalid denominator,
unknown source identity and ambiguous parsing yield `UNAVAILABLE` numeric metrics.
No available security subset also yields unavailable, never a zero concentration.
If read coverage exceeds the portfolio beyond its rounding bounds, abstain.

Retain at most the ten largest aggregated securities in the response, with source
row references for all contributing lots. Optional prior-period changes require
both snapshots AVAILABLE, the same economic basis and compatible currency/scope;
otherwise comparison is unavailable with reasons. Never claim daily trading or
the time a concentration changed from two published monthly snapshots.

## Application and sources

All 100 funds remain visible. Add a neutral list metric and a detail section with
top positions, subset shares, coverage, source dates, unknown/partial reasons and
the original verified PDF. No high-risk/fraud labels, numerical alarm, probability,
buy/sell advice or additional independent finding count is introduced. Two-finding
filter semantics remain unchanged. Old bundles expose an explicit uncalculated
concentration state and remain loadable.

Every response binds the same new bundle and cutoff. Source IDs remain opaque,
fund-scoped and manifest-backed. Strict API and browser validation checks all
concentration source references, dates, status/metric consistency and exact source
union. No HTTP input can request arbitrary paths or computation. Startup serves
sealed results without collection. Real data cannot enter Git or build assets.

## Acceptance fixed before calculation

Synthetic tests cover duplicated ISIN lots, top-N ordering/ties, exact HHI,
zero versus missing, partial denominators, negative positions, repo/derivative
exclusion, unsupported geometry, wrapped ISIN rows, group/portfolio reconciliation,
future publication/period exclusion, duplicate reports, selected-latest failure,
unopened-code rejection and future-value invariance. Test old-bundle compatibility,
unchanged D1/flow/core summaries/order, source isolation/corruption, nullable old
responses, partial/unknown UI, verified PDF access, keyboard and mobile layout.

Run repository, frozen detector and frozen handoff tests, locked frontend checks,
production browser tests and actual local UI probes. Independently recompute
concentration arithmetic and check original source-row samples. Report actual
coverage separately from accuracy; no fraud success rate is inferred. Preserve
raw inputs, the snapshot SQLite, frozen handoff bytes and prior sealed results.
