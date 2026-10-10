"""D7 allowlist: model inputs cannot carry raw NAV, AUM, KAP text or user data."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    evidence_id: str = Field(max_length=100)
    detector_id: str = Field(max_length=30)
    state: Literal['TRIGGERED','NOT_TRIGGERED','ABSTAINED']
    value: str | None = Field(max_length=100)
    threshold: str | None = Field(max_length=100)
    effective_date: str | None = Field(max_length=40)
    is_attribute: bool

class Packet(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    fund_code: str = Field(max_length=12)
    fund_name: str = Field(max_length=300)
    category: str | None = Field(max_length=200)
    as_of: str = Field(max_length=40)
    evidence: list[Evidence] = Field(max_length=8)
    allowed_options: list[str] = Field(max_length=4)

def allowed_options(evidence: list[Evidence]) -> list[str]:
    covered = [item for item in evidence if not item.is_attribute and item.detector_id in {'D1','D2','D3','D4'} and item.state!='ABSTAINED']
    event = any(item.detector_id=='AN-FND-005' and item.state=='TRIGGERED' for item in evidence)
    triggered = any(not item.is_attribute and item.state=='TRIGGERED' for item in evidence)
    if event:
        return ['MATERIAL','INSUFFICIENT_EVIDENCE']
    if not covered and not triggered:
        return ['INSUFFICIENT_EVIDENCE']
    choices = ['INSUFFICIENT_EVIDENCE']
    if covered:
        choices.append('NOT_MATERIAL')
    if triggered:
        choices.extend(['MATERIAL','DATA_ISSUE'])
    return choices
