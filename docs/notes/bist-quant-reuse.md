# Reusing code from bist-quant

**Reviewed:** 2026-10-06, read-only, from a shallow clone of [Safa675/bist-quant](https://github.com/Safa675/bist-quant) at commit `8473426` (2026-07-21). Apache-2.0; the author is the project owner.

## Fund code: do not import

`src/bist_quant/clients/fund_analyzer.py` (`TEFASAnalyzer`, alias `FundAnalyzer`) does **not** use borsapy. It calls a third-party hosted Borsa MCP endpoint (`https://borsamcp.fastmcp.app/mcp`) over JSON-RPC and falls back to regex parsing of free text. It conflicts with the handoff rules:

- Missing fields default to `0.0` (NAV, AUM, returns, expense ratio, minimum investment). DEC-003 requires missing values to stay missing.
- `_calculate_beta` always returns `1.0` and `_calculate_alpha` always returns `0.0`, yet `get_fund_risk_metrics` reports them as metrics.
- Allocation results carry no as-of date; AN-FND-004 needs dated snapshots.
- History is date and NAV only; no AUM or investor-count history.
- No tests in the repo cover it.

Write a new TEFAS adapter instead, following the spike plan in `docs/handoff-v0.5/docs/10_Data_Requirements_and_Provider_Matrix.md` section 3 and the findings in `research/spikes/2026-10-06-tefas/REPORT.md`.

## Ported (2026-10-06)

Each ported file starts with its source and a list of what changed. Tests are in `tests/unit/`.

| bist-quant source | Ported to | Main changes |
|---|---|---|
| `common/resilience.py` | `services/p50k/providers/resilience.py` | Retries only the exception types the caller names; never retries an open circuit; the circuit breaker can ignore errors that aren't about provider health; one trial call at a time when half-open; logs the error class, not its message. |
| `common/disk_cache.py` | `services/p50k/providers/disk_cache.py` | JSON only (no pandas); reads return when the value was cached; NaN and non-JSON values rejected; key names validated so they can't escape the cache directory; atomic single-file writes. |
| `analytics/core_metrics.py` (selected functions) | `services/p50k/series.py` | Undefined results are `None`, not `0.0`; NaN, non-positive prices and duplicate dates raise; real `date` objects; drawdown as a fraction; log returns added; alignment reports dropped observations. `normal_cdf` and the performance suite were not ported. |

When BIST returns (postponed by DEC-024): `clients/borsapy_client.py`, `clients/borsapy_prices.py`, `clients/borsapy_indices.py`, `common/loaders/price_loader.py`.

## Out of scope

`signals/`, `strategies/`, `screening/`, `regime/`, the backtester and the portfolio optimizers. They are trading and selection tools, and the product rules out buy/hold/sell verdicts and personalized recommendations.

## Copy, don't depend

Prefer copying the few files above over depending on the whole library. bist-quant is about 93K lines of Python, requires Python 3.13+, and pulls in yfinance and other dependencies the funds phase doesn't need.

## Not verified

bist-quant's own test suite was not run. Whether `bist-quant` is published on PyPI was not checked. borsapy's fund API was checked later, in the 2026-10-06 TEFAS spike.
