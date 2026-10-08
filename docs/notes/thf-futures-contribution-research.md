# THF reported-futures contribution study

The owner approved examining THF futures as explanations for the previously
observed equity-reference gaps on 2026-10-08. The study now combines the existing
stock reference with a conditional, static reported-contract contribution using
official Borsa Istanbul settlement history. The reported futures positions do
not remove the large reference gap in the July-report window. Actual attribution
remains unknown because daily positions, trades and subscriptions are unobserved.

## Requirements and changes

Research preparation for **FR-018, FR-019, FR-038 and NFR-038**, related to
**AN-CMP-002**. No catalog threshold, product requirement status or replay-admission
rule is upgraded. Underlying futures are inputs to the approved THF fund study;
the DEC-024 fund-first scope is unchanged.

- `services/p50k/analytics/futures_contribution.py`: pure Decimal monetary P&L
  and contribution arithmetic, exact contracts, sides, units, strict missing
  data and expiry rules.
- `research/events/2026-09-17-spk-liquidations/fund_futures_divergence/`:
  committed protocol and offline runner verifying PDFs, official CSVs,
  provenance, unchanged equity results and committed runtime bytes.
- `tests/unit/test_futures_contribution.py` and
  `tests/unit/test_futures_contribution_runner.py`: synthetic monetary, temporal,
  expiry, missing-data, source-schema and provenance regression checks.
- This completion note. Financial observations and numeric returns remain in
  gitignored `raw/bist/THF/`; no raw financial values are committed.

Preregistration commit: `96e0c7a`. Initial runtime: `4f74cdb`. The first real
attempt stopped before contribution calculation because two cached acquisition
records lacked a final redirect URL. The receipt reader was corrected in
`5c24275`, without changing source bytes or the financial method, and the next
run completed successfully. Unknown redirect endpoints remain explicitly unknown,
bound to the original HTTP receipts, request URLs and unchanged CSV hashes.

## Sources, method and actual coverage

All eleven original monthly PDFs were audited: 39 futures rows, 38 distinct
contract codes. Eight reports contain no explicit futures rows; that does not
prove no derivatives activity during those months. Three reports have observed
snapshot positions. A later report never supplies an earlier window's positions.

The narrow download retained **156 official CSVs across 52 required dates**:
settlement bulletins, dated contract specifications and contract changes. All
files returned HTTP 200 and passed schema/hash verification. Every reported
valuation equals its official report-date settlement, and every quantity times
multiplier times reported valuation reconciles with the printed notional.
The [official VIOP data page](https://www.borsaistanbul.com/veriler/vadeli-islem-ve-opsiyon-piyasasi-verileri)
supplies the archived daily files. Settlement and close are distinct columns;
metadata's last settlement may refer to the previous session.

The fixed reference computes signed reported contract quantity times official
multiplier times the change in exact-contract settlement price, divided by
reported fund net assets. This is not notional/NAV treated as an asset allocation,
and collateral is not assumed to be realized futures P&L. It preserves the
existing stock-weight convention and original observation windows.

A contract expired before baseline is explicitly excluded with no replacement
assumed. Cash-settled expiry within a window uses the exact expiry settlement
and holds the resulting cumulative P&L constant thereafter. No continuous-contract
stitching, interest, reinvestment or actual rollover is invented. Physical
delivery within a window would be unavailable; the observed stock contracts do
not expire within the study cutoff.

There are **48 available futures observations** and **47 combined observations**
across the three futures-report windows. One original stock-missing observation
remains unavailable for the combined reference. The other eight reports' actual
derivatives activity remains unknown, with no invented zero contribution.
All eleven windows and exclusions are retained. No alarm threshold, fraud label,
attribution percentage, success rate or false-alarm rate is estimated.

Private result:

```text
raw/bist/THF/futures-divergence/f0a1fca755bb021531d406c0c6b3118567d3a350eb23acf4987e92a55e4f4aac/results.json
SHA256: a4f652b4ca1c687d381a4cbe8b110547ac7c7ccf710d982dcb05a0815f553aa3
```

## Actual verification

Final regression runs, after the receipt correction:

```sh
# Repository root: Ran 426 tests in 4.428s; OK.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services /home/safa/miniforge3/bin/python3 -m unittest discover -s tests -t . -v

# research/events/2026-09-17-spk-liquidations/price_detectors:
# Ran 9 tests in 0.265s; OK.
PYTHONDONTWRITEBYTECODE=1 /home/safa/miniforge3/bin/python3 -m unittest test_detectors -v

# docs/handoff-v0.5: Ran 88 tests in 0.003s; OK.
PYTHONDONTWRITEBYTECODE=1 /home/safa/miniforge3/bin/python3 -m unittest discover -s tests -v

# Repository root: exit 0; result path and SHA printed.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services /home/safa/miniforge3/bin/python3 research/events/2026-09-17-spk-liquidations/fund_futures_divergence/run.py
```

**523 tests passed.** An independent exact-Fraction checker performed **3,306
checks with zero failures**, verifying original CSV marks/specifications,
PDF quantities/sides/NAV, every contribution, expiry cash holding, unchanged
stock metrics and all eleven original windows. The runner bound 486 input
artifacts and checked their hashes before and after calculation.

The private `THF-futures-review.canvas.tsx` passed TypeScript 5.9.3 against the
actual Canvas SDK with zero diagnostics (minimal React declarations). Source
fidelity checks matched all eleven windows, 194 interval records, 39 source
positions, 328 futures items and 156 official CSV hashes. The JSX SDK stub
exercised 59 views, 204 charts and 6,039 plotted source numbers. Missing stock
observations split the curves, eight reports without explicit positions produce
no invented zero contributions, and expiry cash holding is visible. Actual
host visual rendering has not been verified.

Separate source checks passed: 371 original-PDF inventory checks, 32,636 history
checks, 198 source-notional/valuation checks and 3,185 adjustment-feed checks.
Staged code was scanned against 35,539 specific local financial values: zero
financial literal hits; calendar metadata collisions and synthetic round-number
fixtures were reviewed. `git diff --cached --check` passed. Frozen files and the
unrelated untracked research brief were not edited.

## Data mode, limits and next task

Origin is **HISTORICAL_REPLAY**, interpretation
**CONDITIONAL_ARCHIVE_DIAGNOSTIC**, `point_in_time_admitted=false` and rights
UNKNOWN. Official archived files do not establish historical first-publication
or revision times. Two bound cached change-file receipts retain an unknown final
response URL; their official request URLs, HTTP status, timestamps and hashes
are recorded. No source entitlement or historical alarm-timing claim is made.

The model freezes month-end contract quantities and uses stale reported net
assets. Actual daily trading, closures, new positions, fund asset growth, fees,
margin interest and subscriptions can change the true contribution. The old
equity reference and assumed TEFAS/session alignment retain their existing
limitations. Actual futures P&L is UNKNOWN, and full-fund/fraud classifications
remain ABSTAINED. Residual agreement or disagreement is not causal proof.

No other fund, broad BIST equity history, account, deployment, public numeric
data release or migration is part of this study. The next recommended task is
to examine changes in THF's individual equity holdings and weights between
reports, as another check of whether the frozen-portfolio approximation is
economically informative. Daily-position attribution still requires richer data.
