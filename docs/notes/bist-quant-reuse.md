# Reusing code from bist-quant

**Reviewed:** 2026-10-06, read-only, from a shallow clone of [Safa675/bist-quant](https://github.com/Safa675/bist-quant) at commit `8473426` (2026-07-21). Apache-2.0; the author is the project owner.

## Fund code: do not import

`src/bist_quant/clients/fund_analyzer.py` (`TEFASAnalyzer`, alias `FundAnalyzer`) does **not** use borsapy. It calls a third-party hosted Borsa MCP endpoint (`https://borsamcp.fastmcp.app/mcp`) over JSON-RPC and falls back to regex parsing of free text. It conflicts with the handoff rules:

- Missing fields default to `0.0` (NAV, AUM, returns, expense ratio, minimum investment). DEC-003 requires missing values to stay missing.
- `_calculate_beta` always returns `1.0` and `_calculate_alpha` always returns `0.0`, yet `get_fund_risk_metrics` reports them as metrics.
- Allocation results carry no as-of date; AN-FND-004 needs dated snapshots.
- History is date and NAV only; no AUM or investor-count history.
- No tests in the repo cover it.

Write a new TEFAS adapter instead, following the spike in `docs/handoff-v0.5/docs/10_Data_Requirements_and_Provider_Matrix.md` section 3.

## Candidates to copy

Copy the file with an attribution header and add tests in this repo. Review each one against the handoff's integrity rules before use.

| File | Size | Use |
|---|---|---|
| `common/resilience.py` | 154 lines | `CircuitBreaker`, `retry_with_backoff` for provider calls |
| `common/disk_cache.py` | 292 lines | Local response cache |
| `analytics/core_metrics.py` (selected functions) | 1,036 lines total | `curve_to_returns`, `compute_max_drawdown`, `align_series_by_date`, `quantile`, `sample_std_dev`. `PerformanceMetrics` fields default to `0.0`; check how empty or missing input is reported before reuse, since unknown must not read as normal. |

When BIST returns (postponed by DEC-024): `clients/borsapy_client.py`, `clients/borsapy_prices.py`, `clients/borsapy_indices.py`, `common/loaders/price_loader.py`.

## Out of scope

`signals/`, `strategies/`, `screening/`, `regime/`, the backtester and the portfolio optimizers. They are trading and selection tools, and the product rules out buy/hold/sell verdicts and personalized recommendations.

## Copy, don't depend

Prefer copying the few files above over depending on the whole library. bist-quant is about 93K lines of Python, requires Python 3.13+, and pulls in yfinance and other dependencies the funds phase doesn't need.

## Not verified

bist-quant's own test suite was not run. borsapy's current fund API was not checked. Whether `bist-quant` is published on PyPI was not checked.
