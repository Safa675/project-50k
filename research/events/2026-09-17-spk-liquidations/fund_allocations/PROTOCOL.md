# AN-FND-004 monthly-average allocation research protocol

Registered on 2026-10-08 before any allocation distance, threshold crossing or
ranking from the local fund PDFs. Owner approved this slice in chat.

## Scope and immutable choices

- DEC-024: Turkish funds only. The selected universe is the existing committed
  `research/events/2026-09-17-spk-liquidations/top100_funds.txt` (100 codes).
  No other price files or funds are evaluated. No new download is required.
- Use the original selected funds' KAP report-list metadata and associated PDF
  attachments under `raw/kap/reports/`. Do not reuse the headline series' implicit
  selection among duplicate disclosures as proof of a unique allocation version.
- Closing periods: October 2025 through September 2026 inclusive. September 2025
  is an opening endpoint only. Attempt all 12 scheduled consecutive monthly pairs
  for each selected code, including explicit missing-month attempts.
- Admit only monthly report metadata (`period=AB`, valid year/month); exclude
  weekly reports and retain exclusion counts. Match disclosure ID, reported
  period, selected fund identity and exact associated attachment filename.
- Parse the published **monthly-average asset-type percentage table** identified
  by its semantic heading. Its section letter can vary. Do not use month-end
  security holdings, turnover percentages, or investor-information-form charts as
  interchangeable allocation observations.
- Preserve printed category labels and percentages, page/rectangle references,
  publication strings, disclosure IDs, source hashes and parsing limitations.
  Category keys use orthographic normalization only. No semantic category merge,
  imputed zero, discarded negative position, percentage repair or renormalization.
- The complete parsed table must have nonnegative finite percentages that sum
  **exactly to 100**; fractions are the exact printed percentages divided by 100.
  Rounded totals above or below 100 are noncomputable in this first version.
  Both tables must have the same nonempty reported category set/schema and basis.
  A changing sparse table cannot silently imply zero for omitted categories.
- Unsupported layouts, ambiguous cells, duplicate category labels, multiple
  plausible tables/attachments, and multiple monthly disclosures remain explicit
  noncomputable cases. Do not choose a version by highest ID, best score or most
  convenient numbers.

## Fixed calculation and threshold

FR-035 / AN-FND-004, with FR-037 calculation and NFR-038 replay guards:

```text
delta(category) = current_fraction - previous_fraction
D = 0.5 * sum(abs(delta(category)))
maximum_category_change = max(abs(delta(category)))
screen_crossing = D >= 0.20 OR maximum_category_change >= 0.20
```

The 0.20 threshold is the literal catalog heuristic, not a tuned value or a
validated fraud cutoff. Category change uses **percentage points**, not relative
percent change. D measures a change between published composition observations;
for this research they are monthly averages. It is not actual turnover, an exact
trade date, estimated investor cash flow, or misconduct.

Do not modify the frozen price detectors, their registrations, AN-FND-002 or the
frozen handoff. No threshold/window/universe changes after outcomes are seen.
Parser corrections must address a documented extraction error, retain synthetic
regression coverage and be disclosed in the result's code fingerprint.

## Counts and presentation

- Count selected/source/parsed funds, scheduled pairs, calculable/noncomputable
  pairs, parsing reasons, duplicate metadata/attachments and weekly exclusions.
- Distinguish latest scheduled period, latest reported period and latest valid
  earlier pair. A stale valid pair is never presented as the latest observation.
- Separately count the eight already known liquidation-list targets and the other
  selected funds. The latter are not known-clean controls. Neither group is a
  fraud label. Report the denominators and missingness.
- Report per-period crossings and any-period crossings; preserve signed category
  changes. Rank only calculable observations by D descending, then maximum
  category change descending, then code and closing period ascending. Rankings
  are exploratory composition changes, not ranked fraud likelihood.
- Named private results may include selected funds; committed findings name only
  the existing eight targets. No original KAP/TEFAS value is committed.
- No classifier accuracy, false-positive rate or independent validation claim.
  No threshold fitting on targets, no sealed-test run or broader-universe analysis.

## Time, rights and output boundary

Original source bytes are read-only. The current archive does not establish full
historical versions or first availability. Preserve displayed publication times
without turning report periods into invented historical receipts. Research
arithmetic is `EXPLORATORY_ARCHIVE`, origin `HISTORICAL_REPLAY`, rights `UNKNOWN`;
every real production status remains `ABSTAINED`. A nominal period before the
SPK order does not establish an alert made or knowable before that order.

The service evaluator separately admits only immutable ReplayCursor observations
with verified timing/rights, comparable category basis/schema, complete weights,
scope and monthly periods. Missing/future/ambiguous evidence produces ABSTAINED
without numeric metrics or future evidence IDs. No baseline rule from AN-FND-002
is invented for AN-FND-004. This slice does not create public FR-064 events,
external alerts or a live product.

Private results live under gitignored
`raw/kap/allocation-analysis/{fingerprint}/results.json`. Preserve protocol,
universe, runner/core/parser and source hashes. Require this committed protocol's
exact SHA-256 before a real run. Output creation is atomic/idempotent and refuses
input aliases or foreign/conflicting existing results. No overwrite of raw inputs,
other research results, SQLite databases or the unrelated research brief.

## Acceptance

Synthetic tests cover fixed-threshold boundaries, identical distributions,
negative/nonfinite/missing values, mismatched schemas, non-unit sums, parser
column isolation and alternate layouts, duplicate/ambiguous sources, weekly/gap
exclusions, source preservation and idempotent output. Replay tests ensure later
observations/revisions cannot change a frozen earlier decision. Run the three
repository regression suites and verify a sample of private PDF-derived results
independently. Report actual failures and exclusions; never describe abstention
as a normal or safe fund.
