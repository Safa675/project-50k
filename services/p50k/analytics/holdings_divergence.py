"""A publication-bounded, signed-spot-equity proxy for fund unit returns.

The reported month-end position values supply frozen opening weights. This is
an arithmetic sensitivity diagnostic, never an estimate of actual daily trades,
a full-fund replication, or a fraud classifier. Decimal values, source absence
and the shared market calendar remain explicit. No file or provider is read.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import (
    Context, Decimal, DecimalException, DivisionByZero, InvalidOperation,
    Overflow, ROUND_HALF_EVEN, localcontext,
)
from zoneinfo import ZoneInfo


_LOCAL = ZoneInfo("Europe/Istanbul")
_MAX_POSITIONS = 10000
_MAX_DIGITS = 4096
_ZERO = Decimal(0)
_ONE = Decimal(1)
_CAVEATS = (
    "research_diagnostic_only",
    "frozen_reported_weights_not_observed_daily_positions",
    "signed_negative_rows_economic_meaning_unknown",
    "historical_vendor_publication_and_price_revisions_unknown",
    "tefas_previous_common_market_session_alignment_assumed",
    "unmodeled_futures_cash_yield_fees_trading_and_dividends",
    "no_full_fund_or_fraud_inference",
)


@dataclass(frozen=True)
class StockPosition:
    isin: str
    price_symbol: str | None
    reported_value: Decimal | None


@dataclass(frozen=True)
class HoldingsSnapshot:
    snapshot_id: str
    reported_period_end: date
    available_at: datetime
    fund_net_assets: Decimal | None
    positions: tuple[StockPosition, ...]
    problems: tuple[str, ...] = ()
    futures_present: bool = False


@dataclass(frozen=True)
class GapDiagnostic:
    availability: str  # AVAILABLE or UNAVAILABLE, not a detector status.
    actual_return: Decimal | None
    equity_proxy_return: Decimal | None
    gap: Decimal | None
    net_equity_weight: Decimal | None
    gross_equity_weight: Decimal | None
    security_count: int
    prices_required: int
    prices_present: int
    signed_weights: tuple[tuple[str, str, Decimal], ...]
    reasons: tuple[str, ...]
    gross_reported_position_weight: Decimal | None = None
    negative_reported_position_count: int = 0
    futures_present: bool = False
    caveats: tuple[str, ...] = _CAVEATS
    fund_status: str = "ABSTAINED"
    fraud_status: str = "ABSTAINED"


@dataclass(frozen=True)
class DiagnosticRow:
    valuation_date: date
    fund_row_label: date | None
    interval_number: int
    metric: GapDiagnostic


@dataclass(frozen=True)
class DiagnosticWindow:
    snapshot_id: str
    reported_period_end: date
    available_at: datetime
    next_publication_date: date | None
    base_date: date | None
    base_fund_row_label: date | None
    rows: tuple[DiagnosticRow, ...]
    reasons: tuple[str, ...] = ()


def _known_text(value: object) -> bool:
    return (isinstance(value, str) and bool(value.strip())
            and value.strip().upper() not in ("UNKNOWN", "UNVERIFIED"))


def _date_only(value: object) -> bool:
    return isinstance(value, date) and not isinstance(value, datetime)


def _valid_decimal(value: object) -> bool:
    return (isinstance(value, Decimal) and value.is_finite()
            and len(value.as_tuple().digits) <= _MAX_DIGITS
            and abs(value.as_tuple().exponent) <= _MAX_DIGITS)


def _context(values: Sequence[Decimal]) -> Context:
    # Exact additions of the bounded source decimals, followed by deterministic
    # finite-precision ratios. Never inherit caller rounding or trap settings.
    nonzero = [value for value in values if value]
    precision = max(80, max((v.adjusted() for v in nonzero), default=0)
                    + max((-v.as_tuple().exponent for v in nonzero), default=0)
                    + len(str(len(values) + 1)) + 20)
    return Context(prec=precision, rounding=ROUND_HALF_EVEN,
                   Emin=-999999, Emax=999999,
                   traps=[InvalidOperation, DivisionByZero, Overflow])


def _snapshot_reasons(snapshot: HoldingsSnapshot) -> list[str]:
    reasons = list(snapshot.problems)
    if not _known_text(snapshot.snapshot_id):
        reasons.append("snapshot_id_unknown")
    if not _date_only(snapshot.reported_period_end):
        reasons.append("reported_period_end_invalid")
    aware = (isinstance(snapshot.available_at, datetime)
             and snapshot.available_at.tzinfo is not None
             and snapshot.available_at.utcoffset() is not None)
    if not aware:
        reasons.append("publication_timezone_required")
    elif (_date_only(snapshot.reported_period_end)
          and snapshot.reported_period_end > snapshot.available_at.astimezone(_LOCAL).date()):
        reasons.append("report_period_after_publication")
    if not _valid_decimal(snapshot.fund_net_assets) or snapshot.fund_net_assets <= 0:
        reasons.append("positive_finite_decimal_fund_net_assets_required")
    if not isinstance(snapshot.positions, tuple) or not snapshot.positions:
        reasons.append("reported_stock_positions_required")
    elif len(snapshot.positions) > _MAX_POSITIONS:
        reasons.append("position_count_out_of_bounds")
    else:
        for index, position in enumerate(snapshot.positions):
            if not isinstance(position, StockPosition):
                reasons.append(f"stock_position_required:{index}")
                continue
            if not _known_text(position.isin):
                reasons.append(f"isin_unknown:{index}")
            if not _known_text(position.price_symbol):
                reasons.append(f"price_identity_unknown:{position.isin}")
            if not _valid_decimal(position.reported_value):
                reasons.append(f"reported_position_value_invalid:{position.isin}")
    return reasons


def _unavailable(reasons: Sequence[str], *, count: int = 0,
                 prices_present: int = 0, weights: tuple[tuple[str, str, Decimal], ...] = (),
                 net: Decimal | None = None, gross: Decimal | None = None,
                 printed_gross: Decimal | None = None, negative_rows: int = 0,
                 futures_present: bool = False) -> GapDiagnostic:
    return GapDiagnostic("UNAVAILABLE", None, None, None, net, gross,
                         count, 2 * count, prices_present, weights,
                         tuple(dict.fromkeys(reasons)), printed_gross,
                         negative_rows, futures_present)


def calculate_holdings_gap(
    snapshot: HoldingsSnapshot, *, base_date: date, valuation_date: date,
    prices: Mapping[str, Mapping[date, Decimal | None]],
    base_nav: Decimal | None, end_nav: Decimal | None,
) -> GapDiagnostic:
    """Calculate sum(w_i * (close_end / close_base - 1)), then NAV minus proxy.

    Duplicate ISIN rows are aggregated before dividing by reported fund net
    assets. They must share one explicit price identity. Every reported security,
    including zero-value positions, requires both positive Decimal closes. Cash
    is implicitly zero-return; equities are never normalized to 100%. Futures
    notional is not a spot position and is not accepted in this input type.
    """
    reasons = _snapshot_reasons(snapshot)
    if not _date_only(base_date) or not _date_only(valuation_date) or base_date >= valuation_date:
        reasons.append("strictly_increasing_market_dates_required")
    elif (isinstance(snapshot.available_at, datetime) and snapshot.available_at.tzinfo is not None
          and snapshot.available_at.utcoffset() is not None
          and base_date <= snapshot.available_at.astimezone(_LOCAL).date()):
        reasons.append("baseline_must_be_after_publication_date")
    for name, nav in (("baseline", base_nav), ("endpoint", end_nav)):
        if not _valid_decimal(nav) or nav <= 0:
            reasons.append(f"{name}_positive_finite_decimal_nav_required")
    if not isinstance(prices, Mapping):
        reasons.append("price_mapping_required")
    if reasons:
        return _unavailable(reasons, futures_present=snapshot.futures_present)

    aggregate: dict[str, tuple[str, Decimal]] = {}
    symbol_isin: dict[str, str] = {}
    operands = [snapshot.fund_net_assets, base_nav, end_nav]
    operands.extend(position.reported_value for position in snapshot.positions)
    for position in snapshot.positions:
        existing = aggregate.get(position.isin)
        if existing and existing[0] != position.price_symbol:
            reasons.append(f"contradictory_price_identity:{position.isin}")
        other_isin = symbol_isin.get(position.price_symbol)
        if other_isin and other_isin != position.isin:
            reasons.append(f"price_symbol_has_multiple_isins:{position.price_symbol}")
        symbol_isin[position.price_symbol] = position.isin
        aggregate.setdefault(position.isin, (position.price_symbol, _ZERO))
    if reasons:
        return _unavailable(reasons, count=len(aggregate), futures_present=snapshot.futures_present)

    price_pairs: dict[str, tuple[Decimal, Decimal]] = {}
    present = 0
    for isin, (symbol, _) in sorted(aggregate.items()):
        history = prices.get(symbol)
        if not isinstance(history, Mapping):
            reasons.append(f"price_series_missing:{symbol}")
            continue
        pair = []
        for name, day in (("baseline", base_date), ("endpoint", valuation_date)):
            close = history.get(day)
            if not _valid_decimal(close) or close <= 0:
                reasons.append(f"{name}_positive_finite_decimal_close_required:{symbol}")
            else:
                present += 1
                pair.append(close)
                operands.append(close)
        if len(pair) == 2:
            price_pairs[isin] = tuple(pair)
    try:
        with localcontext(_context(operands)):
            for position in snapshot.positions:
                symbol, amount = aggregate[position.isin]
                aggregate[position.isin] = (symbol, amount + position.reported_value)
            weights = tuple((isin, symbol, amount / snapshot.fund_net_assets)
                            for isin, (symbol, amount) in sorted(aggregate.items()))
            net = sum((weight for _, _, weight in weights), _ZERO)
            gross = sum((weight.copy_abs() for _, _, weight in weights), _ZERO)
            printed_gross = sum((position.reported_value.copy_abs() for position in snapshot.positions), _ZERO) / snapshot.fund_net_assets
            negative_rows = sum(position.reported_value < 0 for position in snapshot.positions)
            if reasons:
                return _unavailable(reasons, count=len(weights), prices_present=present,
                                    weights=weights, net=net, gross=gross,
                                    printed_gross=printed_gross, negative_rows=negative_rows,
                                    futures_present=snapshot.futures_present)
            proxy = sum((weight * (price_pairs[isin][1] / price_pairs[isin][0] - _ONE)
                         for isin, _, weight in weights), _ZERO)
            actual = end_nav / base_nav - _ONE
            gap = actual - proxy
    except DecimalException:
        return _unavailable(("arithmetic_not_representable",), count=len(aggregate),
                            prices_present=present, futures_present=snapshot.futures_present)
    return GapDiagnostic("AVAILABLE", actual, proxy, gap, net, gross,
                         len(weights), 2 * len(weights), present, weights, (),
                         printed_gross, negative_rows, snapshot.futures_present)


def build_diagnostic_windows(
    snapshots: Sequence[HoldingsSnapshot], *, market_sessions: Sequence[date],
    fund_nav_by_label: Mapping[date, Decimal | None],
    prices: Mapping[str, Mapping[date, Decimal | None]],
    fund_label_cutoff: date, max_intervals: int = 20,
) -> tuple[DiagnosticWindow, ...]:
    """Build up to 20 return intervals starting after each local publication day.

    TEFAS label D maps to the preceding *shared-calendar* market session. Missing
    per-stock bars do not move this alignment. Endpoint valuation dates must be
    strictly before the next KAP publication day, and labels after the fixed
    research cutoff are never read. Duplicate labels mapping to a valuation date
    fail closed for that date; no averaging, forward fill or rebalance is used.
    """
    sessions = tuple(market_sessions)
    if (not sessions or any(not _date_only(day) for day in sessions)
            or sessions != tuple(sorted(set(sessions)))):
        raise ValueError("market sessions must be nonempty, distinct and sorted dates")
    if not _date_only(fund_label_cutoff):
        raise ValueError("fund label cutoff must be a date")
    if isinstance(max_intervals, bool) or not isinstance(max_intervals, int) or not 1 <= max_intervals <= 20:
        raise ValueError("research windows require 1 to 20 return intervals")
    if not isinstance(fund_nav_by_label, Mapping) or any(not _date_only(day) for day in fund_nav_by_label):
        raise ValueError("fund NAV labels must be distinct dates")
    if any(not isinstance(snapshot.available_at, datetime)
           or snapshot.available_at.tzinfo is None or snapshot.available_at.utcoffset() is None
           for snapshot in snapshots):
        raise ValueError("all snapshot publication times must be timezone-aware")
    if len({snapshot.snapshot_id for snapshot in snapshots}) != len(snapshots):
        raise ValueError("snapshot IDs must be distinct")
    publications = [snapshot.available_at for snapshot in snapshots]
    if len(set(publications)) != len(publications):
        raise ValueError("duplicate snapshot publication instants are ambiguous")
    ordered = sorted(snapshots, key=lambda snapshot: snapshot.available_at)
    nav_dates: dict[date, list[tuple[date, Decimal | None]]] = {}
    for label, value in fund_nav_by_label.items():
        if label > fund_label_cutoff:
            continue
        previous = bisect_left(sessions, label) - 1
        if previous >= 0:
            nav_dates.setdefault(sessions[previous], []).append((label, value))

    def nav_at(day: date) -> tuple[date | None, Decimal | None, tuple[str, ...]]:
        candidates = nav_dates.get(day, [])
        if len(candidates) > 1:
            return None, None, ("multiple_fund_labels_for_market_session",)
        if not candidates:
            return None, None, ("fund_nav_missing_for_market_session",)
        return candidates[0][0], candidates[0][1], ()

    windows = []
    for index, snapshot in enumerate(ordered):
        publication_day = snapshot.available_at.astimezone(_LOCAL).date()
        next_day = (ordered[index + 1].available_at.astimezone(_LOCAL).date()
                    if index + 1 < len(ordered) else None)
        first = bisect_right(sessions, publication_day)
        base = sessions[first] if first < len(sessions) else None
        if base is None or base >= fund_label_cutoff or (next_day is not None and base >= next_day):
            windows.append(DiagnosticWindow(snapshot.snapshot_id, snapshot.reported_period_end,
                snapshot.available_at, next_day, None, None, (), ("no_eligible_baseline_session",)))
            continue
        base_label, base_nav, base_reasons = nav_at(base)
        rows = []
        for offset in range(1, max_intervals + 1):
            if first + offset >= len(sessions):
                break
            day = sessions[first + offset]
            if day >= fund_label_cutoff or (next_day is not None and day >= next_day):
                break
            label, end_nav, end_reasons = nav_at(day)
            if base_reasons or end_reasons:
                metric = _unavailable(base_reasons + end_reasons,
                                      futures_present=snapshot.futures_present)
            else:
                metric = calculate_holdings_gap(snapshot, base_date=base, valuation_date=day,
                    prices=prices, base_nav=base_nav, end_nav=end_nav)
            rows.append(DiagnosticRow(day, label, offset, metric))
        windows.append(DiagnosticWindow(snapshot.snapshot_id, snapshot.reported_period_end,
            snapshot.available_at, next_day, base, base_label, tuple(rows),
            ("no_eligible_return_interval",) if not rows else ()))
    return tuple(windows)
