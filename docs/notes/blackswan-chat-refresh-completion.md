# BlackSwan chat and refresh completion, 2026-10-10

## Result and requirement IDs

T5.2: owner-scoped fund chat with four bounded read-only tools, session CSRF,
validated SSE, evidence references, budget reservations, 30 turns/user/Istanbul
day, three model calls, six tool calls and a bounded turn deadline. No unvalidated
model tokens reach the UI. Questions reject obvious private/secret/raw-value
input; this is a development guard, not a claim of complete PII detection.

T5.1 (partial): completed overnight inputs imported and deterministic results
refreshed using the original single calibration. Downloads continue; the final
complete import and gated live batch remain to do. T1.7a is complete under
Mirza's delegated audit authorization. T3.1 paid account/model and one decision
smoke passed; the full tuning/INVALID-rate gate remains open.

DEC-032 permanently records the selected B2B evidence-data/API offer for banks
and financial institutions, with Turkish funds and stocks in the hackathon demo.
Insurance work is deferred. Stock support is required and not implemented yet.
Mirza asked to finish this block and pause for alignment; start no new stock or
story feature until he resumes. No frozen requirement registry was edited.

## Changed files

Implementation `726c81d`: `services/p50k/product/chat.py`, `chat_tools.py`,
`chat_routes.py`, `overnight_import.py`; registered routes in `app.py`; safe
failure handling in `ai_client.py`, `decisions.py`, `validator.py`; SQL migrations
006/007 bind immutable turns/messages to evidence, run and owner. Budget SQL
waits are bounded. Existing applied migrations and calibrated modules were not
rewritten. The follow-up prompt correction aligns the same validator with plain
Turkish explanations and gives safe rejection feedback, without weakening it.

Web: `ChatPanel.tsx`, its CSS, `chat-stream.ts`, fund layout and responsive review
styles in `product.css`; synthetic stream/browser tests. Backend tests cover
chat privacy/schema/tools/call limits/owner/quota/provenance and refresh
hashes/revisions/A-to-B-to-A/ambiguity/lookahead/rollback/catalog preservation.
Migration fixtures now use the next unused version 008.

Records: AGENTS, DEC-031 follow-up, DEC-032, current state, product direction,
team asks, build plan, refresh/mapping notes and this completion report.
Operational commands are in `ops/local/BLACKSWAN.md`.

## Real import and live checks

Atomic import `cd09b3c5-b8ab-4bb1-b9bb-b8d571fc991a` captured 814 completed price
files, 996 KAP index files and the completed snapshot database. Inserted 13,101
prices, 2,131 snapshots and 10,819 KAP indexes; 186,365 price and 22 index inputs
were semantic duplicates. Missing prices stayed null. Two new snapshot codes
stay external, preserving the fixed 2,133-fund universe/categories.

Product totals: 1,738,179 price rows, 3,304 snapshots, 12,111 KAP documents,
2,133 catalog funds, seven migrations and one calibration. No new KAP PDFs or
holdings series were invented. New prices are available at acquisition; KAP
uses conservative import admission because existing metadata records request
start, with unknown response-completion time. Original observations remain.

Refreshed run `133a58c1-606c-42f4-8750-0102af458bcb`: 17,064 results, as-of
2026-10-09, same version `all-funds-v2-e8cf9c22c8ba3d47`. Ten name checks matched
the archived list and appeared in the hash-verified PDF. Product appended 131
identity-confirmed event versions; publication time stays unknown, so all
regulatory detector results abstain. Original candidates and sealed sources stay.

Mirza supplied the ignored key; tools checked existence only. Runtime-mounted
`gpt-6.1-sol` produced a VALID fund proposal. First chat attempt was rejected and
withheld; after a prompt correction, live chat produced a VALID cited answer.
Five paid Responses calls across these checks booked USD 0.048630 conservatively;
zero reservations remain and zero real mock decisions exist. This is a smoke
result, not the required tuning-rate measurement or validated answer accuracy.

## Exact verification

From the WSL clone at `726c81d`, with `PYTHONDONTWRITEBYTECODE=1`:

| Command | Actual result |
|---|---|
| `PYTHONPATH=services .venv/bin/python -m unittest discover -s tests -t . -v` | 858 in 68.941s, OK, 55 skips: 53 opt-in PostgreSQL and two Windows-specific |
| Price detector directory: `../../../../.venv/bin/python -m unittest test_detectors -q` | 9 in 0.310s, OK |
| Frozen handoff directory: `../../.venv/bin/python -m unittest discover -s tests -q` | 88 in 0.003s, OK |

Actual isolated PostgreSQL checks on the final source:

- `docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm -e P50K_DB_NAME=p50k_dev -e P50K_TEST_DATABASE=1 --volume ./tests:/app/tests:ro --volume ./db:/app/db:ro migrate python -m unittest tests.unit.test_product_migrations -q`: 16 in 0.927s, OK, zero skips.
- `docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm -e P50K_DB_NAME=p50k_dev -e P50K_TEST_ENDPOINTS=true -e P50K_TEST_DATABASE=1 --volume ./tests:/app/tests:ro --volume ./services:/app/services:ro worker python -m unittest tests.unit.test_product_chat tests.unit.test_product_overnight_import tests.unit.test_product_auth tests.unit.test_product_ai tests.unit.test_product_decisions -q`: 48 in 4.138s, OK, zero skips. Includes concurrency, CSRF, immutable audit, failed output and queue/override flows.

Web worktree: `npm run typecheck` exit 0; `npm test` nine pass;
`npm run test:browser` seven pass on synthetic 3071/8771, including actual AI_OFF,
fragmented SSE, rejected partial text, CSRF, thread identity and mobile overflow.
Docker API/web images build successfully. Latest prompt change is covered by
the final 48 checks and paid smoke; the full Linux suite was not repeated for
that prompt-only correction. Linux log: `../logs/chat-refresh-root.log` outside git.

Native Windows runtime import command used `.venv/Scripts/python.exe -m
p50k.product.overnight_import --overnight-dir
C:/Users/mirza/.local/share/project-50k/overnight/2026-10-10`, with explicit local
database host/port/credential-file settings. The CLI printed only counts/hashes.
`python -m p50k.product.cli run-detectors` ran afterward with the same settings.
Paid checks used a Compose worker with `compose.ai.yaml`, `P50K_AI_MODE=live`;
they printed status only. Leak scans before every commit/merge must return zero.

## Runtime and remaining work

Product web 3070/API 8770/DB 5433 run locally, with live on-demand AI enabled under
the existing caps. Credentials are in ignored `secrets/local-admin-login.json`;
key contents never appear in git or tool output. The original research listeners
3060/8767/8768 remain unchanged. Main was safely pulled by Mirza to `603a09d`;
build edits remain in `project-50k-app`, branch `product/build`, the same Git repo.

Data mode is local DELAYED, rights UNREVIEWED; tests are synthetic. Every detector
figure is a development result. No fraud, prediction, sales entitlement or
accuracy claim. Stocks, agent-team/B2B story, designs, complete download refresh,
20-call tuning/gated batch, backup/restore and cold-boot rehearsal remain. The
expanded stock requirement is the main schedule risk. K1–K6 and after-event
research remain recorded. Next on resume: align the smallest real stock slice
and source, then build it in parallel with the B2B workflow and supplied design.
