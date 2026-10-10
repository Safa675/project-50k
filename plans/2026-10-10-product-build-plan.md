# BlackSwan build plan: B2B evidence data and API for Turkish funds and stocks

**Status: CONFIRMED by delegation** ([DEC-030](../docs/decisions/DEC-030-blackswan-working-agreements.md), 2026-10-10 about 14:30).
- Agents confirm the defaults in section 2 that serve the team's interest, and ask Mirza about problematic ones.
- D7, D9 and D1 are recorded in DEC-031. Mirza supplied the key; live decision/chat smoke passed. The
  closest-name identity and ten delegated exact-name checks are complete. Unknown publication times still
  prevent regulatory triggers. Budget-alert configuration and Safa's separate D7 answer remain open.
- The $25 budget is a target, not a hard cap. The product contains no placeholders (DEC-030).
- Codex continues from `plans/2026-10-10-codex-handoff-prompt.md`.
- **Current direction ([DEC-032](../docs/decisions/DEC-032-b2b-evidence-data-api.md)).** B2B evidence data and API
  access through an agent workflow for banks and financial institutions. Insurance is permanently deferred;
  retained insurance designs below are historical, not implementation tasks. The historical fund case is first,
  and Mirza requires real stock support in the demo. Current BIST 30 catalog/chart/evidence/API support is built;
  stock anomaly classification and stock AI remain unimplemented.
- **Alignment resumed.** Mirza resumed, selected current BIST 30, supplied 22 Figma designs and delegated all
  Git work. Independent frontend/backend/database work proceeds in parallel; fund protocols remain immutable.
- **Design access fixed.** All 22 Figma contexts/screenshots are read and mapped to ten base pages/states and
  twelve hover/context variants. Implementation is running at localhost:3070; typecheck, web build and all 14 browser tests pass.

- **Freezes:** features Sunday 2026-10-11 at 10:30; code at 13:00.
- **Implements:** [DEC-028](../docs/decisions/DEC-028-deploy-ready-ai-native-build.md) and
  [DEC-029](../docs/decisions/DEC-029-open-all-funds.md), with direction and stock scope updated by DEC-032.
- **Inputs:**
  - five read-only reviews in [docs/notes/research-2026-10-10/](../docs/notes/research-2026-10-10/);
  - two adversarial reviews of this plan, on integrity and feasibility, folded in below;
  - the TradingAgents study (section 7).
- **Open asks:** [team asks](../docs/notes/team-asks.md).

## At a glance

- **What we build.** One `docker compose up` starts PostgreSQL, a FastAPI API, a worker and a new Turkish Next.js
  app, all on localhost with real data for about 2,100 funds. The current research demo stays on port 3060 as the
  fallback.
- **Detectors.** Every score is computed deterministically: D1–D5 v2 on every fund, data-quality guards, and
  regulatory events confirmed by a human. Each figure is labelled a development result.
- **The LLM.**
  - An OpenAI model decides materiality, choosing only among options the server allows, from stored evidence
    packets. It never writes a number.
  - Every decision is append-only, and a human can override it.
  - Chat answers pass the same validator before anyone sees them.
- **Agent team.** TradingAgents-inspired, as a fixed pipeline in our own worker: server-written briefs, then a
  challenger, then a committee whose decision a human can override. No framework and no copied code. It is built
  only if the AI core is on time.
- **Story screens.** B2B evidence data and API access for banks and financial institutions, with the agent
  evidence/review workflow and the historical fund case. Insurance screens and documents are permanently deferred.
- **Stock requirement.** The real current BIST 30 data/catalog/chart/API slice is implemented with 30 stocks,
  870 daily closes and five corporate-action observations. Availability is capture time; price adjustment
  semantics and redistribution rights remain unreviewed. No stock classifier/AI claim.
- **Scope.** The work was about 30 hours against 14–16 available. The plan now moves a defined list to after the
  freeze (section 10) and builds the demo path first.

## 1. What exists at the freeze

On this machine, one `docker compose up` starts the following, with every host port on 127.0.0.1 and nothing deployed.

1. **PostgreSQL 18** with:
   - 1,755,010 stored daily price rows after the final refresh, preserving nulls;
   - names, categories and TEFAS status for about 2,133 funds;
   - 3,304 TEFAS snapshots;
   - 12,111 KAP document-index entries, with original report series retained;
   - 131 identity-confirmed SPK event versions; unknown publication time still prevents a trigger;
   - 30 BIST 30 instruments, 870 daily closes and five observed corporate-action records.
2. **The API:**
   - email/password sessions and roles;
   - fund, signal, decision and event endpoints;
   - validated chat;
   - OpenAPI docs, which double as the B2B API documentation.
