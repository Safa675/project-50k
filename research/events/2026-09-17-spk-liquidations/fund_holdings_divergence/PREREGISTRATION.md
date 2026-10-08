# THF reported-equity return consistency: preregistration v1

Registered on 2026-10-08 before computing any real fund/equity return residual.
The owner approved this THF-only pilot in chat. This is a conditional archive
diagnostic, not a fraud classifier or an availability-qualified replay detector.

## Trace and scope

Research preparation for **FR-018, FR-019, FR-038 and NFR-038**, related to
**AN-CMP-002**. No catalog threshold, requirement status or existing detector is
changed. Only THF is evaluated. The other funds, including the unopened fund
files, are excluded. No broad BIST download, stock anomaly detector, alert,
deployment, account or external publication is authorized by this experiment.

Already seen: THF's fund prices, monthly growth, allocation summaries, September
issuer disclosures, spot-security identifiers and price-acquisition coverage.
THF is a development case. Its liquidation is not a fraud ground-truth label.

## Fixed inputs

- The eleven existing monthly THF KAP reports for 2025-10 through 2026-08,
  their report list, original bytes and publication timestamps.
- `raw/tefas/prices/THF.json`: dated unit NAV; zero/null remains unavailable.
- `raw/bist/prices/THF_2025-10-01_2026-10-07.parquet` and its provenance
  descriptor, source acquisition manifests and reported-security universe.
- Existing explicit same-reported-ISIN aliases: IPEKE/TRENJ and KOZAL/TRALT.
  No other name substitution is guessed. All input and code hashes are recorded
  in the private result. No new network request is part of this experiment.

Raw observations and numeric results stay under gitignored `raw/bist/THF/`.
Committed tests use synthetic data only. This protocol must be committed before
real residuals exist; the runner refuses uncommitted protocol/runtime changes.

## Position extraction and reference weights

Read the individual spot-equity rows in section III. Preserve repeated rows,
signed quantities, signed total position values, printed valuation prices,
currency, ISIN, row provenance and the printed FPD/FTD percentages. Never equate
futures notional with a NAV allocation. Futures are recorded as unmodeled.

Use signed **position value / reported fund net asset value** as the initial
reference weight. The headline and section IV net asset value must reconcile;
the spot-row value sum must reconcile with the printed equity group total.
Decimal arithmetic and source-rounding error bounds are used. Rounded printed
percentages are audit checks, not the weights; their row rounding may accumulate.
Ambiguous values, unresolved identities or failed value/denominator reconciliation
make the corresponding snapshot unavailable. Quantity-times-price discrepancies
are checked against their printed precision and reported explicitly.

Aggregate repeated rows by reported ISIN without dropping negative or zero-value
entries. Retain all underlying rows. Negative accounting entries do not establish
verified short positions. Report signed net, positive and absolute negative
weights. Do not rescale equities to sum to 100%.

## Dates and windows

- Common market calendar: sorted distinct session dates in the scoped equity
  panel. This is an observed provider calendar, not a certified exchange calendar.
- KAP publication dates are explicitly interpreted as Europe/Istanbul, as in the
  prior source record; its timezone guarantee remains unverified.
- Baseline `b`: the first common market session **strictly after** the report's
  local publication date. The 09:00 candle label is not treated as close time.
- Evaluate at most **20 following return intervals**, and stop before the next
  downloaded report's local publication date. A later holdings snapshot never
  supplies weights for an earlier period.
- Map a TEFAS row labeled D to the immediately preceding **common market
  session**, not an individual stock's previous available candle. This one-session
  valuation lag is an explicit assumption supported by the provider spike.
- Fund label dates after **2026-09-16** are excluded, conservatively before the
  dated SPK order. There is no alarm-timing or pre-event detection claim.
- Missing or ambiguous NAV mapping, absent/nonpositive/nonfinite baseline or
  endpoint stock prices, or an unresolved identity makes that observation
  unavailable. Require price coverage for **every reported spot security**,
  including printed 0.00% rows. No forward fill, interpolation or renormalization.

## One continuous diagnostic

For initial signed reference weights w_i and baseline closes C_i(b):

```text
fund_return(b,t) = unit_NAV(t) / unit_NAV(b) - 1
equity_proxy(b,t) = sum_i w_i * (C_i(t) / C_i(b) - 1)
gap(b,t) = fund_return(b,t) - equity_proxy(b,t)
```

This is a frozen-initial-weight buy-and-hold **counterfactual**. It is not daily
constant-weight compounding, which would assume daily rebalancing. It does not
multiply old nominal quantities by currently split-adjusted prices. Report the
fund return and proxy in percent, and their difference in percentage points.

Unmodeled holdings are assigned zero P&L for the counterfactual calculation only.
That is not a statement about THF's actual futures, cash, financing or expenses.
Month-end weights may already be stale at publication. Daily trades, subscriptions,
derivatives, dividends, corporate actions, valuation conventions and accounting
signs can explain a gap. Report holdings age and these limits next to every result.

## Outputs and interpretation

Produce per-report curves, available/unavailable interval counts, endpoint values,
and descriptive largest absolute/positive/negative gaps. Show all windows, not
only a favorable example. A window shortened by the next report or NAV cutoff is
explicit. Display full coverage and unavailability reasons.

**Alarm threshold: none.** No tuned cutoff, binary fraud signal, severity,
probability, success rate or false-alarm rate is computed. Those rates are
unavailable with one already studied fund and no validated fraud labels/controls.
Full-fund anomaly/fraud classification is **ABSTAINED**: unmodeled derivatives and
accounting interpretation prevent attributing an equity-only gap to misconduct.

Origin is `HISTORICAL_REPLAY`, with an additional prominent label
`CONDITIONAL_ARCHIVE_DIAGNOSTIC`. Historical stock first-publication/revision times,
legacy adjustment conventions, currency/feed metadata and data rights are not
fully established. `point_in_time_admitted=false`; the production ReplayCursor and
its admission rules are unchanged. Current vendor history is not claimed to be
the history available on the evaluated date.

## Acceptance and completion

Synthetic tests must cover matching replication; AUM independence; 80% stock
weight times a 10% decline giving an 8% contribution; a round-trip stock price
giving zero cumulative contribution without daily rebalancing; signed negative
weights; a hedged flat fund with a numerical gap but abstained classification;
missing/zero prices; duplicate dates; unknown identities; future publications;
20-interval and next-publication boundaries; one-session NAV alignment; and future
values leaving earlier fixed observations unchanged.

Verify the real extraction independently, input hashes unchanged, numerator and
denominator reconciliation, all required price identities, source timestamps and
result arithmetic. Run the three existing regression suites. Publish no raw
values to Git. Report actual failures and exclusions rather than repairing them
to make THF appear anomalous. Economic agreement and fraud-detection performance
are separate from arithmetic and software correctness.
