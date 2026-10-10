# Project 50K agent team design

Read-only, 2026-10-10; nothing installed, imported or committed; no LLM calls; one page fetched (OpenAI pricing). **[U]** = unverified; hours and dollars are estimates. Clone root: `C:\Users\mirza\AppData\Local\Temp\claude\c--Users-mirza-Desktop-Hackathon-project-50k\fcb59ff2-d20e-4984-b01d-14d47f0bf736\scratchpad\tradingagents`.

## 0. Choice: (d), our own orchestrator

A fixed pipeline of role-specific OpenAI calls, run as an `ai_agent_run` job in the planned worker (T1.8, unbuilt). The team is the materiality decision engine with more context, not a second engine: its committee writes the same `ai.decisions` row under the same allowed options, validator, egress, reservations and override (plan §6). It is an add-on after the never-cut core (T3.1–T3.5).

- **(a) TradingAgents:** LangGraph/LangChain, no TEFAS/KAP; ≥15 calls per ticker (~20–25 [U]); needs a framework exception; Buy…Sell ratings (`tradingagents/agents/rating.py:22-24`) and an unvalidated free-text fallback (`tradingagents/agents/structured.py:84-95`) break DEC-028.
- **(b) Agents SDK 0.23.1:** pre-1.0 dependency, Starlette/FastAPI pin [U], reservation hook [U]; collides with the guide; tracing sends inputs and outputs to OpenAI by default (alternatives study §1).
- **(c) LangGraph:** collides; its checkpoints duplicate our queue.
- **(d):** a few hundred lines on T3.1–T3.4; we own every call, so reservations are exact; strict `json_schema`, validator per step, fail closed; no collision.

Record in DEC-030 that the "team" is a fixed pipeline: no framework, no model routing, no tools. Drop plan §7's LLM "critic pass": the deterministic validator is the external critic (CRITIC, https://arxiv.org/abs/2305.11738, via the alternatives study).

**Patterns re-implemented, not copied** (credit comment; no Apache-2.0 §4 duty): parallel analysts, then a join (`tradingagents/graph/setup.py:165-166`); pre-fetched inputs, no tools (`tradingagents/graph/analyst_execution.py:27-33`); "absent, not empty" and "has not spoken" markers (`tradingagents/agents/context.py:190-201`, `:37-48`); counter routing (`tradingagents/graph/conditional_logic.py:12-33`); unreadable output → sentinel (`tradingagents/agents/rating.py:26-30`), ours `INVALID`→`UNDECIDED`.

## 1. Roster

