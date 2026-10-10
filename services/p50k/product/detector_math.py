"""Causal price-detector mathematics for the all-fund development run.

These functions have no I/O or calibration-date selection. Windows and formulas
follow the frozen price study; array-wide evaluation avoids a Python loop per
calendar window. Nonfinite values mean missing, never zero.
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


def _series(values: np.ndarray) -> np.ndarray:
    out = np.asarray(values, dtype=float)
    if out.ndim != 1:
        raise ValueError("a calendar-aligned one-dimensional series is required")
    return np.where(np.isfinite(out), out, np.nan)


def log_returns(prices: np.ndarray) -> np.ndarray:
    """Log price ratios; missing/nonpositive prices also invalidate the next return."""
    values = _series(prices)
    out = np.full(len(values), np.nan)
    if len(values) < 2:
        return out
    valid = (values[1:] > 0) & (values[:-1] > 0)
    previous, current = values[:-1][valid], values[1:][valid]
    with np.errstate(invalid="ignore", divide="ignore", over="ignore", under="ignore"):
        ratio = current / previous
        computed = np.log(ratio)
        # Preserve the frozen operation for ordinary values. The mathematically
        # equivalent log difference is needed only if division over/underflows.
        unstable = ~np.isfinite(computed)
        computed[unstable] = np.log(current[unstable]) - np.log(previous[unstable])
    out[1:][valid] = computed
    return out


def leave_one_out_peer_medians(returns: np.ndarray, min_peers: int = MIN_PEERS) -> np.ndarray:
    """Every fund's peer median, excluding itself and requiring finite peer returns.

    Sort each date once, then locate the middle peer values after deleting the
    own rank. This also handles tied values and funds missing on that date.
    """
    matrix = np.asarray(returns, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("a fund-by-calendar matrix is required")
    if min_peers < 1:
        raise ValueError("min_peers must be positive")
    out = np.full(matrix.shape, np.nan)
    funds, dates = matrix.shape
    if funds <= min_peers or dates == 0:
        return out
    finite = np.isfinite(matrix)
    values = np.where(finite, matrix, np.nan)
    order = np.argsort(values, axis=0, kind="stable")
    ordered = np.take_along_axis(values, order, axis=0)
    ranks = np.empty_like(order)
    columns = np.arange(dates)[None, :]
    ranks[order, columns] = np.arange(funds)[:, None]
    peers = finite.sum(axis=0)[None, :] - finite
    enough = peers >= min_peers
    lower = np.maximum((peers - 1) // 2, 0)
    upper = np.maximum(peers // 2, 0)
    lower += finite & (ranks <= lower)
    upper += finite & (ranks <= upper)
    lower_values = np.take_along_axis(ordered, lower, axis=0)
    upper_values = np.take_along_axis(ordered, upper, axis=0)
    out[enough] = ((lower_values + upper_values) / 2)[enough]
    return out


def peer_median(returns: np.ndarray, own: int, min_peers: int = MIN_PEERS) -> np.ndarray:
    """The frozen single-fund API, backed by the category-wide implementation."""
    return leave_one_out_peer_medians(returns, min_peers)[own]


def lagged(values: np.ndarray, places: int) -> np.ndarray:
    """Move a series later without carrying values into preceding dates."""
    if places < 0:
        raise ValueError("lag must be nonnegative")
    series = _series(values)
    out = np.full(len(series), np.nan)
    if places < len(series):
        out[places:] = series[:len(series) - places]
    return out


def _windows(values: np.ndarray, window: int, minimum: int) -> np.ndarray:
    if window < 1 or minimum < 1 or minimum > window:
        raise ValueError("window and minimum must be positive, with minimum <= window")
    series = _series(values)
    if not len(series):
        return np.empty((0, window))
    padded = np.pad(series, (window - 1, 0), constant_values=np.nan)
    return np.lib.stride_tricks.sliding_window_view(padded, window)


def rolling_median(values: np.ndarray, window: int, min_count: int) -> np.ndarray:
    """Median over the ending calendar window, counting only finite observations."""
    segments = _windows(values, window, min_count)
    out = np.full(len(segments), np.nan)
    enough = np.isfinite(segments).sum(axis=1) >= min_count
    if enough.any():
        out[enough] = np.nanmedian(segments[enough], axis=1)
    return out


def rolling_corr(x: np.ndarray, y: np.ndarray, window: int, min_pairs: int) -> np.ndarray:
    """Pearson correlation using only finite pairs, with zero variance undefined."""
    a, b = _windows(x, window, min_pairs), _windows(y, window, min_pairs)
    if len(a) != len(b):
        raise ValueError("paired series must share one calendar")
    out = np.full(len(a), np.nan)
    pairs = np.isfinite(a) & np.isfinite(b)
    enough = pairs.sum(axis=1) >= min_pairs
    if not enough.any():
        return out
    a, b, paired = a[enough], b[enough], pairs[enough]
    counts = paired.sum(axis=1)
    a_mean = np.where(paired, a, 0).sum(axis=1) / counts
    b_mean = np.where(paired, b, 0).sum(axis=1) / counts
    centered_a = np.where(paired, a - a_mean[:, None], 0)
    centered_b = np.where(paired, b - b_mean[:, None], 0)
    a_square = np.square(centered_a).sum(axis=1)
    b_square = np.square(centered_b).sum(axis=1)
    # Equal decimal values can have a nonzero computed std from mean roundoff.
    # Test actual range as well, preserving the protocol's zero-variance rule.
    varying_a = np.where(paired, a, np.inf).min(axis=1) < np.where(paired, a, -np.inf).max(axis=1)
    varying_b = np.where(paired, b, np.inf).min(axis=1) < np.where(paired, b, -np.inf).max(axis=1)
    valid = varying_a & varying_b & (a_square > 0) & (b_square > 0)
    result = np.full(len(a), np.nan)
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        result[valid] = ((centered_a * centered_b).sum(axis=1)[valid]
                         / np.sqrt(a_square[valid] * b_square[valid]))
    result[~np.isfinite(result)] = np.nan
    out[enough] = np.clip(result, -1, 1)
    return out


def excess_level(excess: np.ndarray) -> np.ndarray:
    """D1: ending 60-date median with at least 50 finite excess returns."""
    return rolling_median(excess, LEVEL_WINDOW, LEVEL_MIN)


def excess_change(excess: np.ndarray) -> np.ndarray:
    """D2: D1 less the 120-date median ending 60 calendar dates earlier."""
    before = lagged(rolling_median(excess, BEFORE_WINDOW, BEFORE_MIN), LEVEL_WINDOW)
    return excess_level(excess) - before


def autocorrelation(returns: np.ndarray) -> np.ndarray:
    """D3: ending 120-date lag-one Pearson correlation, at least 100 pairs."""
    return rolling_corr(returns, lagged(returns, 1), SMOOTH_WINDOW, SMOOTH_MIN)


def peer_correlation(returns: np.ndarray, peers: np.ndarray) -> np.ndarray:
    """D4: ending 120-date correlation with the leave-one-out peer median."""
    return rolling_corr(returns, peers, SMOOTH_WINDOW, SMOOTH_MIN)


def score_series(returns: np.ndarray, peers: np.ndarray) -> dict[str, np.ndarray]:
    """Compute the four anomaly statistics, without thresholds or decisions."""
    own, peer = _series(returns), _series(peers)
    if len(own) != len(peer):
        raise ValueError("own returns and peers must share one calendar")
    excess = own - peer
    return {"D1": excess_level(excess), "D2": excess_change(excess),
            "D3": autocorrelation(own), "D4": peer_correlation(own, peer)}


def age_days(days: list[date], first_priced: date | None) -> np.ndarray:
    """D5 attribute: days since first positive price, unknown before that date."""
    if first_priced is None:
        return np.full(len(days), np.nan)
    return np.array([(day - first_priced).days if day >= first_priced else np.nan
                     for day in days], dtype=float)


def threshold(per_fund: list[np.ndarray], percentile: float) -> float | None:
    """Pooled percentile, abstaining below 1000 finite values or five funds.

    The caller must restrict series to the protocol's calibration-date interval.
    """
    values = [series[np.isfinite(series)] for series in map(_series, per_fund)]
    contributing = sum(bool(len(series)) for series in values)
    pooled = np.concatenate(values) if values else np.array([])
    if len(pooled) < MIN_CALIBRATION_VALUES or contributing < MIN_CALIBRATION_FUNDS:
        return None
    return float(np.percentile(pooled, percentile, method="linear"))
