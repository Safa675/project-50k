# THF reported-futures contribution: preregistration v1

Registered on 2026-10-08 before calculating the futures contribution or the
combined reference residual. The owner approved examining THF futures in chat.
The previously computed spot-equity gaps and source exposure context are already
known development observations. Two official settlement-price examples and
contract metadata were inspected for feasibility; this is not a blind evaluation.

Research preparation for FR-018, FR-019, FR-038 and NFR-038, related to AN-CMP-002.
No catalog threshold or requirement status changes. Scope is THF only, using the
same eleven reports and unchanged windows from the preceding equity diagnostic.
Actual financial values and all result files remain below gitignored `raw/`.

## Fixed sources and temporal scope

- Original THF KAP PDFs and the hash-bound, source-coordinate futures inventory.
- The existing equity diagnostic anchored to code commit `96dbbd0`; its dates,
  NAV alignment, stock reference returns and unavailable rows are unchanged.
- Official Borsa Istanbul daily VIOP bulletins `viop_YYYYMMDD.csv`, exact-contract
  metadata `viopms_YYYYMMDD.csv` and relevant contract-adjustment records.
- Only dates required by the three reports with explicit futures positions,
  their report-end reconciliation, baselines, endpoints and intervening expiry.
  No broad BIST download, another fund or post-cutoff return is evaluated.

Only a position reported in the corresponding already-published report enters a
window. The later August report cannot explain an earlier July-report window.
Reports without explicit futures rows establish no observed snapshot position;
their actual intramonth futures P&L remains unknown, not zero.

## Fixed arithmetic and missing-data rules

For a reported quantity q, side s (+1 long, -1 short), official multiplier M,
baseline settlement F(b) and endpoint settlement F(t):

```text
reference_futures_pnl = sum(s * q * M * (F(t) - F(b)))
reference_futures_contribution = reference_futures_pnl / report_fund_net_assets
combined_reference_return = existing_equity_reference + futures_contribution
remaining_gap = existing_fund_return - combined_reference_return
```

This freezes reported quantities and normalizes currency P&L by the same report
net-assets denominator used for the original equity reference weights. It is a
conditional comparison, not actual fund P&L or a daily-position reconstruction.
Subscriptions, turnover and asset growth make the denominator stale; no daily
asset value is invented. The equity reference's existing weight convention is
preserved, rather than silently replacing it with a different model.

Use official **settlement** prices, not the separately supplied close, spot
prices or current/continuous futures quotes. Require exact contract code,
positive finite quotes and multipliers, TRY units, known side and consistent
baseline/endpoint contract specifications. Reconcile source quantity times
reported valuation price times official multiplier with printed notional-like
value. That value and collateral are not NAV allocations or realized P&L.
Changes in specifications, unresolved corporate actions, missing required prices
or failed source reconciliation make the affected contribution unavailable.
Never fill a missing quote, renormalize remaining positions or invent a rollover.

Contracts expired before baseline are recorded as excluded: this static model
opens no replacement contract. For cash-settled contracts expiring inside the
window, use the exact expiry settlement, then retain that cumulative P&L as cash
without interest or reinvestment. Later prices cannot change an earlier output.
Physical delivery inside a window is unsupported and produces unavailability.
There is no guess about actual THF rollover or daily opening/closing trades.

## Output and interpretation

Show all eleven reports, explicit no-position/expired-contract exclusions,
required-contract coverage, source reconciliation, signed exposure context,
futures contribution and the remaining stock-plus-futures gap wherever available.
The original unavailable stock observation stays unavailable even if futures
arithmetic is available. Evaluate the original fixed windows; do not select a
shorter window or change the method to make a gap disappear.

No alarm threshold, fraud probability, attribution percentage, success rate or
false-alarm rate is estimated. Actual futures P&L and fraud classification remain
unknown/ABSTAINED. Numerical agreement cannot establish the cause of the fund's
return. Missing daily positions and trading data remain explicit.

Origin is HISTORICAL_REPLAY, interpretation CONDITIONAL_ARCHIVE_DIAGNOSTIC,
point_in_time_admitted=false. Official archived prices do not by themselves
establish first-publication/revision times or approved storage/display rights.
The production replay cursor, existing detectors and equity diagnostic remain
unchanged. No external publication, deployment, account, spending or repository
push is part of this experiment.

## Acceptance

Synthetic tests cover monetary units, long/short signs, multiple positions,
missing/zero quotes, missing metadata, changed multipliers, expiry cash holding,
unsupported physical delivery, expired-before-baseline exclusions, publication
and future-price invariance, independent Decimal context and no-position unknown.
Independently verify actual source totals, official metadata and Decimal/Fraction
arithmetic, and rerun the repository, price-detector and frozen reference suites.
Runtime code and this protocol must be committed before the first real
contribution is computed. Report all actual exclusions and test failures.