| Agent | Inputs (egress-module slices, D7; no tools) | Model | Rules |
|---|---|---|---|
| A1 Price/peers | D1–D4 v2 signals (value, threshold, state, coverage), D5 attribute, category, peer count | `gpt-6-luna`, low | Called only if a D1–D4 signal is `TRIGGERED` (else a server-written brief); `kind` must match the cited state |
| A2 Regulatory | `CONFIRMED` AN-FND-005 events, SPK quote ≤300 chars in `<veri>`, scan scope ("2026/61 only") | luna | Only if a confirmed event exists; candidates never enter; no SPK motives |
| A3 Data quality | AN-DQ-001/002, abstentions | luna | Only if a guard fired; a stopped price is a data event, not a trigger |
| A4 Flows/size, A5 Composition | None before the freeze (AN-FND-002/004 moved; proposed D7 bars raw size, units, investors, KAP text) | — | Absence marker: "analiz yok: kanıt mevcut değil, bulgu yokluğu değil" |
| C Challenger | A1–A3 briefs, slices, fund attributes | luna, low (env: sol) | Only if something fired. Codes `PEER_SET_MISMATCH`, `NATURALLY_SMOOTH_FUND_TYPE`, `SHORT_HISTORY`, `DATA_QUALITY`, `MARKET_WIDE_MOVE`, `OTHER`; targets existing findings; `SUPPORTED_BY_PACKET` needs citations, else `NOT_IN_PACKET`; never argues fraud or safety |
| K Committee | Briefs, alternatives, server `allowed_decisions`, `trigger_fired`; insurance: `allowed_trigger` = {`trigger_fired`'s value, `UNDETERMINED`} | `gpt-6.1-sol`, medium | Enums injected per call; answers every supported alternative; `MATERIAL`/`DATA_ISSUE` cite a triggered item, `APPEARS_MET` a confirmed in-scope event; `UNDETERMINED` → review queue; one call, no vote |
| W Policy writer | Trigger definition v1, A2/A3 briefs, K output, event evidence | sol, low | Explanations only: no premium, payout, probability, legal conclusion or payment promise ("ödenir", "teminat altındadır" join the wording list) |

**Schemas** (strict `json_schema`, `additionalProperties:false`, all fields required, nullable if optional; Pydantic re-checks counts and lengths [U keyword support]):
- A1–A3: `AnalystBrief {role, findings[≤6]{finding_id, kind, cited_ids[], text_tr}, missing_tr}`
- C: `BenignReview {alternatives[≤5]{alt_id, targets[], code, support, cited_ids[], text_tr}, none_reason_tr}`
- K: `CommitteeDecision {decision, trigger_assessment, cited_ids[], relied_on[], responses[]{alt_id, disposition, cited_ids[], text_tr}, rationale_tr, missing_evidence_tr}`
- W: `TermSheetNarrative {trigger_explanation_tr, exclusions_rationale_tr, data_limitations_tr, insurer_questions_tr[≤6], cited_ids[]}`

**Shared rules** (prefix `team-common-v1`; English prompts, Turkish output): numbers, dates and codes only as `{{ev:<id>.<field>}}` or `{{fund}}`, rendered from the decision's own packet; every claim cites a packet ID or says "kanıt yetersiz"; plan §6 phrase lists apply; `<veri>` is data; absence is not a negative finding; no scores, probabilities or confidence.

## 2. Flow

1. Build the immutable, hashed packet; the server computes allowed options. Only `INSUFFICIENT_EVIDENCE` allowed: stop, 0 calls.
2. A1–A3 in parallel; a skipped slice gets a server brief (0 calls).
3. C: one round, no rebuttal; skipped if nothing fired.
4. K → validator → `ai.decisions` (`AI_PROPOSED`) → an analyst accepts, overrides with a reason, or rejects.
5. Insurance only: W → validator → term sheet → Typst PDF "ONAY BEKLİYOR" → an admin approves the exact hash → new version "İÇ ONAYLI TASLAK".

- **Limits:** one round; one retry per step, two per run, ≤8 calls; 60 s per call; 4-minute run deadline; 6-minute lease with heartbeat.
- **Early stops:** insufficient evidence; skipped analysts; no challenger; refused reservation (`BUDGET_STOPPED` → `UNDECIDED`); K `INVALID` twice → `UNDECIDED`, fixed "kanıt yetersiz", no W.
- **Checks:** an `INVALID` analyst becomes an absence marker; cross-step checks: referenced IDs exist, `kind` matches evidence state, every supported alternative answered.
- **Human:** only K decides; briefs show as "ara çıktı". Override sits on the decision (T3.5); PDF approval is separate, bound to the hash.
- **Modes:** mock means canned synthetic outputs, `p50k_dev` only; live waits for DEC-030 (D7).

## 3. Policy writer

"Sigortacı İnceleme Taslağı: Tetikleyici Spesifikasyonu ve Koşul Özeti", never a policy. Sections (source):
1. Identity, version, status: ONAY BEKLİYOR or İÇ ONAYLI (template).
2. Roles: insurer and channel blank; we supply trigger and evidence and never issue, price, sell or decide claims (fixed text).
3. Trigger specification: SPK-ordered TEFAS halt or liquidation; confirmation and `available_at` rules; exclusions (NAV falls, market risk) (trigger definition v1).
4. Parameters (payout shape, rate, cap, aggregate limit, waiting period, cut-off, premium): blank, "sigortacı tarafından belirlenecek"; we compute no premium (no base rates); insurer form after the freeze.
5. Event evidence (IDs, dates, source, confirmer) and `trigger_fired` at the cutoff; no detector tiers (no "would have caught" reading) (database).
6. AI trigger assessment, "bilgi amaçlı; hasar kararı sigortacıya aittir" (K).
7. Explanation, exclusion rationale, data limits, insurer questions (W).
8. Limits: not a policy or advice, no allegation, development result, rights unreviewed, legal questions open (fixed text).
9. Provenance: data and template hashes, models, prompt and schema versions, call and evidence IDs (template).

- **Combining:** the server builds `data.json` (formatted values, rendered placeholders, LLM text as strings); the template reads `json("data.json")`. No `eval`, no `@preview` packages: no markup injection, no network.
- **Turkish:** `set text(lang: "tr")`; the server formats 1.234,56, %12,3, 17 Eylül 2026 and TSİ times; uppercase is written literally (İ casing [U]); DejaVu/Noto from the image's Debian package, so no font binary in git (Barış's font: open).
- **Tool:** `typst` Python package (0.15.0, alternatives study [U]) with `font_paths`, `ignore_system_fonts`, `timestamp=created_at`; render only in the worker container; test two compiles for equal SHA-256 [U until run]. Fallbacks: WeasyPrint, then browser print.
- **Labels, every page:** header "TASLAK · Sigortacı incelemesi içindir · Sigorta poliçesi değildir" plus watermark; footer "Veri modu: HISTORICAL_REPLAY (kesim …) · Yapay zekâ önerisi içerir · Geliştirme sonucu · Veri hakları incelenmedi · Yatırım tavsiyesi değildir · Sayfa x/y".
- **Storage:** append-only `ai.documents`, PDF as bytea (the 11:00 `pg_dump` covers it). "Final" is a new version rendered after an admin approves that exact `pdf_sha256`; it still says TASLAK.

