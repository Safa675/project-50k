"""Price-only detectors for the top-100 study. The rules are in PREREGISTRATION.md.

Every array is aligned to one date calendar and NaN means "not defined". A
statistic at calendar index i uses only indices up to i, so later prices can
never change an earlier value.
"""
from __future__ import annotations

from datetime import date

import numpy as np

MIN_PEERS = 10
LEVEL_WINDOW, LEVEL_MIN = 60, 50
BEFORE_WINDOW, BEFORE_MIN = 120, 100
SMOOTH_WINDOW, SMOOTH_MIN = 120, 100
YOUNG_DAYS = 730
MIN_CALIBRATION_VALUES, MIN_CALIBRATION_FUNDS = 1000, 5


def log_returns(prices: np.ndarray) -> np.ndarray:
    """r[i] = ln(p[i] / p[i-1]) where both prices exist; prices hold NaN for "no price"."""
    out = np.full(len(prices), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        out[1:] = np.log(prices[1:] / prices[:-1])
    out[~np.isfinite(out)] = np.nan
    return out


def peer_median(returns: np.ndarray, own: int, min_peers: int = MIN_PEERS) -> np.ndarray:
    """Median return of the other rows of a category matrix, where at least min_peers have one."""
    peers = np.delete(returns, own, axis=0)
    enough = np.sum(~np.isnan(peers), axis=0) >= min_peers
    out = np.full(returns.shape[1], np.nan)
    if enough.any():
        out[enough] = np.nanmedian(peers[:, enough], axis=0)
    return out


def lagged(x: np.ndarray, k: int) -> np.ndarray:
    """x moved k places later: out[i] = x[i - k]."""
    out = np.full(len(x), np.nan)
    out[k:] = x[:len(x) - k]
    return out


def rolling_median(x: np.ndarray, window: int, min_count: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        seg = x[max(0, i - window + 1):i + 1]
        seg = seg[~np.isnan(seg)]
        if len(seg) >= min_count:
            out[i] = np.median(seg)
    return out


def rolling_corr(x: np.ndarray, y: np.ndarray, window: int, min_pairs: int) -> np.ndarray:
    """Pearson correlation over the last `window` dates, using dates where both are defined."""
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        lo = max(0, i - window + 1)
        a, b = x[lo:i + 1], y[lo:i + 1]
        both = ~(np.isnan(a) | np.isnan(b))
        if both.sum() < min_pairs:
            continue
        a, b = a[both], b[both]
        if a.std() == 0 or b.std() == 0:  # no variance: undefined, not "smooth"
            continue
        out[i] = np.corrcoef(a, b)[0, 1]
    return out


def excess_level(excess: np.ndarray) -> np.ndarray:
    """D1: median excess return over the last 60 dates."""
    return rolling_median(excess, LEVEL_WINDOW, LEVEL_MIN)


def excess_change(excess: np.ndarray) -> np.ndarray:
    """D2: D1's median minus the median over the 120 dates before its window."""
    before = lagged(rolling_median(excess, BEFORE_WINDOW, BEFORE_MIN), LEVEL_WINDOW)
    return excess_level(excess) - before


def autocorrelation(returns: np.ndarray) -> np.ndarray:
    """D3: lag-1 autocorrelation of returns over the last 120 dates."""
    return rolling_corr(returns, lagged(returns, 1), SMOOTH_WINDOW, SMOOTH_MIN)


def peer_correlation(returns: np.ndarray, peers: np.ndarray) -> np.ndarray:
    """D4: correlation of returns with the peer median over the last 120 dates."""
    return rolling_corr(returns, peers, SMOOTH_WINDOW, SMOOTH_MIN)


def age_days(days: list[date], first_priced: date | None) -> np.ndarray:
    """D5: days since the first price; NaN before it."""
    if first_priced is None:
        return np.full(len(days), np.nan)
    return np.array([(d - first_priced).days if d >= first_priced else np.nan for d in days], dtype=float)


def threshold(per_fund: list[np.ndarray], percentile: float) -> float | None:
    """Percentile of all defined values, or None when there are too few values or funds."""
    values = [v[~np.isnan(v)] for v in per_fund]
    funds = sum(1 for v in values if len(v))
    pooled = np.concatenate(values) if values else np.array([])
    if len(pooled) < MIN_CALIBRATION_VALUES or funds < MIN_CALIBRATION_FUNDS:
        return None
    return float(np.percentile(pooled, percentile))
