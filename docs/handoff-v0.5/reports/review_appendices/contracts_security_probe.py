"""Read-only schema counterexamples for received v0.3; no application is exercised."""
import copy
import json
from pathlib import Path
import jsonschema
import yaml
from referencing import Registry, Resource

ROOT = Path('received/Project_50K_Work_Handoff_v1/baseline/Project_50K_v0.3')
schemas = {p.name: json.loads(p.read_text()) for p in ROOT.glob('contracts/*.schema.json')}
registry = Registry().with_resources((s['$id'], Resource.from_contents(s)) for s in schemas.values())
api = yaml.safe_load((ROOT / 'contracts/openapi.yaml').read_text())
base_answer = json.loads((ROOT / 'fixtures/synthetic_ai_answer.json').read_text())
base_event = json.loads((ROOT / 'fixtures/synthetic_event.json').read_text())
results = []

def probe(name, schema, value, expectation, schema_only=True):
    errors = list(jsonschema.Draft202012Validator(schema, registry=registry, format_checker=jsonschema.FormatChecker()).iter_errors(value))
    results.append({'id': name, 'schema_accepts': not errors, 'expectation': expectation, 'classification': 'SCHEMA_CONTRACT_ONLY_NOT_APP_VULNERABILITY' if schema_only else 'CONTRACT_CHECK', 'errors': [e.message for e in errors], 'input': value})

probe('CS-P01-replay-request-missing-cutoff', api['components']['schemas']['ChatInput'], {'question_tr': 'Bu hareket neden oldu?', 'origin': 'HISTORICAL_REPLAY'}, 'Reject historical replay unless immutable bundle/version plus non-null cutoff resolves server-side.')
probe('CS-P02-live-request-carries-replay-cutoff', api['components']['schemas']['ChatInput'], {'question_tr': 'Bu hareket neden oldu?', 'origin': 'LIVE', 'replay_cutoff': '2025-01-01T00:00:00Z'}, 'Reject ambiguous live request carrying a replay cutoff.')
a = copy.deepcopy(base_answer); a['origin']='HISTORICAL_REPLAY'
probe('CS-P03-replay-answer-no-context-identity', schemas['ai_answer.schema.json'], a, 'Replay answer must retain canonical asset plus immutable context/cutoff; existing schema has no such fields.')
a=copy.deepcopy(base_answer); a['answer_tr']='İşlem hacmi 999 birimdir.'; a['claims']=[]; a['evidence']=[]
probe('CS-P04-answered-no-claims-no-evidence', schemas['ai_answer.schema.json'], a, 'A factual ANSWERED result cannot silently bypass claim/evidence validation; requires material-claim completeness at semantic boundary.')
a=copy.deepcopy(base_answer); a['claims'][0]['evidence_ids']=['ffffffff-ffff-4fff-8fff-ffffffffffff']
probe('CS-P05-dangling-evidence-reference', schemas['ai_answer.schema.json'], a, 'Semantic validator must reject nonexistent evidence IDs; schema validation alone is insufficient.')
e=copy.deepcopy(base_event); e['status']='REVIEW_REQUIRED'; e['origin']='LIVE'; e['evidence'][0]['origin']='LIVE'; e['evidence'][0]['rights_status']='UNKNOWN'
probe('CS-P06-public-event-unreleased-unknown-rights', schemas['event.schema.json'], e, 'Public Event response must reject unreleased event or unapproved public evidence; internal lifecycle schema can remain broader.')
a=copy.deepcopy(base_answer); a['evidence'][0]['locator']='javascript:alert(1)'
probe('CS-P07-unsafe-citation-locator', schemas['ai_answer.schema.json'], a, 'Generic locator is not safe hyperlink validation; final rendering must allow only validated http(s) metadata or controlled fixture links.')
a=copy.deepcopy(base_answer); a['tool_usage']={'calls':0,'web_searches':2,'elapsed_ms':60000}
probe('CS-P08-incoherent-tool-budget-metadata', schemas['ai_answer.schema.json'], a, 'Server budget accounting must enforce web_searches <= calls and actual deadline; output metadata cannot authorize spending.')
e=copy.deepcopy(base_event); e['window_start']='2026-10-02T00:00:00Z'; e['window_end']='2026-10-01T00:00:00Z'
probe('CS-P09-reversed-event-window', schemas['event.schema.json'], e, 'Semantic validation must reject reversed timestamps; JSON Schema cannot compare timestamp values.')

a=copy.deepcopy(base_answer); a['claims'][1]['calculation_id']=None
probe('CS-P10-derived-claim-missing-calculation', schemas['ai_answer.schema.json'], a, 'DERIVED numeric claim should require a resolvable deterministic calculation reference.')
n={'notification_id':'00000000-0000-4000-8000-000000000601','event_id':base_event['event_id'],'event_revision':2,'title_tr':'Önemli güncelleme','read_at':None,'created_at':'2026-10-02T00:00:00Z','delivery_class':'UPDATE'}
probe('CS-P11-documented-update-class-rejected',api['components']['schemas']['Notification'],n,'UPDATE class documented by policy and delivery-key helper must be representable in notification response.',False)

for name,s in schemas.items(): jsonschema.Draft202012Validator.check_schema(s)
print(json.dumps({'root':str(ROOT),'scope':'Static Draft 2020-12 schemas with format checking only. No API/auth/RLS/browser/email/LLM implementation exists or was tested.', 'results':results},ensure_ascii=False,indent=2))
