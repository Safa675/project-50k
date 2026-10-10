"""Claim a bounded decision job and retain errors as classes/codes only."""
from __future__ import annotations
from p50k.product.ai_client import AIUnavailable
from p50k.product.decisions import evaluate
from p50k.product.queue import claim, finish
from p50k.product.settings import Settings
from p50k.product.analysis_context import use_analysis_date

def step(settings: Settings, owner: str) -> bool:
    job=claim(settings,owner)
    if not job:
        return False
    failure=None
    try:
        if len(job)>4 and job[4]=='analysis_replay':
            from p50k.product.analysis_jobs import run_analysis
            run_analysis(settings,job[1]['analysis_date'])
        else:
            with use_analysis_date(job[1].get('analysis_date','live')):
                if job[1].get('budget_bucket')=='batch':
                    evaluate(settings,job[1]['fund_code'],bucket='batch',max_calls=1)
                else:
                    evaluate(settings,job[1]['fund_code'])
    except AIUnavailable as error:
        failure=str(error)
    except Exception as error:
        failure=type(error).__name__
    finish(settings,str(job[0]),owner,failure)
    return True