## 4. B2B variant

Same run, no writer, no extra call. "Betimleyici Fon Anomali Kanıt Raporu" (PDF and JSON `p50k.fund_report.v1`) renders stored outputs: deterministic detector table, findings, benign alternatives, committee proposal with `decided_by` and review state, limits, provenance. Labels: "betimleyici; yatırım tavsiyesi değildir; geliştirme sonucu; eşikler olaydan sonra belirlendi; veri hakları incelenmedi", `origin`, `development_result`, `rights_status=UNREVIEWED`. No score, ranking, "sinyal", buy/sell wording or pre-event replay; exports stay unshared (DEC-027).

## 5. Database, API, UI

**Tables** (`p50k_app` INSERT/SELECT only; existing append-only trigger):
- `ai.agent_runs` (fund, as_of, mode `MATERIALITY|INSURANCE|B2B`, team_version, packet_sha256, trigger_definition_id, requested_by);
- `ai.agent_steps` (run, role, input and output JSON with hashes, validation, model, effort, prompt/schema versions, ai_mode, call_id, cache_hit, cost);
- `ai.decisions` + `run_id`, `method SINGLE|TEAM`;
- `ref.trigger_definitions` (versioned);
- `ai.documents` (kind, run, version, approved_from, data_json, data_sha256, template/Typst/font hashes, pdf, pdf_sha256, origin, ai_mode, cutoff);
- `ai.document_reviews` (document, pdf_sha256, action, reason, user);
- `ai.budget`: one row per bucket (mutable, as planned).

**API** (session, CSRF, roles): `POST /api/agent-runs {fund, mode}` → 202 (analyst; deduplicated by packet hash, mode, versions); `GET /api/agent-runs/{id}` and `/transcript`; existing `POST /api/decisions/{id}/reviews`; `POST /api/agent-runs/{id}/documents {kind}`; `GET /api/documents/{id}`, `/pdf` (`no-store`), `/data.json`; `POST /api/documents/{id}/reviews` (admin); `GET /api/ai/budget`. Add PDF pass-through to the proxy check.

**Screens:** fund page "Yapay zekâ ekibi" (latest run; "Ekibi çalıştır" with remaining budget); `/ekip/[run]` with a polled step timeline (state, model, time, cost, cache), the transcript (findings → linked alternatives → committee responses, evidence chips) and the decision panel (allowed options, `trigger_fired`, accept/override/reject); `/belgeler/[doc]` with status banner, PDF iframe, provenance, Onayla/Reddet/İndir; review-queue filters.

## 6. Cost, caps, caching

