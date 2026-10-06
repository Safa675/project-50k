#!/usr/bin/env python3
"""Offline audit regressions; not a production validator or proof of prose support.

Uses the documentation-validation dependencies. Writes one scoped JSON report.
"""
from copy import deepcopy
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]


def calculation_errors(answer):
    """Check the shipped RATIO provenance path only; no arbitrary evaluator."""
    errors = []
    evidence = {e['evidence_id']: e for e in answer['evidence']}
    calculations = {c['calculation_id']: c for c in answer['calculations']}
    if len(evidence) != len(answer['evidence']):
        errors.append('Duplicate evidence IDs')
    if len(calculations) != len(answer['calculations']):
        errors.append('Duplicate calculation IDs')
    claim_ids = [c['claim_id'] for c in answer['claims']]
    if len(set(claim_ids)) != len(claim_ids):
        errors.append('Duplicate claim IDs')
    for claim in answer['claims']:
        if any(i not in evidence for i in claim['evidence_ids']):
            errors.append('Unresolved claim evidence')
        calc_id = claim['calculation_id']
        if calc_id is not None and calc_id not in calculations:
            errors.append('Unresolved calculation')
        if claim['support'] == 'DERIVED' and calc_id is None:
            errors.append('Missing derived calculation')
        if calc_id in calculations:
            operand_ids = {o['evidence_id'] for o in calculations[calc_id]['operands']}
            if not operand_ids.issubset(set(claim['evidence_ids'])):
                errors.append('Calculation inputs absent from claim evidence')
    for calc in answer['calculations']:
        try:
            if calc['operation'] != 'RATIO' or len(calc['operands']) != 2:
                raise ValueError('Unsupported operation')
            vals, units = [], []
            for operand in calc['operands']:
                row = evidence[operand['evidence_id']]
                value = Decimal(row['values'][operand['field']])
                if not value.is_finite():
                    raise ValueError('Nonfinite operand')
                vals.append(value)
                units.append(row['units'][operand['field']])
            if units[0] != units[1] or vals[1] == 0 or calc['unit'] != 'ratio':
                raise ValueError('Incompatible ratio operands')
            with localcontext() as ctx:
                ctx.prec = 50
                ctx.rounding = ROUND_HALF_EVEN
                expected = vals[0] / vals[1]
            result = Decimal(calc['result'])
            if not result.is_finite() or result != expected:
                raise ValueError('Calculation mismatch')
        except (KeyError, ValueError, ArithmeticError, TypeError) as exc:
            errors.append(str(exc))
    return errors


