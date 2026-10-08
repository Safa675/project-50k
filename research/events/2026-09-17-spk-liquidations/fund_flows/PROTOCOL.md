# B1: return-adjusted endpoint growth — exploratory protocol

Version: B1-1. Owner approved implementation and local named results in chat on
2026-10-08. This document is committed before executing the new calculation on
the real archive. Requirements: FR-037 and NFR-038 (partial); AN-FND-002.
No requirement registry or frozen detector registration is changed.

## Question and prior exposure

How much of a fund's change in reported total value is not explained by its
reported per-unit price change? Is the existing 10% catalog heuristic useful as
an initial review screen, or does it mark ordinary changes in many other funds?

The top-100 universe and earlier price-detector results have already been seen.
THF and TP2 growth was studied before this protocol. This is development research,
not independent validation, a fraud classification, or proof of a historical alert.
No threshold, universe or window is selected using the new results.

## Inputs and fixed universe

- Only codes in the committed `../top100_funds.txt` are allowed. The default run
  includes all 100; an explicit subset must pass the same allowlist before any
  source file is opened. No unopened price files or additional funds are read.
- Read only `raw/kap/series/{CODE}.json` at the repository root. Its fund and KAP
  source markers must match. Missing files and bad input are explicit outcomes.
  No network requests, PDF reparsing, TEFAS-price lookup or snapshot DB is needed.
- Monthly closing periods are October 2025 through September 2026 inclusive.
  September 2025 is permitted only as the opening endpoint for October 2025.
  Reports outside this range and weekly reports do not enter calculations.
- Compare actual consecutive calendar months of the same fund. Do not bridge
  gaps, choose among duplicate periods, mix monthly/weekly reports, or invent an
  opening value from the current report's `previous_period_price`.
- Use `total_value` and `period_end_price` from both reports. Preserve disclosure
  IDs, source period/cadence, publication strings, parser problems and source
  hashes. Recorded publication strings are not verified historical availability.

## Calculation and unchanged heuristic

For opening reported assets A0, closing reported assets A1, opening unit price
P0 and closing unit price P1:

```text
endpoint residual = A1 - A0 * (P1 / P0)
residual rate = endpoint residual / A0
research screen crossing = abs(residual rate) >= 0.10
```

Use Decimal with a local precision of 50 and ROUND_HALF_EVEN. Do not quantize
before comparing the threshold. Missing/nonfinite numbers, nonpositive opening
assets, negative closing assets or nonpositive prices cannot produce a rate.
A verified actual closing asset value of zero is arithmetically distinct from a
missing NAV; the archive's action/comparability limits still apply.

The threshold is the existing AN-FND-002 project hypothesis, not a calibrated or
validated cutoff. It is not changed after observing results. Positive and negative
crossings are both retained; use neutral signed labels.

This arithmetic is an endpoint value residual, not exact subscription/redemption
cash. Transaction timing, distributions/reinvestment, splits, mergers, share-class
scope and accounting changes can alter its interpretation. Units outstanding are
not investor counts and are not required for the primary calculation. A units-price
identity discrepancy and a mismatch against `previous_period_price` are separate
diagnostics, not repaired values or independently validated thresholds.

## Calculation versus production decision

The raw arithmetic output is labeled `EXPLORATORY_ARCHIVE`, with the source's
`HISTORICAL_REPLAY` origin and UNKNOWN rights retained. No currency is guessed:
amounts without explicit verified currency are in unknown source units. Ratios
also require compatible inputs for their financial interpretation.

Production evaluation is a separate function using an immutable ReplayCursor.
It must require eligible source versions at the cutoff, matching scope/currency
and valuation basis, verified action status, and an explicit prior-only baseline
check. Missing or unresolved evidence returns ABSTAINED, never NOT_TRIGGERED.
Unknown/future source availability cannot leak metrics or future evidence IDs.

The current archive lacks those guarantees, so every real research record has
`production_status: ABSTAINED`, an unverified baseline and explicit unresolved
assumptions. A research screen crossing must not be displayed as TRIGGERED.
No generic 20-observation minimum is introduced: the catalog does not define the
historical baseline check. Synthetic passed-baseline fixtures test admission
structure, not the empirical validity of a policy.

## Fixed summaries and rankings

Keep all attempted monthly pairs, including noncomputable pairs and their reasons.
For each selected fund report:

1. The latest reported closing month in the fixed window and its attempted pair.
   If that pair is missing/invalid, latest screen status is unknown. Do not silently
   substitute a valid earlier month and call it current.
2. The latest valid arithmetic pair, with its period and an explicit stale flag
   when it is earlier than the latest reported closing month.
3. Whether any valid pair crossed 10%, how many valid/crossing pairs there were,
   and the largest absolute residual rate with its signed value and period.
4. The same peak/any-crossing summaries for nominal closing periods through
   August 2026. This is a period subset, not proof a report was available before
   the SPK order of 17 September 2026.

Rank the latest valid current screens by absolute residual rate descending, ties
by code ascending. Historical peak rankings are separate, also absolute rate
descending/code ascending; tied peaks within a fund use the earliest period.
Do not rank unavailable latest pairs using stale earlier values.

Aggregate denominators distinguish selected funds, missing/invalid sources,
funds with any valid pair, valid latest pairs, all monthly attempts and valid
monthly pairs. Report latest-screen and any-period counts separately, with both
signs. For the eight known liquidation-list targets (THF, TP2, TLY, DFI, DOH, PRY,
KHA, PNU), report target counts and other-fund counts with their denominators.
Other funds are not a confirmed clean control set; these counts are not fraud
accuracy, recall or false-positive rates.

## Reproducibility, local output and naming

Before opening sources, the runner verifies this protocol, the universe and its
consumed code files against their committed HEAD blobs. A supplied protocol hash
must also match. Record protocol hash/commit, code hashes and selected source
hashes/missing states. No code, source or protocol is modified by a run.

Write deterministic, atomic results only beneath the repository's Git-ignored
`raw/kap/flow-analysis/`, in a directory identified by the run fingerprint.
Reuse identical own results; refuse foreign/conflicting files and input aliases,
including symlink escapes. Different source/code/protocol versions get separate
run identities. The standard output contains aggregate counts and the local path,
not named non-target findings.

Detailed results may name every selected fund locally, as requested by the owner.
Raw values and named non-target screen crossings never enter tracked docs/tests
or Git output. A private local analysis view may expose those names to the owner.
Committed summaries name only the eight targets and use aggregate counts otherwise.

## Acceptance checks and limits

Synthetic tests cover price-only growth (zero residual), signed changes, exact
positive/negative 10% boundaries, Decimal context independence, invalid values,
gaps, duplicate periods, weekly exclusion, latest-period missingness, allowlist
enforcement before reads, read-only input preservation, output isolation/foreign
file protection, committed protocol/code checks and deterministic reruns.
Production tests cover unknown metadata/baseline, incompatible units/actions,
cutoff eligibility and invariance under later publications/revisions.

Run the existing service, price-detector and frozen-reference suites. Verify the
216 frozen manifest entries and both frozen price-detector files. Hash selected
source bytes before/after the real run; do not touch external SQLite stores.

The opened/unopened split, unknown provider rights, historical universe selection,
limited KAP version history and unknown action/currency semantics remain limits.
This run does not identify funds that are currently unsafe, establish misconduct,
publish real data, or measure independent detector performance.