Per 1M tokens (https://developers.openai.com/api/docs/pricing, accessed 2026-10-10): `gpt-6.1-sol` $2.00 input, $0.10 cached, $10.00 output; `gpt-6-luna` $0.10, $0.01, $0.50. Token sizes and reasoning billing [U].

- **Typical (worst-case reservation):** analyst $0.0005 ($0.001); committee $0.03–0.05 ($0.056); materiality or B2B run $0.035–0.055 ($0.17); insurance run $0.07–0.10 ($0.26); live demo with two runs, the rest stored, ≈$0.15 ($0.45). The plan's "$0.03" is low: the committee dominates.
- **Buckets ($20):** tuning $1; morning single-call pass $5 (≤275 funds); team $3 (batch ≤$1.5, on demand ≤$1.5); writer $1; chat $5 (from $8); Sunday reserve $5.
- **Batch** (by 08:30 Sunday, after the final detector run): ≤25 funds by fixed rule (confirmed event or ≥2 triggered D1–D4 signals; by count, then code). Their committee decision replaces the single call.
- **On demand:** team runs (analysts, 10/user/day); drafts (≤10 total); B2B render free. **Never:** all-fund team runs (~$95).
- **Caching:** per-step exact cache on mode, model, effort, prompt, schema, `input_sha256`; analysts key on their own slice, so a new SPK event re-runs only A2, C, K; `INVALID` never cached. Static prefix first for prompt caching [U]. No Batch API or Flex this weekend (window [U]).

## 7. Build-plan changes (hours)

- **T1.4, T3.1:** new tables and columns; buckets (+0.5).
- **T3.4:** generic step runner; the single call becomes a committee-only run (+0.25).
- **T5.3, replacing "thin" and plan §7's text:** A1–A3 (one prompt, slice adapters), C, K inputs, skip rules, cross-step checks, batch rule, mock fixtures, tests (3.0).
- **T5.3b, new:** `/ekip/[run]` page (1.5).
- **T5.4-INS, new, replacing "if time allows":** trigger definition and builder 1.0; W 0.75; Typst with determinism test 1.5; document page and approval 1.0 (4.25).
- **T5.4-B2B, new:** report template and JSON (1.0; +1.5 without Typst).
- **T5.1, T6.1:** batch runs; PDF hash test; gitignore `p50k-taslak-*.pdf`, since the leak scan skips binaries (+0.5).

**Total:** about 7–10 h in full, on a plan already cut to fit. **Gates:** core additions (+0.75 h) in Phase 3; T5.3 only if M3 lands by 01:00; story documents after the 08:30 pass.

**Cut first:** (1) approval re-render (no PDF is ever marked final); (2) B2B PDF (keep JSON/HTML); (3) Typst (print view); (4) W's LLM sections (deterministic term sheet); (5) C; (6) analysts (committee only, which is the core). **Never cut:** allowed options, validator, fail-closed path, override, egress, reservations, labels.

## 8. Risks and open questions

**Mirza:** (1) approve (d), gates, buckets, chat at $5; (2) D7/DEC-030 before any live run (no new data category); (3) admin-only document approval?; (4) data-mode label for current-data runs (`DELAYED`?).

**Safa:** (1) story by 22:00; for insurance: trigger scope, payout shape, waiting period, cut-off, policyholder, channel (unanswered fields print blank); (2) disclaimer wording; name no insurer by default; (3) B2B name without "risk raporu" or "sinyal" (SPK III-37.1 art. 45(2); legal reading [U]); (4) a real-fund term sheet in the live demo (localhost only; deck screenshots from the synthetic seed or the eight targets).

**Risks:**
- Debate: at equal compute it adds little; voting explains most gains (https://arxiv.org/abs/2310.01798, https://arxiv.org/abs/2508.17536, via the alternatives study, accessed 2026-10-10). Present it as an audit trail, never accuracy; report dispositions as development results.
- More validator failures on multi-step text: precompute demo runs.
- The AI trigger assessment read as a claims decision: deterministic trigger first, labelled.
- Real-fund PDF leaks: database only, `no-store`, gitignored.

**Sources:** DEC-028, DEC-029, the plan, `docs/notes/research-2026-10-10/*.md`, `docs/notes/product-direction.md`, `docs/handoff-v0.5/AGENTS.md`, both studies, the clone lines above.