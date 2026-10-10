"""Claim a bounded decision job and retain errors as classes/codes only."""
from __future__ import annotations
from p50k.product.ai_client import AIUnavailable
from p50k.product.decisions import evaluate
from p50k.product.queue import claim, finish
from p50k.product.settings import Settings

def step(settings: Settings, owner: str) -> bool:
    job=claim(settings,owner)
    if not job:
        return False
    failure=None
    try:
        evaluate(settings,job[1]['fund_code'])
    except AIUnavailable as error:
        failure=str(error)
    except Exception as error:
        failure=type(error).__name__
    finish(settings,str(job[0]),owner,failure)
    return True
