"""Return, drawdown, alignment and quantile helpers for dated value series.

Adapted from bist-quant (github.com/Safa675/bist-quant @ 8473426,
src/bist_quant/analytics/core_metrics.py, Apache-2.0), with these changes:
- undefined statistics return None instead of 0.0 (an empty series has no
  mean, a one-point series has no spread), so "unknown" never reads as zero;
- NaN, infinity, booleans, non-positive prices and duplicate dates raise
  InvalidSeries instead of being dropped silently;
- dates are datetime.date objects rather than truncated strings;
- drawdown is a fraction (-0.25), not a percentage;
- adds log returns, which the anomaly catalog uses for detection;
- alignment reports how many observations each series lost;
- normal_cdf and the performance suite (Sharpe, CAGR, VaR and so on) are not
  ported: the handoff forbids turning deviations into probabilities, and the
  product does not grade investment performance.

Returns are between consecutive observations, whatever the calendar gap, and
are dated at the later observation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Mapping, Sequence


class InvalidSeries(ValueError):
    """The input cannot support the requested calculation."""


@dataclass(frozen=True)
class SeriesPoint:
    date: date
    value: float


@dataclass(frozen=True)
class AlignedSeries:
    dates: list[date]
    values: dict[str, list[float]]
    unmatched: dict[str, int]  # observations dropped because another series lacked the date


def _finite(value: float) -> float:
    if isinstance(value, bool):
        raise InvalidSeries("Boolean is not a numeric observation")
    if isinstance(value, (str, bytes)):
        raise InvalidSeries("Text is not a numeric observation; parse it in the provider adapter")
    try:
        out = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InvalidSeries(f"Expected a finite number, got {value!r}") from exc
    if not math.isfinite(out):
        raise InvalidSeries("Missing or non-finite number")
    return out


def _ordered(points: Sequence[SeriesPoint], *, positive: bool = False) -> list[SeriesPoint]:
    """Validate and sort by date; duplicates and invalid values raise."""
    checked = []
    for point in points:
        if not isinstance(point.date, date) or isinstance(point.date, datetime):
            raise InvalidSeries(f"Expected a datetime.date, got {point.date!r}")
        value = _finite(point.value)
        if positive and value <= 0:
            raise InvalidSeries(f"Non-positive value {value!r} on {point.date.isoformat()}")
        checked.append(SeriesPoint(point.date, value))
    checked.sort(key=lambda p: p.date)
    for earlier, later in zip(checked, checked[1:]):
        if earlier.date == later.date:
            raise InvalidSeries(f"Duplicate date {later.date.isoformat()}")
    return checked


def mean(values: Sequence[float]) -> float | None:
    """Arithmetic mean, or None for an empty input."""
    checked = [_finite(v) for v in values]
    if not checked:
        return None
    return math.fsum(checked) / len(checked)


def sample_std_dev(values: Sequence[float]) -> float | None:
    """Bessel-corrected standard deviation, or None for fewer than two values."""
    checked = [_finite(v) for v in values]
    if len(checked) < 2:
        return None
    m = math.fsum(checked) / len(checked)
    variance = math.fsum((v - m) ** 2 for v in checked) / (len(checked) - 1)
    return math.sqrt(max(variance, 0.0))


def quantile(values: Sequence[float], q: float) -> float | None:
    """Linear-interpolation quantile (NumPy's default, R type 7), or None if empty."""
    if isinstance(q, bool) or not 0.0 <= q <= 1.0:
        raise ValueError("q must be between 0 and 1")
    ordered = sorted(_finite(v) for v in values)
    if not ordered:
        return None
    index = (len(ordered) - 1) * q
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return ordered[lower]
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def simple_returns(points: Sequence[SeriesPoint]) -> list[SeriesPoint]:
    """value_t / value_(t-1) - 1 between consecutive observations."""
    ordered = _ordered(points, positive=True)
    return [SeriesPoint(cur.date, cur.value / prev.value - 1) for prev, cur in zip(ordered, ordered[1:])]


def log_returns(points: Sequence[SeriesPoint]) -> list[SeriesPoint]:
    """ln(value_t / value_(t-1)) between consecutive observations."""
    ordered = _ordered(points, positive=True)
    return [SeriesPoint(cur.date, math.log(cur.value / prev.value)) for prev, cur in zip(ordered, ordered[1:])]


def max_drawdown(points: Sequence[SeriesPoint]) -> float | None:
    """Largest peak-to-trough fall as a fraction (-0.25 = 25% below the peak), or None if empty."""
    ordered = _ordered(points, positive=True)
    if not ordered:
        return None
    peak = ordered[0].value
    worst = 0.0
    for point in ordered:
        peak = max(peak, point.value)
        worst = min(worst, point.value / peak - 1)
    return worst


def align_by_date(series: Mapping[str, Sequence[SeriesPoint]]) -> AlignedSeries:
    """Keep only dates present in every series (inner join)."""
    ordered = {name: _ordered(points) for name, points in series.items()}
    if not ordered:
        return AlignedSeries(dates=[], values={}, unmatched={})
    common = set.intersection(*({p.date for p in points} for points in ordered.values()))
    dates = sorted(common)
    values = {name: [p.value for p in points if p.date in common] for name, points in ordered.items()}
    unmatched = {name: len(points) - len(dates) for name, points in ordered.items()}
    return AlignedSeries(dates=dates, values=values, unmatched=unmatched)
