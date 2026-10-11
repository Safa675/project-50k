"""Agent runtime configuration from the environment; no credential is read here."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping
import os

DEFAULT_MODEL = 'gpt-6.1-sol'
DEFAULT_INPUT_PRICE = Decimal('2.5')
DEFAULT_OUTPUT_PRICE = Decimal('10')


@dataclass(frozen=True)
class RoleModel:
    model: str
    input_price: Decimal | None
    output_price: Decimal | None
    max_output_tokens: int
    effort: str

    @property
    def priced(self) -> bool:
        return (self.input_price is not None and self.output_price is not None
                and self.input_price > 0 and self.output_price > 0)


@dataclass(frozen=True)
class AgentConfig:
    mode: str = 'off'
    key_file: Path = Path('/run/secrets/openai_api_key')
    fast: RoleModel = RoleModel(DEFAULT_MODEL, DEFAULT_INPUT_PRICE, DEFAULT_OUTPUT_PRICE, 1200, 'low')
    strong: RoleModel = RoleModel(DEFAULT_MODEL, DEFAULT_INPUT_PRICE, DEFAULT_OUTPUT_PRICE, 2000, 'low')
    daily_cap_usd: Decimal = Decimal('3.00')
    total_target_usd: Decimal = Decimal('25')
    case_gap_seconds: int = 300
    timeout_seconds: int = 60

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> 'AgentConfig':
        env = os.environ if environ is None else environ
        base = env.get('P50K_AI_MODEL', DEFAULT_MODEL)
        base_in = _decimal(env.get('P50K_AI_INPUT_USD_PER_MILLION'))
        base_out = _decimal(env.get('P50K_AI_OUTPUT_USD_PER_MILLION'))
        if base == DEFAULT_MODEL:
            base_in = base_in or DEFAULT_INPUT_PRICE
            base_out = base_out or DEFAULT_OUTPUT_PRICE

        def role(prefix: str, tokens: int) -> RoleModel:
            model = env.get(f'P50K_AGENT_MODEL_{prefix}', base)
            if model == base:
                prices = (base_in, base_out)
            else:
                prices = (_decimal(env.get(f'P50K_AGENT_MODEL_{prefix}_INPUT_USD_PER_MILLION')),
                          _decimal(env.get(f'P50K_AGENT_MODEL_{prefix}_OUTPUT_USD_PER_MILLION')))
            return RoleModel(model, prices[0], prices[1], tokens, env.get('P50K_AGENT_EFFORT', 'low'))

        return cls(mode=env.get('P50K_AI_MODE', 'off'),
                   key_file=Path(env.get('P50K_OPENAI_KEY_FILE', '/run/secrets/openai_api_key')),
                   fast=role('FAST', 1200), strong=role('STRONG', 2000),
                   daily_cap_usd=_decimal(env.get('P50K_AGENT_DAILY_CAP_USD')) or Decimal('3.00'),
                   total_target_usd=_decimal(env.get('P50K_AI_TOTAL_TARGET_USD')) or Decimal('25'),
                   case_gap_seconds=_integer(env.get('P50K_AGENT_CASE_GAP_SECONDS'), 300, 0, 86400))


def _decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        return None
    return number if number.is_finite() and number > 0 else None


def _integer(value: str | None, default: int, low: int, high: int) -> int:
    try:
        number = int(value) if value is not None else default
    except ValueError:
        return default
    return min(high, max(low, number))
