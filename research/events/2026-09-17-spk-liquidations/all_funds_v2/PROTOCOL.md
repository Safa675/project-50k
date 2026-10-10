# All-fund price evidence v2: parameters fixed after the event

**Recorded:** 2026-10-10, Europe/Istanbul, before any all-fund statistic or percentile is computed.
**Authority:** DEC-028/029/030 and build-plan D8. This file is committed alone and is immutable thereafter.
**Scope:** T2.1/T2.2; D1–D5, AN-DQ-001/002 and confirmed AN-FND-005 evidence.

## Already seen before writing this

- The frozen 100-fund protocol, detector code, category thresholds and results.
- The SPK order of 17 September 2026 and its 131 mapped funds.
- The prior THF/TP2 price and KAP case studies and the research app.
- Current fund-list/category/status metadata, archive structure, row counts and missing-value counts.
- Phase 1 imports, including the candidate event mapping. The closest-name identity is approved;
  ten exact-name human spot checks remain outstanding.

No all-fund detector statistic or percentile has been computed for this protocol.
This is development exploration on all opened funds, with no independent holdout.
Never call these thresholds preregistered before the event, validated accuracy or lead time.

## Universe, provenance and point in time

- All funds in the archived 2026-10-06 TEFAS fund list. A missing price file does not remove a fund:
  its coverage states remain visible and abstain where necessary.
- One category source only: `fonTurAciklama` from that listing, replacing the frozen study's
  snapshot `fonKategori`. Categories, constituents and TEFAS status are current retrieved metadata,
  not historical membership. All peers are other listed funds in the same category.
- Daily published NAV only; zero, null and nonfinite prices remain missing. No interpolation,
  zero filling, intraday prices, rank history, AUM history or investor-count history is invented.
- Price availability is the imported explicit rule: positive row D from about 11:05 Istanbul on D;
  an explicit missing row is known only from archive acquisition. Unknown availability is excluded.
- Select only observations with `available_at <= cutoff` and effective date no later than the cutoff.
  Published KAP/event evidence follows its publication availability; an unknown timestamp remains unknown.
- Revisions are selected deterministically by latest eligible availability then observation time. Conflicting
  values tied on those times cause abstention for that fund/date rather than an arbitrary winner.
- The calendar is the union of eligible dated price rows up to the cutoff. A return uses the preceding
  calendar row, not the previous nonmissing price. Gaps therefore break a return.
- Input watermarks and fingerprints include observation identities, hashes, values and availability.
  Runs retain protocol/code/version references and cutoff. Later observations cannot change a stored run.
- `DELAYED` describes current published archive data with its last actual date. `HISTORICAL_REPLAY`
  requires an explicit cutoff and excludes later fund status from evidence. This is not a validated replay.

## Fixed math

Let r(d) = ln(P(d)/P(d-1)) when both adjacent calendar prices are positive and finite.
For each fund, m(d) is the median of other same-category returns at d with at least ten eligible peers;
e(d) = r(d)-m(d). Windows end at d and contain calendar rows, including gaps.

| ID | Statistic | Admission | Comparison |
|---|---|---|---|
| D1 | Median e over the last 60 rows | At least 50 finite excess values; current r and m defined | Strictly above category 99th percentile |
| D2 | D1 median minus median e over the 120 rows immediately preceding its 60-row window | At least 50 current and 100 preceding values; current r and m defined | Strictly above category 99th percentile |
| D3 | Lag-one Pearson correlation of r over the last 120 rows | At least 100 finite pairs; current r defined | Strictly above category 99th percentile |
| D4 | Pearson correlation of r and m over the last 120 rows | At least 100 finite pairs; current r and m defined | Strictly below category 1st percentile |
| D5 | Calendar days since first eligible positive archived price | A first eligible price | Attribute only; short visible history when below 730 days |

Correlation with zero variance is undefined and abstains. Exact constant finite windows are detected
by equal minimum/maximum, including decimal windows where floating standard deviation rounds away from zero.
Math may use NumPy floating arithmetic; stored scalar results use decimal strings, never rounded for comparison.
Scores may be optimized only with synthetic equality/look-ahead tests against the frozen formulas.

