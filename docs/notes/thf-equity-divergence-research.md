# THF reported-equity return diagnostic

The owner approved a THF-only fund/equity divergence pilot on 2026-10-08.
The pilot now calculates a publication-bounded comparison between THF unit NAV
returns and the signed spot-equity positions in its downloaded monthly reports.
This supplies a continuous research observation, not a fraud classifier.

## Requirements and changed files

Research preparation for **FR-018, FR-019, FR-038 and NFR-038**, related to
**AN-CMP-002**. No product requirement, catalog threshold or data-admission gate
is marked complete. The TEFAS-only product scope in DEC-024 remains unchanged;
underlying equities are inputs to a fund study.

- `services/p50k/providers/thf_holdings.py`: geometry-aware, signed spot-position
  extraction, row provenance and reconciliation against source totals.
- `services/p50k/analytics/holdings_divergence.py` and its package initializer:
  pure Decimal arithmetic, explicit missing data, signed initial weights and
  publication-bounded observation windows.
- `research/events/2026-09-17-spk-liquidations/fund_holdings_divergence/`:
  committed preregistration and an offline, THF-only, hash-bound runner.
- `tests/unit/test_thf_holdings.py`, `test_holdings_divergence.py` and
  `test_holdings_divergence_runner.py`: synthetic parsing, arithmetic, date,
  missing-data, scope and committed-source checks.
- This note records the executed scope and practical limits. Numeric financial
  observations and results are excluded from Git.

The protocol was committed as `898643c` before any real return residual was
computed. Runtime code was committed as `96dbbd0` before the first actual run.
The runner rejects a protocol/runtime that differs from its committed bytes.

## Executed experiment

The eleven existing THF reports cover October 2025 through August 2026. All
467 signed spot rows were extracted. The reference weights are position value
divided by fund net assets, aggregated by reported ISIN. Printed percentages
are rounding audits; equities are never normalized to the entire fund.

Each window starts on the first observed common market session after the KAP
publication date. It contains at most twenty following return intervals and
ends before the next report publication or the preregistered fund-label cutoff.
TEFAS label D is mapped to the preceding common market session, explicitly as
an assumption. The arithmetic compares cumulative fund return with the sum of
initial signed stock weights times cumulative stock returns. It assumes no
daily rebalancing and does not value old nominal quantities at adjusted prices.

The actual run produced eleven windows and 194 candidate intervals: 193 had
complete required prices and NAV; one was unavailable because a required stock
close was absent. That interval remains missing. All windows, unavailable rows,
source positions, endpoints, descriptive extrema, weights and caveats are saved
in the private results. No threshold or binary anomaly label was generated.

The observed differences establish that the reference equity contribution can
depart from the fund return. Their cause is unresolved. The reports showing
the largest differences also contain futures, whose actual P&L this diagnostic
does not calculate. This is a possible explanation, not an attribution.

Private result:

```text
raw/bist/THF/divergence-analysis/4a1ac6d36969dd66e2da6780a72b11804f31276074fb49f9e851a6d5535f7e18/results.json
SHA256: 1059eff06a897d1e21103c801b5d92bcf45be4ec88d7f3bcc79cd2b52c5b1d0c
```

## Actual validation

The existing three regression suites were executed with Python 3.13.13:

```sh
# Repository root: Ran 367 tests in 4.762s; OK.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services /home/safa/miniforge3/bin/python3 -m unittest discover -s tests -t . -v

# research/events/2026-09-17-spk-liquidations/price_detectors:
# Ran 9 tests in 0.275s; OK.
PYTHONDONTWRITEBYTECODE=1 /home/safa/miniforge3/bin/python3 -m unittest test_detectors -v

# docs/handoff-v0.5: Ran 88 tests in 0.004s; OK.
PYTHONDONTWRITEBYTECODE=1 /home/safa/miniforge3/bin/python3 -m unittest discover -s tests -v

# Repository root: exit 0, private result path and SHA printed.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services /home/safa/miniforge3/bin/python3 research/events/2026-09-17-spk-liquidations/fund_holdings_divergence/run.py
```

Total: **464 tests passed**. The new tests cover matching replication, AUM
independence, signed and offsetting positions, missing/zero prices, identities,
future data invariance, publication boundaries, NAV alignment and deterministic
Decimal behavior. A separate original-PDF/Fraction extraction check performed
13,351 checks with zero errors before the return calculation.

After the actual run, an independent exact-Fraction checker performed 37,858
checks with zero errors. It recomputed every available return, proxy, gap and
signed weight, checked all time boundaries and verified all source hashes.
An additional 271 checks validated weight breakdowns and futures caveat flags
on all candidate intervals. Receipts live beside the private result. The stated
Decimal/Fraction agreement tolerance was fixed at `1e-70`.

A private interactive canvas presents all eleven windows. Actual SDK
TypeScript 5.9.3 checking returned zero diagnostics, using minimal React
declarations. A JSX SDK stub verified eleven views, all 194 interval records,
eleven PDF hashes and 612 source-derived numbers across 22 charts. The missing
endpoint remains unavailable; a synthetic missing-middle case verifies that
charts do not connect across missing data. This is not actual host visual
rendering, which remains unverified. The canvas contains no network request.

The runtime verified 321 input artifacts and preserved their hashes. Before
committing code, staged numeric literals were compared against 33,485 specific
source values; the only collisions were reviewed calendar-year metadata.
Short round numbers in clearly synthetic fixtures were reviewed manually.
`git diff --cached --check` passed. Frozen handoff files were not edited.

## Data mode, untested behavior and limits

Origin is **HISTORICAL_REPLAY**; interpretation is
**CONDITIONAL_ARCHIVE_DIAGNOSTIC**, with `point_in_time_admitted=false`.
Historical stock first-publication times, revisions, legacy adjustments,
currency/feed details and data rights remain incompletely established. No
availability-qualified historical alarm timing is claimed. Rights remain
UNKNOWN and numeric results stay local.

Daily trades, futures, financing, cash yield, fees, dividends and corporate
actions are not modeled. Negative accounting rows are preserved without being
declared verified short positions. Month-end weights may already be stale at
publication. The observed session calendar is not an official exchange calendar,
and the NAV/session alignment is assumed. Full-fund anomaly and fraud statuses
therefore remain ABSTAINED.

Fraud-detection success and false-alarm rates were not tested: there is one
already studied development fund and no validated fraud labels or control group.
No other fund, broad BIST history, live integration, deployment or account was
used. No database migration was required. The unrelated untracked research
brief was left unchanged.

The next recommended task is to assess THF's reported futures and daily turnover
as explanations for the large reference gaps. This can resolve the model's
economic coverage before considering a broad stock-history download or applying
the method to all funds.
