# Project 50K — Deployment, Operations & Cost Controls

**Version:** 0.4 audit + owner decisions · **Prepared:** 2026-10-02
**Status:** implementation specification / not a claim of deployed functionality.

## 0. Confirmed ceiling and account baseline
Owner decision 2026-10-02: no existing project service accounts. Total project cost ceiling is **TRY 5,000**, excluding only Claude/Codex subscriptions used for development. This is cumulative project spend, not a monthly budget. Runtime model/search, hosting, database, market/news/on-chain access, domain, email, taxes/fees and contingency must fit inside it. No operating duration or vendor allocation has been approved.

A feasible entitlement/usage plan has not yet been verified. Do not promise that the selected four-market/on-chain target fits the ceiling. Track committed + actual + reserved costs against the remaining ceiling; separately track renewal liabilities before accepting a plan. Record quote date, currency conversion assumptions and taxes. Stop paid work before exceeding available funds; if required data/service cannot fit, report the conflict before committing or reducing the owner's target. The ceiling does not automatically authorize purchases, accounts or paid calls.

## 1. Candidate topology
Vercel for Next.js; Railway for one FastAPI service plus one durable worker; Supabase for PostgreSQL/Auth; Resend for permitted transactional email; selected LLM provider for inference/research. These are architecture choices, not provisioned services or validated plan entitlements. Check current plans, regions, function timeouts, connection limits and usage terms at deployment.

Start with PostgreSQL jobs/outbox rather than a separate Redis queue. Long-running collectors and inference orchestration do not run inside a short-lived web render. Browser refresh reads cached application data; it does not fan out to market providers.

## 2. Environment contract
Use `.env.example`, keep real secrets outside git. Frontend gets only explicitly public Supabase URL/publishable key; service-role, LLM, email and provider keys stay server-side. Exact hosted variable names and model identifiers are checked in current provider docs during implementation, not guessed.

Separate development, staging and production identities/databases. Local synthetic fixtures are safe by default; staging email uses dry-run or a small verified recipient allowlist. `ALLOW_EXTERNAL_EMAIL=false` is the default. Production never auto-creates demo data or bypasses Google auth.

## 3. Deployment checklist
1. Clear competition, data rights, privacy notice, vendor processing and spending gates.
2. Resolve supported package versions; commit lockfiles; build and test in CI.
3. Configure Supabase Google provider, consent screen and exact redirect allowlist. Validate JWT/session server-side and RLS with two accounts.
4. Apply reviewed migrations, constraints, role tables and backups. Enable only licensed provider routes and actual capabilities.
5. Deploy API/worker with least-privilege credentials; verify CORS, TLS, health and job lease recovery.
6. Deploy web and inspect real narrow/desktop layouts. Enable live mode only per-provider after spike acceptance.
7. Verify sender domain, unsubscribe and outbox dry-run before a single authorized test email; enable broader sending only after release approval.
8. Record version, config hash, prompt version, data coverage, incident owner and rollback action.

This package performs none of these remote actions.

## 4. Observability
Record request ID, job ID, event revision, provider, latency, retries, status, data mode and cost counters. Do not log tokens, full private chats or email bodies. Dashboard: source freshness, detector enabled/disabled status, alerts per asset-day, tool failures, unknown-confidence rate, outbox age, unique eligible notifications, opt-outs and user feedback. “Average confidence” alone is not a quality metric.

Health checks distinguish liveness from readiness and upstream degradation. Provider outage should not crash authenticated browsing. Add an admin pause for ingestion, generation and external mail separately, with audit history.

## 5. Failure runbook
| Incident | Immediate action | Recovery |
|---|---|---|
| Bad source data | Quarantine affected source/interval; stop derived notifications | Re-ingest validated version; recompute and issue correction |
| LLM citation fabrication | Block explanation publication, preserve deterministic facts | Review evidence/tool trace; rerun guarded template |
| Email storm | Disable external sending; retain outbox audit | Fix dedup/eligibility, cancel stale jobs, controlled test |
| Credentials exposed | Revoke keys and stop affected service | Rotate, inspect logs/access, security incident response |
| Chain reorganization | Withdraw unfinalized event; suppress eligibility | Reconcile canonical block/signature states |
| Database restore | Pause workers/sends | Restore, reconcile provider IDs and idempotency keys before restart |

## 6. Cost model — illustrative variables, not vendor quotes
Monthly cost = hosting + database/storage + market/news/on-chain rights and API fees + email + LLM input/output + paid web-search calls + monitoring. Data licensing may dominate; no free-plan guarantee is assumed.

For inference, calculate `calls × (input_tokens × input_price + output_tokens × output_price) / 1,000,000 + tool_calls × tool_price`. Example workload assumption only: 100 active users × 2 chats/day × 30 days = 6,000 monthly chats, before event explanations. Substitute actual current prices and measured usage in `templates/COST_WORKSHEET.md`. This monthly workload example is not an approved deployment plan and must not turn the TRY 5,000 total ceiling into a monthly allowance.

Proposed caps: 10 user chat turns/day, 2 research searches/turn, 8 evidence sources/turn, 6 tool calls/turn, 45-second total request deadline. They are configurable and unvalidated UX defaults. Share one cached event explanation across users when allowed; do not send one LLM request per notification recipient. Apply daily project budget and safe degraded mode. Public chat is disabled until abuse/cost controls are accepted.

## 7. Rollback and retention
Keep immutable detector/prompt/config versions for events. Rollback code and config independently; retain user preferences and notification ledger. Recomputed event revisions do not imply a fresh notification unless materially changed. Proposed retention periods require review, minimization and tests; see domain/security documents.

## 2026-10-03 risk review

Current selected-plan feasibility and operating horizon are unknown. Dated public list prices in the data/cost review are not a complete commercial quote; hand-authored runway/turn examples are not bills. No paid commitment authorized. Current synthesis: reports/RISK_REVIEW.md; register: research/risk_review/RISK_REGISTER.json.