def main():
    def load(rel):
        return json.loads((ROOT / rel).read_text())
    resources = []
    for path in (ROOT / 'contracts').glob('*.schema.json'):
        schema = json.loads(path.read_text())
        resources.append((schema['$id'], Resource.from_contents(schema)))
    registry = Registry().with_resources(resources)
    api = yaml.safe_load((ROOT / 'contracts/openapi.yaml').read_text())
    cases = []
    def check(name, passed):
        cases.append({'case': name, 'passed': bool(passed)})
    def valid(schema, payload):
        return not list(Draft202012Validator(schema, registry=registry,
                                             format_checker=FormatChecker()).iter_errors(payload))
    chat = api['components']['schemas']['ChatInput']
    check('Replay input rejects missing cutoff', not valid(chat, {'question_tr':'Ne oldu?', 'origin':'HISTORICAL_REPLAY'}))
    check('Replay input rejects null cutoff', not valid(chat, {'question_tr':'Ne oldu?', 'origin':'HISTORICAL_REPLAY','replay_cutoff':None,'replay_bundle_id':None}))
    check('Live input rejects replay cutoff', not valid(chat, {'question_tr':'Ne oldu?', 'origin':'LIVE','replay_cutoff':'2026-10-01T10:00:00Z','replay_bundle_id':'00000000-0000-4000-8000-000000000501'}))
    check('Live input accepts explicit null cutoff', valid(chat, {'question_tr':'Ne oldu?', 'origin':'LIVE','replay_cutoff':None,'replay_bundle_id':None}))
    check('Replay input accepts known cutoff', valid(chat, {'question_tr':'Ne oldu?', 'origin':'HISTORICAL_REPLAY','replay_cutoff':'2026-10-01T10:00:00Z','replay_bundle_id':'00000000-0000-4000-8000-000000000501'}))
    answer = load('fixtures/synthetic_ai_answer.json')
    answer_schema = load('contracts/ai_answer.schema.json')
    check('Answer fixture schema and ratio provenance', valid(answer_schema, answer) and not calculation_errors(answer))
    bad = deepcopy(answer); del bad['asset_id']
    check('Answer rejects absent canonical asset', not valid(answer_schema, bad))
    bad = deepcopy(answer); bad['origin']='HISTORICAL_REPLAY'
    check('Replay answer rejects null cutoff', not valid(answer_schema, bad))
    bad = deepcopy(answer); bad['claims'][1]['calculation_id']=None
    check('Derived claim rejects missing calculation ID', not valid(answer_schema,bad))
    bad = deepcopy(answer); bad['calculations']=[]
    check('Orphan calculation reference rejected semantically', bool(calculation_errors(bad)))
    bad = deepcopy(answer); bad['calculations'][0]['result']='7'
    check('Incorrect ratio rejected semantically', bool(calculation_errors(bad)))
    bad = deepcopy(answer); bad['evidence'][0]['values']['prior_slot_median']='0'
    check('Zero denominator rejected semantically', bool(calculation_errors(bad)))
    bad = deepcopy(answer); bad['evidence'][0]['units']['prior_slot_median']='TRY'
    check('Mixed ratio units rejected semantically', bool(calculation_errors(bad)))
    bad = deepcopy(answer); bad['claims'][0]['evidence_ids']=['00000000-0000-4000-8000-000000000999']
    check('Dangling evidence reference rejected semantically', bool(calculation_errors(bad)))
    event = load('fixtures/synthetic_event.json')
    public = load('contracts/public_event.schema.json')
    check('Published synthetic projection remains labeled', valid(public,event))
    for state in ('CANDIDATE','INVESTIGATING','REVIEW_REQUIRED'):
        bad=deepcopy(event); bad['status']=state
        check('Public projection rejects '+state, not valid(public,bad))
    real=deepcopy(event); real['origin']='LIVE'
    for e in real['evidence']:
        e['origin']='LIVE'; e['rights_status']='APPROVED'; e['locator']='https://example.com/official'
    check('Schema permits rights-labeled real projection (not entitlement proof)', valid(public,real))
    for rights in ('UNKNOWN','RESTRICTED','SYNTHETIC'):
        bad=deepcopy(real); bad['evidence'][0]['rights_status']=rights
        check('Real public projection rejects '+rights+' evidence', not valid(public,bad))
    bad=deepcopy(real); bad['evidence'][0]['origin']='SYNTHETIC'
    check('Real public projection rejects synthetic evidence', not valid(public,bad))
    bad=deepcopy(real); bad['evidence'][0]['locator']='javascript:alert(1)'
    check('Public locator rejects executable scheme', not valid(public,bad))
    check('UPDATE response delivery enum is supported', 'UPDATE' in api['components']['schemas']['Notification']['properties']['delivery_class']['enum'])
    editable=load('config/admin_settings.json')['editable']
    operation=api['paths']['/admin/settings/{key}']['patch']
    key_param=next(p for p in operation['parameters'] if p['name']=='key')
    check('Admin path keys match reviewed allowlist', set(key_param['schema']['enum'])==set(editable))
    check('Admin value rules match reviewed config', operation['x-setting-value-schemas']==editable)
    check('String setting value rejected', not valid(api['components']['schemas']['SettingInput'], {'value':'false','expected_version':1,'reason':'Reviewed reason text'}))
    for key in ('chat_daily_turn_limit','rvol_threshold'):
        check('Out-of-range setting rejected for '+key, not valid(editable[key],999))
    thread=api['components']['schemas']['ChatThread']
    stub={'thread_id':answer['thread_id'],'asset_id':answer['asset_id'],'origin':'HISTORICAL_REPLAY','messages':[]}
    check('Stored replay thread requires cutoff', not valid(thread,stub))
    report={'run_at_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS' if all(c['passed'] for c in cases) else 'FAIL','checks':cases,'scope':'Offline schema counterexamples, shipped ratio provenance and configuration declarations only. No runtime authorization, prose entailment, RLS, network fetch, provider rights or delivery validation.'}
    (ROOT/'reports/contract_regression_results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'checks':len(cases),'failed':[c['case'] for c in cases if not c['passed']]},indent=2))
    return 0 if report['status']=='PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