3. **The worker,** with a PostgreSQL job queue for AI decisions. Imports and detectors run as command-line jobs.
4. **The web app** (Turkish, using the supplied Figma design system and exact local logo/assets):
   - fund list and fund pages, with chart, detector evidence and the SPK timeline;
   - a review queue of AI decisions with human override;
   - chat;
   - B2B evidence/feed/API screens;
   - real BIST 30 support, implemented separately from immutable fund protocols;
   - watchlists, notification preferences/read state, evidence feedback and contextual chat.

## 2. Decisions in this plan (recommended defaults; change any of them)

| # | Decision | Default |
|---|---|---|
| D1 | Where to build | A git worktree at `C:\Users\mirza\Desktop\Hackathon\project-50k-app` on branch `product/build`. Host bind mounts (the main checkout's `raw/` and the forward snapshot SQLite, both read-only) live in a gitignored `compose.override.yaml`, with an example committed. Main stays on `main` with registered files untouched. Main was safely advanced to `3b7bf4c` before Figma integration; Codex handles subsequent protected-path-checked pulls. K4 still decouples the live demo |
| D2 | Frontend | A new Next.js app in `web/` with the same pinned versions as `frontend/`. It copies only the chart and the Turkish formatters. `frontend/` stays the research app and fallback |
| D3 | Backend | A new package, `services/p50k/product/`, with psycopg 3 and plain SQL. Plain SQL migrations run through a small runner. It imports the providers and the frozen detectors read-only |
| D4 | Ports | web 127.0.0.1:3070, API 127.0.0.1:8770, PostgreSQL 127.0.0.1:5433 (dev profile). The smoke test runs as its own compose project on 3071/8771 |
| D5 | Versions (resolved 2026-10-10, locked at setup) | `postgres:18.6` (volume at `/var/lib/postgresql`), `python:3.13-slim`, `node:24-slim`, `openai` 3.28.0, `psycopg[binary,pool]` 3.3.x, `argon2-cffi` 25.1.0 |
| D6 | LLM models | `gpt-6.1-sol` for decisions and chat; `gpt-6-luna` for cheap steps; fallback `gpt-5.4-nano`. IDs come from env and are checked by a smoke test. Responses API with `store: false` (not stored for retrieval; OpenAI keeps abuse logs for up to 30 days) |
| D7 | What real data goes to OpenAI | **Derived evidence only**, enforced by one egress module with a field allowlist and a test. Raw prices, TEFAS size/units/investors, KAP text and personal data are excluded. The chat panel warns users. **D7 is approved in DEC-031.** The supplied key passed live model/decision/chat smoke; on-demand AI is live under existing caps. Safa's separate answer remains recorded as pending |
| D8 | Detectors for all funds | **D1–D5 v2.** Peers come from all funds. The single category source for every fund is `fonTurAciklama` from the saved 2026-10-06 fund list, a stated change from the frozen run.<br>The v2 protocol is committed alone before any all-fund percentile is computed. It lists what was already seen: the frozen results, the 100-fund thresholds, the 17 September order and its 131 funds.<br>It runs once on Saturday and is never recalibrated on overnight data. Labels read "geliştirme sonucu; eşikler olaydan sonra belirlendi". If M2 slips by more than an hour, drop v2: uncovered categories then abstain with "kategori için kalibre eşik yok" |
| D9 | Overnight collection | Restartable runners built in T2.6 and dry-run on THF and TP2 first. They run on the host from the worktree's environment. Output goes under `~/.local/share/project-50k/overnight/2026-10-10/` only.<br>Jobs: TEFAS 12-month prices, snapshots and profiles for all funds; SPK bulletin PDFs for 2024–2026 (download only). Pacing 1.5 s / 6 s; each job stops after 3 consecutive failures |
| D10 | Real-data pages | Behind login. A public landing page shows no real data |
| D11 | AI decision types | Materiality only: `MATERIAL`, `NOT_MATERIAL`, `DATA_ISSUE` or `INSUFFICIENT_EVIDENCE`, with the server computing the allowed options. Insurance assessments are permanently deferred (DEC-032) |
| D12 | Agent team | A fixed pipeline in our worker, TradingAgents-inspired, with no framework and no copied code (section 7). Before the freeze it is a challenger plus a committee, run only if M3 lands by 01:00. Recorded in DEC-030 together with D7 |
| D13 | Data-mode labels | `DELAYED` for current published TEFAS data, with its as-of date; `HISTORICAL_REPLAY` only for replays with a cutoff. A replay packet never carries later TEFAS status (the 2026-10-06 status would reveal the halt) |
| D14 | Review authority | Analysts review AI decisions. Insurer-review print views and their document approval are permanently deferred (DEC-032) |
| D15 | Product and demo scope | Turkish funds and stocks; historical fund case first, real stock support required in the hackathon demo (DEC-032). Current BIST 30 source-data support is implemented through isolated modules and a versioned data-only protocol; stock classification/AI remains separate |

## 3. Architecture and safety rails

```
Browser (tr) ─127.0.0.1:3070─► [web] Next.js standalone (HOSTNAME=0.0.0.0, compress off)
                                 └─ route handlers /api/p/* forward Cookie, Origin, X-CSRF-Token, Set-Cookie; SSE pass-through
                                      ▼
                                 [api] FastAPI (:8000 → 127.0.0.1:8770) ──► OpenAI via the egress module
[migrate] SQL runner (owner role) ─► [db] PostgreSQL 18 ◄── psycopg pool (role p50k_app) ── [worker] ai_decide jobs
CLI jobs (docker compose run --rm worker …): import-archive, run-detectors, import-overnight
```

**Database.**
- Schemas: `ref`, `obs`, `det`, `ai`, `auth`, `b2b` and `ops`.
- Provenance on every observation; `development_result=true` on every detector result.
- Importers COPY into staging tables, then `INSERT … ON CONFLICT DO NOTHING`.
- SQLite inputs are opened as `file:…?mode=ro&immutable=1`.

**AI records.**
- **Permissions.** The migration role owns every table. The app role `p50k_app` has only INSERT and SELECT on
  `ai.packets`, `ai.decisions`, `ai.decision_reviews`, `det.evidence_items` and `ops.audit_log`, and a BEFORE UPDATE OR
  DELETE trigger blocks changes.
- **Decision rows.** They store `model_id`, `prompt_version`, `schema_version`, `ai_mode`, `packet_sha256`, `call_id`
  and `created_at`, all NOT NULL.
- **Effective value.** It is the latest human review for the current packet. A changed packet sends the fund back to
  the queue with "önceki kanıta göre insan kararı". A rejection gives `UNDECIDED`.
- **Mock runs.** They use a separate `p50k_dev` database, and the real-data database rejects mock rows.

**Secrets.**
- `.dockerignore` denies everything and re-allows only `pyproject.toml`, `uv.lock`, `services/`,
  `research/…/price_detectors/detectors.py`, `db/` and `web/`. It also excludes `.env*` (except `.env.example`),
  `secrets/`, `backups/`, `.git` and `**/*.sqlite3`.
- Images use `ENV PYTHONPATH=/app/services` and install `--extra api --extra research --extra product`.
- Secrets are file sources under the gitignored `secrets/`. The OpenAI key and the pepper are mounted only into `api`
  and `worker`. `env_file` is optional; there are no secret build arguments, and secrets are held as `SecretStr`.
- Logs redact credentials and never log login or chat bodies. Jobs store only the error class.
- A hook blocks agents from reading `.env*` or `secrets/`. Agents use `docker compose config --no-interpolate`.

**Login.**
- argon2id passwords and server-side sessions.
- A CSRF header plus an Origin check; requests without an Origin are rejected.
- Host allowlists on both the API and Next.
- Default-deny routing with a public allowlist, and a route-walk test.
- Throttling per email and IP, trusting `X-Forwarded-For` only from `web`.
- Roles: viewer, analyst, admin. Seed passwords are generated at run time.

**Data safety.**
- "Clean start" means `docker compose down`, never `-v`.
- `pg_dump -Fc` runs at Sunday 11:00, with a restore rehearsed into a separate project before 12:00.
- The smoke test uses its own project and volume and is torn down with `-v`. The demo volume never receives synthetic
  rows.

## 4. Data plan

**Saturday, offline, by M1.**
- **Funds.** Names, categories (`fonTurAciklama`) and TEFAS status for 2,133 funds, from the saved 2026-10-06 fund
  list.
- **Prices.** 1,673,412 values; zero or null stays missing.
- **Snapshots.** 1,073 forward rows plus 100 local rows.
- **KAP.** The 101 parsed monthly series, as an index.
- **SPK order 2026/61.** Its 131 funds, mapped by rule. Mirza checks the closest-name match and 10 exact matches
  (T1.7a). Only then are the events `CONFIRMED`.

**Overnight:** the D9 jobs (prices, snapshots, profiles, SPK PDFs).

**Sunday by 08:30:**
1. `import-overnight`.
2. One detector rerun on the refreshed prices, using the fixed v2 thresholds.
3. One live AI pass (section 6).

**Moved after the freeze:** the SPK web-service and KAP-event spikes, SPK text extraction, SPK 2005–2023, KAP report
lists for more funds. The Windows forward-snapshot task keeps running and first fires on Monday at 21:00.

## 5. Detectors

| Detector | Coverage before the freeze |
|---|---|
| D1/D2 excess return (≈ AN-FND-001), D3 autocorrelation, D4 peer correlation (v2) | All funds with enough history, run as a CLI on Saturday |
| D5 fund age | An attribute, not an anomaly |
| AN-FND-005 regulatory event | The 17 September order with human entity verification; descriptive institutional evidence, not an insurance assessment |
| AN-DQ-001/002 stale or placeholder data | All funds. A stopped price is a data-quality event, not a liquidation trigger |
| AN-FND-002/004 flow and allocation (monthly, about 100 funds) and K1 | **After the freeze** |

Each run records the version, parameters and input watermark. For each fund it stores `TRIGGERED`, `NOT_TRIGGERED` or
`ABSTAINED`, with reasons and evidence IDs. A per-fund overview shows which detectors cover the fund.

## 6. AI layer (DEC-028)

### One validator for all model text

Decisions, chat answers and any summaries are validated before anything is shown.

1. **Schema.** The output matches its strict schema.
2. **Citations.** Cited IDs must exist in the packet or in the thread's tool results.
3. **Numbers.** Numbers, dates and identifiers appear only as placeholders. Each placeholder renders as a labelled
   value with its threshold and a magnitude band computed on the server. Validation fails on:
   - any digit outside a placeholder;
   - a Turkish number word used as a numeral, that is, before a unit, time or magnitude noun (gün, ay, yıl, kat,
     puan, yüzde, bin, milyon). "Bir" as the article stays valid;
   - intensity adjectives ("olağanüstü", "çok üzerinde").
4. **Wording.**
   - Phrase lists cover allegation, advice, prediction or safety, SPK motives, performance claims and coverage
     vocabulary.
   - İ, I, ı and i are folded together before matching.
   - The Turkish test corpus includes valid sentences with many "bir" and invalid sentences in capitals.
5. **Failure.** One retry, then `INVALID`. The text reads "Yapay zekâ önerisi üretilemedi; insan incelemesi gerekli",
   and the fund goes to the queue. "Kanıt yetersiz" is shown only when the server finds the evidence insufficient,
   never for a model failure.
6. **Chat.** Tool-progress events stream; the answer is sent only after validation. Evidence chips appear only for IDs
   the tools returned.

### Decisions

1. **Allowed options.** The server computes them from the packet:
   - no covering detector and no event: `INSUFFICIENT_EVIDENCE`, with no model call;
   - `NOT_MATERIAL` needs a covering detector;
   - a confirmed in-scope SPK event removes `NOT_MATERIAL` and `DATA_ISSUE`;
   - `MATERIAL` and `DATA_ISSUE` must cite a triggered signal or a data-quality event;
   - every decision cites at least one ID.
2. **Review.** Analysts accept, override (with a required reason) or reject.
   - The effective value is the latest human review on any decision for the current packet, single-call or team.
   - A later AI decision never displaces it; it is shown as "farklı yapay zekâ önerisi".
   - Each decision field gets its own review.
3. **Failure.** It fails closed to `UNDECIDED`.
4. **Client settings.**
   - The OpenAI client runs with `max_retries=0` and `timeout=60`. The runner does the retries and reserves budget for
     each one.
   - Every step sets `max_output_tokens`, and its reservation is priced from that.
   - Reservations are rows with `expires_at`. A timeout or expiry settles at the worst case.
   - After an `INVALID`, the same packet and prompt are blocked from rerunning.

### Schedule and budget

- **Until the overnight data is imported (T5.1):** mock mode, plus at most 20 live decisions for prompt tuning (at most
  $1).
- **By Sunday 08:30:** one live pass of at most 300 decisions, run after the final detector run with 6 concurrent jobs.
- **Demo overrides:** made after that pass.
- **If D9 is declined:** the pass runs right after M2.
- **Gate.** The 08:30 pass runs only if the 20 tuning calls show an acceptable `INVALID` rate. The pass is sized from
  the measured p90 cost, with the demo funds first.
- **Caps:**
  - $20 of our own, split into buckets:
    - tuning, $1;
    - the morning single-call pass, $5;
    - the agent team, $3 (batch $1.5, on demand $1.5);
    - chat, $5;
    - the Sunday 11:00–13:00 reserve, $5;
    - unallocated, $1.
  - Each call reserves its worst-case cost first.
  - Chat is limited to 30 turns per user per day.
  - "Yeniden değerlendir" is for analysts only, and deduplicated.
- **Cache key:** mode, model, effort, prompt version, schema version and packet hash. `INVALID` output is never cached.

### Chat

- **Tools at the freeze:** `search_funds`, `get_fund_profile`, `get_signals` and `get_decision`. Each goes through the
  egress module and returns at most 4 KB.
- **Limits per turn:** 3 model calls, 6 tool calls, 45 s.
- **Threads:** scoped to their owner.

## 7. Agent team (TradingAgents-inspired)

The study, design and critique are in
[docs/notes/research-2026-10-10/](../docs/notes/research-2026-10-10/) (`agents-*.md`).

### What TradingAgents is

- **Basics.** v0.6.0 (2026-10-03), Apache-2.0, LangGraph/LangChain.
- **Flow.**
  1. Four analysts (market, news, fundamentals, sentiment) run in parallel.
  2. Bull and bear researchers debate, and a research manager decides.
  3. A trader proposes a trade.
  4. Aggressive, conservative and neutral risk analysts debate.
  5. A portfolio manager outputs a Buy…Sell rating.
- **Calls.** At least 15 LLM calls per run, typically 20–25.
- **Data.** US and crypto only: yfinance, SEC, Reddit, StockTwits, news.
- **Findings for us:**
  - It leaves OpenAI's `store` unset, so OpenAI keeps responses for 30 days by default.
  - Its structured outputs use a forced tool call, not a strict schema, with a free-text regex fallback.
- **Verdict.** Use the pattern, not the code. Its output is investment advice, it has no TEFAS, KAP or SPK support,
  it would add a framework dependency, and its call count does not fit the budget.

### Our design (the critique's cut form)

- **A fixed pipeline in our own worker.** No framework, no model routing and no tools. It runs on the same step runner
  as the single-call decision, and every rule in section 6 applies: allowed options, validator, egress, reservations
  and override.
- **No code is copied.** We say "TradingAgents-inspired" and cite arXiv 2412.20138. DEC-030 records this.
- **Before the freeze** (only if M3 lands by 01:00; otherwise the single call stays):
  1. **Server briefs.** The server writes the analyst briefs deterministically, one per evidence slice: price and
     peers, regulatory events, data quality.
  2. **The challenger (C), cheap model.** It may argue only the benign alternatives the server allows for that
     packet:
     - `SHORT_HISTORY` needs a D5 age bound;
     - `DATA_QUALITY` needs a data-quality event that a halt does not explain;
     - `NATURALLY_SMOOTH_FUND_TYPE` needs a fixed category list;
     - `MARKET_WIDE_MOVE` needs a fixed same-date share of category triggers;
     - `OTHER` can never support `NOT_MATERIAL`.
  3. **The committee (K), strong model at low effort.**
     - It receives the server slice: every item ID and its state.
     - It answers each allowed alternative and issues the decision from the allowed options.
     - A confirmed in-scope SPK event removes `NOT_MATERIAL` and `DATA_ISSUE`, and alternatives cannot target it.
  4. **Human review.** Only K's decision is reviewed and overridable. The challenger's text shows as "ara çıktı" and
     never goes into an export.
  5. **The `/ekip/[run]` page.** It shows the step timeline, the transcript with evidence chips, and the decision
     panel.
- **Cost and timing.**
  - About $0.035–0.055 per run; the committee dominates.
  - Batch: at most 25 funds by a fixed rule (a confirmed event, or 2 or more triggered D1–D4 signals), after the final
    detector run, by 08:30.
  - On demand: analysts only, 10 runs per user per day.
  - Never across all funds (about $95).
  - The demo uses stored runs. A live moment runs C → K only, with priority over batch jobs, and falls back to the
    stored run after 60 s.
- **Historical insurance design — permanently deferred by DEC-032; no implementation tasks below.**
  - Title: "Tetikleyici Endeksi ve Kanıt Spesifikasyonu (sigortacı incelemesi için taslak)".
  - Contents: the trigger definition, the confirmed event evidence, and K's decision with its human review.
  - Cover, premium, payment and eligibility are covered by one fixed sentence: they belong to a licensed insurer, and
    no agreement with an insurer or channel exists. There are no blank premium or payout rows. Safa's answers appear
    as questions, not values.
  - Statuses: "İNCELEME BEKLİYOR" and "İÇ İNCELEMEDEN GEÇTİ".
  - Approval binds to `data_sha256`, `decision_id`, `review_id` and `packet_sha256`. A change after approval returns
    409.
  - The AI trigger assessment appears only in the app, with its override.
  - Coverage vocabulary is banned in all LLM text: teminat, kapsam, tazminat, hasar, prim, poliçe, sigortalı,
    sigorta ettiren, ödenecek, hak kazanır, muafiyet.
- **After the freeze:** LLM analysts and B2B report PDFs. The earlier policy writer, insurance PDF and approval
  re-rendering proposals are retained as history and permanently deferred by DEC-032.
- **What the debate is worth.** Research says debate adds little at equal compute. We present it as an audit trail
  (alternatives considered and answered), never as accuracy.

## 8. Story layer (Sunday by 10:30)

**Active: B2B evidence data and API (DEC-032).**
- **Buyer and offer.** Banks and financial institutions; evidence data and API access through an agent workflow.
  Pricing, demand and partnerships are hypotheses, not demonstrated facts.
- **Historical fund case.** Show stored observations, deterministic evidence, the agent assessment and human
  override. Do not imply prediction, fraud findings, validated accuracy or advance warning.
- **Feed.** An evidence feed with CSV export. Every row is labelled `development_result`, `origin`,
  `rights_status=UNREVIEWED`, `decided_by` and its review state.
- **CSV header:** "Geliştirme sonucu; veri hakları incelenmedi; yatırım tavsiyesi değildir".
- **Docs.** The protected OpenAPI page serves as the API documentation; API keys come after the freeze. The
  commercial offer does not authorize external resale or deployment; real data remains on localhost.
- **Stock support.** Required in the hackathon demo, with real source-backed data and separate versioned evidence
  rules. Current BIST 30 catalog/chart/evidence/API support is implemented; stock anomaly classification/AI is not.

**Historical A. Insurance — permanently deferred, not a demo path.**

The earlier proposal is retained below only as a record; none of its screens, assessments or documents is an
active task.
- **Trigger check.** Labelled `HISTORICAL_REPLAY`, it uses only observations available before the cutoff. Eligibility
  is contract terms only, and no detector tiers are shown.
- **AI assessment.** Beside the deterministic `trigger_fired`, labelled "bilgi amaçlı; hasar kararı sigortacıya
  aittir".
- **The insurer-review print view** (section 7).
- **After the freeze:** an LLM policy writer and PDFs.
- **Pitch line:** "Designed so that a licensed insurer issues the policy and a bank distributes it; we would supply
  the trigger and evidence. No insurer or bank partnership exists."

**Historical B. Earlier B2B descriptive-data proposal — refined by the active direction above.**
- **Feed.** An anomaly feed with CSV export. Every row is labelled `development_result`, `origin`,
  `rights_status=UNREVIEWED`, `decided_by` and its review state.
- **CSV header:** "Geliştirme sonucu; veri hakları incelenmedi; yatırım tavsiyesi değildir".
- **Docs.** The OpenAPI page serves as the API documentation; API keys come after the freeze.

## 9. Verification

- **Python.**
  - Unit tests with synthetic data.
  - Login tests, including the 401 route walk.
  - The validator corpus and the egress allowlist test.
  - Database tests: an UPDATE as `p50k_app` fails; an override survives a rerun; a packet change sends the fund back
    to the queue.
  - Queue tests for `ai_decide`.
  - The golden test reads `raw/` through `P50K_RAW_DIR` and reports itself skipped without it.
- **Linux baseline at M1.** In WSL2, run
  `git clone --branch product/build /mnt/c/Users/mirza/Desktop/Hackathon/project-50k ~/p50k-linux`, then the root and
  frozen suites. Save the failing test names. At the freeze, no new name may appear.
- **Proxy check before M1,** through 127.0.0.1:3070:
  - a dummy login sets the cookie;
  - a CSRF POST passes for both `127.0.0.1` and `localhost`;
  - `curl -N` receives the 10 events of a dummy SSE endpoint one at a time.
- **Web.** Typecheck, Vitest, and a Playwright smoke test in the separate `p50k-smoke` project.
- **Before every commit:** the leak scan with `P50K_RAW_DIR` pointing at the main checkout's `raw/`. Exit 1 or 2 blocks
  the commit.
- **At the freeze:**
  - scan image layers, inspect output and logs for the key prefix;
  - check that no mock rows exist;
  - deck screenshots come from the synthetic seed or show only the eight targets.

## 10. Timeline and scope

| Phase | By | Work (owner C unless noted) | Done when |
|---|---|---|---|
| 0 Confirm | Sat 13:45 | T0.1 confirm (M); T0.3 D7 and D9 (M) | Plan confirmed |
| 1 Foundations | Sat 17:30 | Pre-pull the four pinned images. T1.1 worktree, ignores, secrets folder, read-blocking hook; then T0.2 key (M). T1.3 lock. T1.4 migrations, roles, triggers. T1.2 compose plus the proxy check. T1.5 settings and logs. T1.7 `import-archive` CLI. T1.7a mapping check (M, by 17:00). Linux baseline | Archive row counts match |
| 2 Detectors and API | Sat 20:30 | T2.1 v2 protocol committed alone; T2.2 `run-detectors` CLI for D1–D5 v2, data quality and events; T2.4 API (funds, detail, signals, events, OpenAPI); T2.6 overnight runners, dry-run, then started. T4.0 machine prep (M) | Signals for every fund via the API; overnight jobs running |
| 3 AI core and screens | Sun 01:00 | T1.6 login; T3.1 OpenAI wrapper with caps and modes; T3.2 egress; T3.3 validator; T3.4 decision engine (materiality); T3.5 review queue and override; T1.8 queue for `ai_decide`; T3.6 web shell, login, fund list, fund page | A mock decision flows from packet to queue to override in the UI |
| Overnight | | D9 jobs; machine on; a 07:00 log check (M) | |
| 5 Live, chat and B2B story | Sun 10:30 (feature freeze) | T5.1 import overnight data, rerun detectors, live AI pass by 08:30; T5.2 chat with 4 tools; T5.3 agent team (challenger, committee, `/ekip` page) if M3 landed by 01:00; T5.4 B2B evidence/API screens; T5.5 supplied Figma implementation and Turkish/accessibility pass; T5.6 real stock data support through isolated modules | Fund case and required stock path work end to end |
| 6 Freeze | Sun 13:00 | 10:30–11:00 fixes only; 11:00 `pg_dump` and restore rehearsal; smoke test; leak and secret scans; demo seed and overrides (T6.2); cold-boot rehearsal; T6.3 freeze merge in the worktree (`freeze-merge` from `origin/main`, `--no-ff`, no registered paths touched, push after Mirza's OK, tag); T6.4 demo script with Safa and Barış | Tagged `event-freeze` |

**Moved after the freeze now:**
- the SPK web-service and KAP-event spikes;
- AN-FND-002/004 and K1;
- SPK text extraction, and SPK 2005–2023;
- KAP report-list expansion beyond the authorized completed cohort;
- B2B API keys (the OpenAPI page stands in);
- the partner panel;
- summaries for all funds;
- the CI compose job and the scheduler (jobs run from the CLI).

**Never cut:**
- real data and the detectors;
- AI decisions with allowed options and override;
- the validator and the fail-closed path. If the validator is not ready by Phase 5, chat runs with AI off;
- login.

## 11. Todo list

Owner: **C** = Claude, **M** = Mirza, **S** = Safa, **B** = Barış, **T** = team. Order as in section 10.

### Phase 0

- [x] T0.1 (M) Confirm the plan: delegated by DEC-030; D1 confirmed during takeover
- [x] T0.3 (M) Answer D7 and D9 (DEC-031); Safa's separate D7 answer remains open
- [ ] T0.4 (M) Relay the asks
- [x] T0.5 (M, S, T) Story/buyer/revenue direction: Mirza confirmed B2B evidence data/API for banks and financial institutions (DEC-032); commercial validation still open
- [x] T0.7 (M) Stock timing/universe: Mirza requires stocks in the demo and selected current BIST 30; data-only slice implemented
- [x] T0.6 (B) Supplied Figma variables, typography, logo, assets and component states received; all 22 contexts/screenshots accessible

### Phase 1

- [x] Pre-pull `postgres:18.6`, `python:3.13-slim`, `node:24-slim` and uv 0.12.17
- [x] T1.1 Worktree; deny-all `.dockerignore`; ignores for `secrets/`, `backups/`, test output, `*.sqlite3`, `*.dump`
  and `compose.override.yaml`; the read-blocking hook
- [x] T0.2 (M) Key supplied in the approved ignored runtime location; live model/decision/chat smoke passed
  - Budget-alert configuration remains open. DEC-030 makes $25 a target, with the internal $20 buckets retained.
- [x] T1.3 The `product` extra, verified on PyPI and locked
- [x] T1.4 SQL migrations: seven schemas, roles, append-only triggers; the runner
- [x] T1.2 Dockerfiles, `compose.yaml` and the override example; the isolated proxy check
- [x] T1.5 Settings, redacting logs, health endpoints
- [x] T1.7 `import-archive` CLI (staging plus ON CONFLICT), with verified counts and zero-insert rerun
- [x] T1.7a Closest identity confirmed; ten delegated exact-name checks pass; unknown publication still cannot trigger
- [x] The Linux baseline in WSL2: 663 + 9 + 88 tests pass at `19989c5`, zero skips

### Phase 2

- [x] T2.1 The D1–D5 v2 protocol, committed alone at `e9b7ba7`
- [x] T2.2 `run-detectors`: 17,064 results for 2,133 funds; immutable calibration, evidence and completed runs
- [x] T2.4 API: funds, detail, signals, events, OpenAPI; protected until Phase 3 auth
- [x] T2.6 Restartable downloads completed with explicit gaps: 2,129 price files/four failures; 2,134 profile files/one failure/five empty responses; 1,071-fund KAP cohort completed with reuse; 194 discovered SPK PDFs saved
- [ ] T4.0 (M) AC power, sleep set to Never, Windows Update paused until Monday, Docker Desktop starting at login

### Phase 3

- [x] T1.6 Login, CSRF, expiry/revocation/throttling and PostgreSQL tests
- [x] T3.1 Wrapper/caps/reservations/modes and paid model/account/decision/chat smoke pass; full tuning remains a batch gate
- [x] T3.2 Typed egress and allowlist test
- [x] T3.3 Validator/Turkish corpus; live quality measurement remains gated
- [x] T3.4 Immutable packets/options/cache/INVALID block; synthetic flow tested
- [x] T3.5 Review queue, original/human values/reason, override survives rerun
- [x] T1.8 Leased/deduplicated queue; concurrent claim/lease recovery tests
- [x] T3.6 Login, protected fund pages/evidence/review; isolated browser flow passes

### Overnight

- [ ] (M) Check the logs at 07:00

### Phase 5 (feature freeze at 10:30)

- [ ] T5.1 Final available download import and deterministic rerun completed (1,755,010 prices; 17,064 results; original calibration). Measured tuning/gated live pass still due by 08:30
- [x] T5.2 Chat with four bounded read-only tools, owner threads, budgets/daily limits and cited source links. DEC-033 adds plain explanations and real validated-paragraph streaming; chat v4 passed three live questions and a before-completion browser test. Wider quality remains a separate gate
- [ ] T5.3 The agent team (if M3 landed by 01:00):
  - the step runner;
  - server briefs;
  - the challenger with server-allowed alternatives;
  - the committee;
  - batch runs (at most 25 funds by the fixed rule);
  - the `/ekip/[run]` page
- [ ] T5.4 B2B workflow overview, historical fund evidence and protected OpenAPI docs implemented; final demo/feed review remains. Challenger/committee is separate unfinished work; no insurance screens
- [x] T5.5 All 22 Figma designs implemented; DEC-033 adds nontechnical results/source labels, understandable method disclosures, last-known dated prices and genuine asset logos. Final typecheck/build, 21 web unit tests and 16 browser tests pass. The populated KAP marker remains an explicit browser-coverage gap
- [x] T5.6 Real current BIST 30 source-data catalog/chart/API, capture timestamps and corporate-action records; data-only protocol committed before ingestion. No stock anomaly classifier/AI; fund protocols preserved

### Phase 6

- [ ] T6.1 Smoke test (separate project); key and mock-row scans; the Linux suites with no new failing names
- [ ] T6.2 Demo seed with generated passwords; demo overrides after the live pass
- [ ] T6.3 Early backup/restore rehearsal verified 34 tables/eight migrations. Repeat at Sunday 11:00 after final changes, including migrations 009/010; then freeze merge/tag
- [ ] T6.4 Demo script with Safa and Barış; cold-boot rehearsal, including the fallback demo on 3060

### Carried over and after the freeze (kept, not dropped)

- [ ] K1 Per-date estimated flow (AN-FND-002 with DEC-026's (M-2, M-1) rule)
- [ ] K2 Windows research-suite fixes (the product suites run in Linux)
- [ ] K3 The Windows forward-snapshot task (first run Monday 21:00)
- [ ] K4 Decouple the research demo from the main checkout, then pull the merged `main` into the main checkout
- [ ] K5 The do-not-claim list applies to the product and the pitch
- [ ] K6 After the event:
  - SPK history from 2005 (a base-rate study);
  - the spikes and KAP collection;
  - parsers for more KAP layouts;
  - B2B keys;
  - the partner panel;
  - a data-rights review

## 12. Asks (also in `docs/notes/team-asks.md`)

- **Mirza:** T0.1/T0.2 key/T0.3/T1.7a closed. Remaining: budget alerts, relay open business asks, T4.0 machine preparation and the 07:00 check. Routine Git work is delegated to Codex.
- **Safa:**
  1. Detailed commercial plan, first institutional workflow, pilot and pricing validation. B2B story, buyer class
     and evidence-data/API revenue direction are already confirmed by DEC-032.
  2. Descriptive B2B copy and disclaimers; retain the current integrity labels and avoid advice wording.
  3. Which institutions may be named, with no implied partnership; default to naming none.
  4. His separate D7 answer.
  5. His data sources and their terms; optionally, his full 2026-10-06 snapshot, shared privately.
  6. Capital-markets and commercial data-rights opinions before contracts or external redistribution. Insurance
     questions and the insurer-review print view are permanently deferred.
  7. The Bilun primitives question.
- **Barış:** designs, tokens, logo and public landing direction received through Mirza's 22 Figma links.
  Review final design adaptation if needed; deck screenshots must still use synthetic data or the eight targets.
- **Team:** the product name and the pitch wording within the do-not-claim list.

## 13. Risks

| Risk | Mitigation |
|---|---|
| Not enough time | The after-freeze list, phase order with the data import first, the feature freeze at 10:30 |
| Breaking the live demo | Worktree; separate ports; the main checkout untouched; freeze merge done in the worktree |
| Data egress to OpenAI | DEC-031 derived-only approval; enforced egress allowlist, bounded tools and `store: false` |
| Overspending | $25 target (DEC-030), internal $20 buckets, reserved worst-case call cost, Sunday reserve and per-user limits |
| Invented numbers, advice or claims | One validator, allowed options, human override |
| Losing the database | Never `down -v`; correct volume path; backup and restore rehearsal at 11:00 |
| The overnight machine restarts | T4.0 preparation; restartable runners; the archive data still works |
| Proxy or streaming problems | Proxy and SSE check before M1 |
| Over-claiming in the pitch | Development-result labels; v2 "thresholds fixed after the event"; the reworded pitch line |
| Regulatory exposure | Descriptive evidence only; no assumed partnership or resale rights; legal/data-rights opinions before contracts |

Stock slice boundary: current BIST30 data/catalog/chart/corporate-record API is
implemented; adjustment semantics and redistribution rights are unreviewed.
Stock anomaly classification/AI is separate work. T5.4 B2B workflow overview
implemented with actual counts; challenger/committee remains unfinished.
The 22-frame Figma implementation is tracked in `docs/notes/figma-implementation-2026-10-10.md`;
tool access is fixed and implementation is running locally with passing integrated web checks.
