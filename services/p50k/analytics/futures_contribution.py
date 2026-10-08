"""Static reported-contract sensitivity, not actual futures P&L or fraud evidence.

The caller admits exact-contract specifications and official daily settlement
observations. No prices, metadata, dates, or rollover contracts are inferred here.
Quantity stays fixed at the reported number of contracts; cash-settled expiry
locks the contribution thereafter. Input mappings are read only at required dates.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import (
    Context, Decimal, DecimalException, DivisionByZero, InvalidOperation,
    Overflow, ROUND_HALF_EVEN, localcontext,
)
import re


@dataclass(frozen=True)
class ContractSpecification:
    contract_id: str
    multiplier: Decimal | None
    expiry: date
    settlement_type: str  # CASH or PHYSICAL.
    currency: str
    price_unit: str  # INDEX_POINTS or TRY_PER_SHARE.
    multiplier_unit: str  # TRY_PER_INDEX_POINT or SHARES_PER_CONTRACT.


@dataclass(frozen=True)
class FuturesPosition:
    spec: ContractSpecification
    side: str  # LONG or SHORT; quantity is never signed.
    contracts: Decimal | None


@dataclass(frozen=True)
class SettlementObservation:
    spec: ContractSpecification
    mark_date: date
    settlement_price: Decimal | None


@dataclass(frozen=True)
class FuturesItem:
    contract_id: str
    side: str
    contracts: Decimal
    source_row_count: int
    multiplier: Decimal
    mark_date: date
    baseline_price: Decimal
    endpoint_price: Decimal
    pnl_try: Decimal
    contribution: Decimal


@dataclass(frozen=True)
class ExcludedContract:
    contract_id: str
    expiry: date
    reason: str = "expired_strictly_before_baseline_no_roll_assumed"


@dataclass(frozen=True)
class FuturesContribution:
    availability: str
    pnl_try: Decimal | None
    contribution: Decimal | None
    items: tuple[FuturesItem, ...]
    excluded: tuple[ExcludedContract, ...]
    reasons: tuple[str, ...]
    prices_required: int
    prices_present: int
    fund_status: str = "ABSTAINED"
    fraud_status: str = "ABSTAINED"
    origin: str = "HISTORICAL_REPLAY"
    admission: str = "CONDITIONAL_ARCHIVE_DIAGNOSTIC"
    point_in_time_admitted: bool = False
    assumption: str = "static_reported_contract_quantity_not_actual_trades_or_pnl"


def _date(value: object) -> bool:
    return isinstance(value, date) and not isinstance(value, datetime)


def _decimal(value: object, *, positive: bool = False) -> bool:
    return (isinstance(value, Decimal) and value.is_finite()
            and len(value.as_tuple().digits) <= 4096
            and abs(value.as_tuple().exponent) <= 4096
            and (value > 0 if positive else value >= 0))


def _spec_reasons(spec: object) -> list[str]:
    if not isinstance(spec, ContractSpecification):
        return ["contract_specification_required"]
    reasons = []
    identity = (re.fullmatch(r"F_[A-Z0-9]+(0[1-9]|1[0-2])([0-9]{2})", spec.contract_id)
                if isinstance(spec.contract_id, str) else None)
    if identity is None:
        reasons.append("exact_contract_identity_required")
    if not _decimal(spec.multiplier, positive=True):
        reasons.append("positive_finite_decimal_multiplier_required")
    if not _date(spec.expiry):
        reasons.append("actual_expiry_date_required")
    elif identity is not None and (int(identity[1]) != spec.expiry.month
                                  or int(identity[2]) != spec.expiry.year % 100):
        reasons.append("contract_maturity_month_disagrees_with_actual_expiry")
    if spec.settlement_type not in ("CASH", "PHYSICAL"):
        reasons.append("settlement_type_unknown")
    if spec.currency != "TRY":
        reasons.append("currency_must_be_try")
    if (spec.price_unit, spec.multiplier_unit) not in (
        ("INDEX_POINTS", "TRY_PER_INDEX_POINT"),
        ("TRY_PER_SHARE", "SHARES_PER_CONTRACT"),
    ):
        reasons.append("matching_quote_and_multiplier_units_required")
    return reasons


def calculate_futures_contribution(
    positions: Sequence[FuturesPosition], *, base_date: date, endpoint_date: date,
    fund_net_assets: Decimal | None,
    settlements: Mapping[str, Mapping[date, SettlementObservation]],
) -> FuturesContribution:
    """Sum sign * contracts * multiplier * (settlement_end - settlement_base).

    Divide TRY P&L by reported fund net assets, without treating notional as a
    NAV weight. All required exact-contract marks must be positive finite
    Decimals, even for zero-quantity rows. A physical-delivery expiry in the
    interval is unsupported. Empty positions do not establish actual zero P&L.
    Availability here concerns arithmetic only; historical admission is false.
    """
    reasons: list[str] = []
    excluded: dict[str, ExcludedContract] = {}
    required = present = 0

    def unavailable() -> FuturesContribution:
        return FuturesContribution("UNAVAILABLE", None, None, (),
            tuple(excluded.values()), tuple(dict.fromkeys(reasons)), required, present)

    if not _date(base_date) or not _date(endpoint_date) or endpoint_date < base_date:
        reasons.append("ordered_date_only_window_required")
    if not _decimal(fund_net_assets, positive=True):
        reasons.append("positive_finite_decimal_fund_net_assets_required")
    if not isinstance(settlements, Mapping):
        reasons.append("settlement_mapping_required")
    if (not isinstance(positions, Sequence) or isinstance(positions, (str, bytes))
            or not positions or len(positions) > 10000):
        reasons.append("nonempty_bounded_reported_positions_required")
        return unavailable()
    specifications: dict[str, ContractSpecification] = {}
    for index, position in enumerate(positions):
        if not isinstance(position, FuturesPosition):
            reasons.append(f"futures_position_required:{index}")
            continue
        problems = _spec_reasons(position.spec)
        reasons.extend(f"{problem}:{index}" for problem in problems)
        if position.side not in ("LONG", "SHORT"):
            reasons.append(f"explicit_long_or_short_required:{index}")
        if not _decimal(position.contracts):
            reasons.append(f"nonnegative_finite_decimal_contracts_required:{index}")
        if not problems:
            identity = position.spec.contract_id
            if identity in specifications and specifications[identity] != position.spec:
                reasons.append(f"inconsistent_duplicate_contract_specification:{identity}")
            specifications[identity] = position.spec
    if reasons:
        return unavailable()

    marks: dict[str, tuple[SettlementObservation, SettlementObservation]] = {}
    for identity, spec in specifications.items():
        if spec.expiry < base_date:
            excluded[identity] = ExcludedContract(identity, spec.expiry)
            continue
        if spec.settlement_type == "PHYSICAL" and spec.expiry <= endpoint_date:
            reasons.append(f"physical_delivery_inside_window_unsupported:{identity}")
            continue
        mark_date = min(endpoint_date, spec.expiry)
        source = settlements.get(identity)
        observations = []
        for day in dict.fromkeys((base_date, mark_date)):
            required += 1
            quote = source.get(day) if isinstance(source, Mapping) else None
            if not isinstance(quote, SettlementObservation):
                reasons.append(f"exact_settlement_missing:{identity}:{day.isoformat()}")
            elif quote.spec != spec:
                reasons.append(f"settlement_contract_specification_changed:{identity}:{day.isoformat()}")
            elif not _date(quote.mark_date) or quote.mark_date != day:
                reasons.append(f"settlement_date_mismatch:{identity}:{day.isoformat()}")
            elif not _decimal(quote.settlement_price, positive=True):
                reasons.append(f"positive_finite_decimal_settlement_required:{identity}:{day.isoformat()}")
            else:
                present += 1
                observations.append(quote)
        if len(observations) == len(dict.fromkeys((base_date, mark_date))):
            marks[identity] = (observations[0], observations[-1])
    if reasons:
        return unavailable()

    operands = [fund_net_assets]
    operands.extend(position.contracts for position in positions)
    operands.extend(spec.multiplier for spec in specifications.values())
    operands.extend(quote.settlement_price for pair in marks.values() for quote in pair)
    # Bounded deterministic arithmetic independent of the caller's precision,
    # rounding, flags and traps; sufficient headroom for products and sums.
    precision = max(80, 4 * max(len(value.as_tuple().digits) for value in operands)
                    + max(value.adjusted() for value in operands if value)
                    + max(-value.as_tuple().exponent for value in operands)
                    + len(str(len(positions))) + 20)
    context = Context(prec=precision, rounding=ROUND_HALF_EVEN,
        Emin=-999999, Emax=999999, traps=[InvalidOperation, DivisionByZero, Overflow])
    try:
        with localcontext(context):
            quantities: dict[tuple[str, str], tuple[Decimal, int]] = {}
            for position in positions:
                identity = position.spec.contract_id
                if identity in excluded:
                    continue
                key = (identity, position.side)
                quantity, count = quantities.get(key, (Decimal(0), 0))
                quantities[key] = (quantity + position.contracts, count + 1)
            items = []
            for (identity, side), (quantity, count) in quantities.items():
                baseline, endpoint = marks[identity]
                multiplier = specifications[identity].multiplier
                pnl = (Decimal(1) if side == "LONG" else Decimal(-1)) * quantity * multiplier * (
                    endpoint.settlement_price - baseline.settlement_price)
                items.append(FuturesItem(identity, side, quantity, count, multiplier,
                    endpoint.mark_date, baseline.settlement_price,
                    endpoint.settlement_price, pnl, pnl / fund_net_assets))
            total = sum((item.pnl_try for item in items), Decimal(0))
            return FuturesContribution("AVAILABLE", total, total / fund_net_assets,
                tuple(items), tuple(excluded.values()), (), required, present)
    except DecimalException:
        reasons.append("decimal_arithmetic_unavailable")
        return unavailable()
