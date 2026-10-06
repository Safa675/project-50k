# Offline validation report

**Status:** PASS

Executed 88 reference unit tests. Checked 43 package invariants.

| Check | Result | Detail |
|---|---|---|
| All JSON files parse | PASS | 81 files |
| Requirement counts stable | PASS | {'UR': 80, 'FR': 122, 'NFR': 82} |
| Requirement IDs unique | PASS |  |
| UR headings match registry | PASS |  |
| FR headings match registry | PASS |  |
| NFR headings match registry | PASS |  |
| Traceability covers each requirement | PASS |  |
| Traceability related references exist | PASS |  |
| No product implementation falsely marked complete | PASS |  |
| Source IDs unique | PASS |  |
| Research source count | PASS |  |
| 28 anomaly definitions | PASS |  |
| Anomaly source references resolve | PASS |  |
| Anomaly requirement references resolve | PASS |  |
| JSON Schema 2020-12 structural validity | PASS | 6 schemas |
| Fixture validates fixtures/synthetic_event.json | PASS |  |
| Fixture validates fixtures/synthetic_ai_answer.json | PASS |  |
| AI example citations resolve | PASS |  |
| Example provenance is synthetic | PASS |  |
| Example confidence not a probability | PASS |  |
| Synthetic event not approved for global send | PASS |  |
| OpenAPI version 3.1.0 | PASS |  |
| OpenAPI local references resolve | PASS | [] |
| OpenAPI operation IDs unique | PASS | 25 operations |
| OpenAPI path params/admin declarations | PASS | [] |
| Unsubscribe and deletion contracts present | PASS |  |
| Active Markdown local links exist | PASS | [] |
| Email safe defaults | PASS |  |
| AI quota consistent | PASS |  |
| Confidence enum consistent | PASS |  |
| Example evidence score matches configured formula | PASS |  |
| Received inner archive bytes preserved | PASS |  |
| Agent entry material exists | PASS |  |
| Handoff continuation acknowledged | PASS |  |
| Reference unit suite | PASS | 88 tests, exit=0 |
| Evidence-strength-v1 weights fixed | PASS |  |
| Registry bodies occur in authoritative documents | PASS |  |
| 28 anomaly source-role mappings present | PASS |  |
| All role source IDs resolve | PASS |  |
| Declared active contract/prompt/template file paths exist | PASS | [] |
| Audit contract regressions | PASS | {   "status": "PASS",   "checks": 31,   "failed": [] } |
| No actual environment secret file | PASS |  |
| No font binaries | PASS |  |

## Not verified
- Live APIs/provider entitlements
- Complete OpenAPI conformance validator
- Application E2E/auth/RLS
- Hosted deployment
- LLM runtime behavior
- Empirical historical anomaly performance/calibration
- Impeccable or rendered UI/accessibility