D5 measures visible archive history, a lower bound on age, not verified inception. It never fires an anomaly:
its covered state is `NOT_TRIGGERED` with `is_attribute=true` and the short-history value; unavailable history
is `ABSTAINED`. It is excluded from counts of triggered anomaly detectors.

## Calibration fixed once

- Calibration dates are strictly before 2025-10-06. No value from that date or later enters a percentile.
- Use every eligible finite statistic from each category's listed funds, with those same windows and peers.
- Percentiles use NumPy's linear method: 99 for D1/D2/D3, 1 for D4; ties do not trigger.
- A category needs at least 1,000 finite statistic values from at least five contributing funds.
  D1/D2/D4 additionally need at least eleven category funds so ten other peers can exist.
- Missing category, insufficient peers, insufficient history, zero variance, ambiguous revisions or absent
  thresholds produce `ABSTAINED` with an explicit reason. No threshold is borrowed from another category.
- Store one immutable version containing parameters, category thresholds and the calibration input fingerprint.
  Subsequent runs, including overnight refreshes, load it unchanged. They never recalibrate this version.
- If setup cannot finish by the plan's fallback gate, a separate disclosed frozen-threshold mode is required;
  that is not an unrecorded change to this protocol.

## Data-quality and event states

- AN-DQ-001: stale daily price when at least two weekdays after the last eligible positive NAV have elapsed
  before the cutoff date. Weekends are excluded; official holidays are unverified and the limitation is shown.
  No positive history means abstention. This is an operational data warning, never liquidation evidence.
- AN-DQ-002: the latest eligible explicit row has missing NAV, or no admissible price history exists.
  Such missing input is `TRIGGERED` as a data-quality warning. A complete latest row is `NOT_TRIGGERED`.
- D1–D4 require their current return and any needed current peer median. Missing current input abstains even
  when an earlier rolling window could still produce a score. The last actual eligible calendar date is labelled.
- AN-FND-005: only a human-`CONFIRMED`, in-scope SPK liquidation/access event with known eligible availability
  can be `TRIGGERED`. Candidates and unknown publication times abstain. No event in the single-bulletin archive
  also abstains with source-scope-limited coverage, not a claim that the fund has no regulatory events.
- Source scope is the locally archived SPK 2026/61 order only. Downloaded PDFs create no automatic events.

Every result stores `TRIGGERED`, `NOT_TRIGGERED` or `ABSTAINED`, reason, value/threshold where defined,
evidence ID, effective date, cutoff, version, source references and coverage. Evidence and results are append-only.
Human confirmation appends a new event version; it never edits a candidate or substitutes a price stop.

## Labels and limits

Every detector result carries `development_result=true`, rights `UNREVIEWED`, source/origin and the wording
"geliştirme sonucu; eşikler olaydan sonra belirlendi". Unknown is not normal or safe.

The universe is survivor-biased and selected after the event; category history and distribution adjustments
are unavailable. NAV currency is not independently reported in the archive, and comparability within current
fund types is an exploratory assumption, not a verified matched-currency benchmark. Public archive revisions
and the 11:05 availability assumption are not a complete historical publication ledger. The observed archive
start left-censors fund age. Holiday-aware staleness is not claimed. No SPK motive, fraud, manipulation,
prediction, investment instruction, premium, actuarial probability or measured performance follows.

Committed outputs contain only aggregate development counts and may name only the eight allowed targets.
Real thresholds, signals, other fund names and price values remain in the localhost database/external archive.

## Acceptance

Synthetic tests cover positive trigger, normal control, boundary ties, gaps, missing data, insufficient peers/history,
zero variance and future appended or newly available rows. Calibration must not change when post-cutoff values
change. PostgreSQL checks prove immutable versions/evidence/results, idempotent runs, explicit abstentions,
candidate/unknown-time event exclusion and old-run retention. No real computation precedes this protocol commit.
