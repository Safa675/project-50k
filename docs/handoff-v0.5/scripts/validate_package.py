#!/usr/bin/env python3
"""Offline package QA; does not test providers, auth, deployment or predictive quality.

Run from repository root: python scripts/validate_package.py
Requires PyYAML, jsonschema and referencing in the local environment.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import hashlib
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT=Path(__file__).resolve().parents[1]
ERRORS=[]; CHECKS=[]
def check(name, condition, detail=''):
    CHECKS.append({'name':name,'passed':bool(condition),'detail':detail})
    if not condition:ERRORS.append(name+(': '+detail if detail else ''))
def load(path):return json.loads((ROOT/path).read_text())
def walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values():yield from walk(v)
    elif isinstance(x,list):
        for v in x:yield from walk(v)

def main():
    json_files=list(ROOT.rglob('*.json'))
    for p in json_files:
        try:json.loads(p.read_text())
        except Exception as e:check('JSON parse '+str(p.relative_to(ROOT)),False,str(e))
    check('All JSON files parse',not any(x.startswith('JSON parse') for x in ERRORS),f'{len(json_files)} files')
    registry=load('requirements_registry.json');ids=[r['id'] for r in registry]
    counts=Counter(r.split('-')[0] for r in ids)
    check('Requirement counts stable',dict(counts)=={'UR':80,'FR':122,'NFR':82},str(dict(counts)))
    check('Requirement IDs unique',len(ids)==len(set(ids)))
    for prefix,filename in [('UR','06_User_Requirements.md'),('FR','07_Functional_Requirements.md'),('NFR','08_Non_Functional_Requirements.md')]:
        headings=re.findall(r'^### ('+prefix+r'-\d{3}) — ',(ROOT/'docs'/filename).read_text(),re.M)
        check(prefix+' headings match registry',set(headings)=={i for i in ids if i.startswith(prefix+'-')} and len(headings)==counts[prefix])
    trace=load('contracts/traceability.json')
    check('Traceability covers each requirement',len(trace)==len(ids) and {r['requirement_id'] for r in trace}==set(ids))
    check('Traceability related references exist',all(i in ids for r in trace for i in r['related_requirement_ids']))
    check('No product implementation falsely marked complete',all(r['implementation_status']=='NOT_IMPLEMENTED' for r in trace))
    sources=load('research/sources.json')
    sourceids={s['id'] for s in sources}
    check('Source IDs unique',len(sourceids)==len(sources))
    check('Research source count',len([s for s in sources if s['id'].startswith('R')])==15)
    anomalies=load('config/anomaly_catalog.json')
    check('28 anomaly definitions',len(anomalies)==28 and len({a['id'] for a in anomalies})==28)
    check('Anomaly source references resolve',all(s in sourceids for a in anomalies for s in a['sources']))
    check('Anomaly requirement references resolve',all(a['requirement'] in ids for a in anomalies))
    schema_files=list((ROOT/'contracts').glob('*.schema.json')); resources=[]
    for f in schema_files:
        s=json.loads(f.read_text());Draft202012Validator.check_schema(s)
        resources.append((s['$id'],Resource.from_contents(s)))
    ref_registry=Registry().with_resources(resources)
    check('JSON Schema 2020-12 structural validity',True,f'{len(schema_files)} schemas')
    for file,schema in [('fixtures/synthetic_event.json','contracts/event.schema.json'),('fixtures/synthetic_ai_answer.json','contracts/ai_answer.schema.json')]:
        validator=Draft202012Validator(load(schema),registry=ref_registry,format_checker=FormatChecker())
        errors=list(validator.iter_errors(load(file)))
        check('Fixture validates '+file,not errors,'; '.join(e.message for e in errors))
    event=load('fixtures/synthetic_event.json');answer=load('fixtures/synthetic_ai_answer.json')
    ev_ids={e['evidence_id'] for e in answer['evidence']}
    check('AI example citations resolve',all(i in ev_ids for c in answer['claims'] for i in c['evidence_ids']))
    check('Example provenance is synthetic',event['origin']==answer['origin']=='SYNTHETIC' and all(e['origin']=='SYNTHETIC' for e in event['evidence']))
    check('Example confidence not a probability',event['confidence']['calibrated_probability'] is None)
    check('Synthetic event not approved for global send',event['global_release_approved'] is False)
    api=yaml.safe_load((ROOT/'contracts/openapi.yaml').read_text())
    check('OpenAPI version 3.1.0',api.get('openapi')=='3.1.0')
    names=set(api['components']['schemas']);op_ids=[];ref_errors=[];param_errors=[]
    for node in walk(api):
        if '$ref' in node:
            r=node['$ref']
            if r.startswith('#/components/schemas/') and r.split('/')[-1] not in names:ref_errors.append(r)
            elif not r.startswith('#') and not (ROOT/'contracts'/r).exists():ref_errors.append(r)
    for path,methods in api['paths'].items():
        for method,op in methods.items():
            if method not in {'get','post','put','patch','delete','options','head'}:continue
            op_ids.append(op['operationId'])
            required=set(re.findall(r'\{(.*?)\}',path))
            got={p['name'] for p in op.get('parameters',[]) if p['in']=='path' and p.get('required')}
            if required!=got:param_errors.append(path)
            if path.startswith('/admin/') and (op.get('x-required-role')!='ADMIN' or not op.get('security')):param_errors.append(path+' admin guard')
    check('OpenAPI local references resolve',not ref_errors,str(ref_errors))
    check('OpenAPI operation IDs unique',len(op_ids)==len(set(op_ids)),f'{len(op_ids)} operations')
    check('OpenAPI path params/admin declarations',not param_errors,str(param_errors))
    check('Unsubscribe and deletion contracts present','/email/unsubscribe' in api['paths'] and '/me/deletion' in api['paths'])
    # Markdown relative links, not third-party URL liveness.
    missing=[]
    for f in ROOT.rglob('*.md'):
        if 'archive' in f.parts:continue
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',f.read_text()):
            target=target.split('#')[0]
            if not target or '://' in target or target.startswith('mailto:'):continue
            if not (f.parent/target).exists():missing.append(str(f.relative_to(ROOT))+': '+target)
    check('Active Markdown local links exist',not missing,str(missing[:20]))
    defaults=load('config/notification_defaults.json')
    check('Email safe defaults',defaults['allow_external_email'] is False and defaults['dry_run'] is True and defaults['replay_external_send'] is False and defaults['synthetic_external_send'] is False)
    check('AI quota consistent',defaults['chat_turns_per_user_daily']==10 and '10 requests/day' in (ROOT/'docs/16_API_Specification.md').read_text())
    check('Confidence enum consistent', 'confidence.mode=HEURISTIC_EVIDENCE' in (ROOT/'docs/00_Decisions_and_Corrections.md').read_text() and event['confidence']['mode']=='HEURISTIC_EVIDENCE')
    expected_score=int((100*sum(Decimal(str(event['confidence']['components'][k]))*Decimal(str(w)) for k,w in load('config/detection_defaults.json')['evidence_weights'].items())).quantize(Decimal('1'),rounding=ROUND_HALF_UP))
    check('Example evidence score matches configured formula', event['confidence']['evidence_score']==expected_score)
    archive_rows=load('reports/received_archive_hashes.json')
    archive_ok=len(archive_rows)==11 and all((ROOT/r['path']).is_file() and hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in archive_rows)
    check('Received inner archive bytes preserved',archive_ok)
    required=['START_HERE.md','AGENTS.md','CLAUDE.md','PRODUCT.md','DESIGN.md','prompts/CLAUDE_CODE_START.md','prompts/CODEX_START.md','reports/PACKAGE_AUDIT.md']
    check('Agent entry material exists',all((ROOT/p).exists() for p in required))
    actual_handoff=[p for p in ROOT.rglob('*') if p.is_file() and 'handoff' in p.name.lower()]
    check('Handoff continuation acknowledged', 'handoff' in (ROOT/'START_HERE.md').read_text().lower() and '0.4' in (ROOT/'README.md').read_text())
    proc=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,capture_output=True,text=True)
    (ROOT/'reports/reference_test_output.txt').write_text(proc.stdout+proc.stderr)
    countmatch=re.search(r'Ran (\d+) tests',proc.stdout+proc.stderr)
    executed=int(countmatch.group(1)) if countmatch else 0
    check('Reference unit suite',proc.returncode==0 and executed>0,f'{executed} tests, exit={proc.returncode}')
    detection=load('config/detection_defaults.json')
    check('Evidence-strength-v1 weights fixed',detection['evidence_weights']=={'completeness':0.35,'freshness':0.25,'integrity':0.25,'corroboration':0.15})
    check('Registry bodies occur in authoritative documents',all(r['body'] in (ROOT/r['file']).read_text() for r in registry))
    check('28 anomaly source-role mappings present',all(set(a.get('source_roles',{}))=={'method','data','background','project_heuristic','validation'} and not a['source_roles']['validation'] for a in anomalies))
    check('All role source IDs resolve',all(i in sourceids for a in anomalies for role in ('method','data','background') for i in a['source_roles'][role]))
    details=[]
    for f in list((ROOT/'docs').glob('*.md'))+list((ROOT/'prompts').glob('*.md')):
        for target in re.findall(r'`((?:contracts|prompts|templates)/[A-Za-z0-9_./-]+\.(?:json|md|yaml))`',f.read_text()):
            if not (ROOT/target).is_file():details.append(str(f.relative_to(ROOT))+': '+target)
    check('Declared active contract/prompt/template file paths exist',not details,str(details))
    contract_proc=subprocess.run([sys.executable,'scripts/audit_contract_checks.py'],cwd=ROOT,capture_output=True,text=True)
    check('Audit contract regressions',contract_proc.returncode==0,contract_proc.stdout.strip()+contract_proc.stderr.strip())
    # Packages contain no real API credentials or font binaries.
    check('No actual environment secret file',(ROOT/'.env').exists() is False)
    check('No font binaries',not any(p.suffix.lower() in {'.ttf','.otf','.woff','.woff2'} for p in ROOT.rglob('*')))
    report={'run_at_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS' if not ERRORS else 'FAIL','checks':CHECKS,'errors':ERRORS,'reference_tests_run':executed,'openapi_operations':len(op_ids),'counts':{'requirements':dict(counts),'anomalies':len(anomalies),'sources':len(sources),'scientific_references':15},'not_tested':['Live APIs/provider entitlements','Complete OpenAPI conformance validator','Application E2E/auth/RLS','Hosted deployment','LLM runtime behavior','Empirical historical anomaly performance/calibration','Impeccable or rendered UI/accessibility'],'notes':['OpenAPI QA is YAML parsing/reference/parameter/security-declaration checking, not full OpenAPI conformance certification.','The reference harness is not the production application.']}
    js=json.dumps(report,ensure_ascii=False,indent=2)+'\n';(ROOT/'reports/validation_results.json').write_text(js)
    md='# Offline validation report\n\n**Status:** '+report['status']+'\n\nExecuted '+str(executed)+' reference unit tests. Checked '+str(len(CHECKS))+' package invariants.\n\n'
    md+='| Check | Result | Detail |\n|---|---|---|\n'
    for c in CHECKS:md+='| '+c['name']+' | '+('PASS' if c['passed'] else 'FAIL')+' | '+c['detail'].replace('|','/').replace('\n',' ')+' |\n'
    md+='\n## Not verified\n'+ '\n'.join('- '+x for x in report['not_tested'])+'\n'
    (ROOT/'reports/VALIDATION_REPORT.md').write_text(md)
    print(json.dumps({'status':report['status'],'checks':len(CHECKS),'reference_tests':executed,'errors':ERRORS},indent=2))
    return 0 if not ERRORS else 1
if __name__=='__main__':sys.exit(main())
