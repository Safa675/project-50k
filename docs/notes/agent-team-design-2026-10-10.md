# Agent team and Reporter dock: build contract (DEC-035)

Three implementers work in parallel on separate files and build against this contract. Change it only by agreement
with the integrator, who is Claude in the main session.

## 1. Ownership

| Owner | Files |
|---|---|
| **A, integration backend** | Existing date-scope files: `analysis_context.py`, `analysis_jobs.py`, `context_routes.py`, `workflow.py`, `workflow_routes.py`, `routes.py`, `queries.py`, `watchlists.py`, `decisions.py`, `decision_routes.py`, `stock_routes.py`, `evidence_routes.py` and their tests |
| **B, agent-team backend** | New package `services/p50k/product/agents/`; one new migration; `chat.py`, `chat_routes.py`, `chat_tools.py`; the route registration lines in `app.py`; worker wiring in `worker.py`/`ai_worker.py`; tests `tests/unit/test_product_agents*.py` plus their chat tests |
| **C, web** | Everything under `web/`, apart from nothing; it may change any web file |

Do not edit another owner's files. If a change is needed in one, write it into your final report.

**Never edit:**
- `services/p50k/product/detector_pipeline.py` and `detector_math.py`;
- registered and frozen paths, protocols and `raw/`;
- `docs/handoff-v0.5/`;
- migration files that are already applied (001–012).

## 2. Data (B; next free migration number)

The migration tests write synthetic files numbered 013. Choose a number that keeps those tests valid; renaming the
test's synthetic numbers (for example to 099) is allowed.

- **`agents.cases`:**
  - `case_id` uuid PK, `analysis_scope_key` (same check as chat), `fund_code` → `ref.funds`;
  - `opened_by` (`sentinel`|`user`), `requested_by` uuid NULL, `priority` int, `status`
    (`open`|`investigating`|`reported`|`closed`);
  - `detector_run_id`, `packet_sha256` NULL, `decision_id` NULL, `title_tr`, `opened_at`, `closed_at`.
  - Unique: one non-closed case per (scope, fund).
- **`agents.tasks`:**
  - `task_id`, `case_id`;
  - `role` (`sentinel`|`hypothesizer`|`skeptic`|`verifier`|`reporter`);
  - `status` (`queued`|`running`|`done`|`failed`|`waiting_budget`|`skipped`);
  - `priority`, `source` (`system`|`user`), `requested_by`, `depends_on` uuid[], `title_tr`;
  - `not_before`, `created_at`, `started_at`, `finished_at`, `lease_owner`, `lease_until`, `attempts`;
  - `call_id` NULL, `cost_usd` numeric NULL, `error_class` NULL.
- **`agents.messages`** (append-only; a BEFORE UPDATE OR DELETE trigger raises an error; the `p50k_app` role gets
  INSERT/SELECT only):
  - `message_id`, `case_id`, `task_id`, `from_role`, `to_role` (role|`team`|`human`);
  - `kind` (`case_opened`|`hypothesis`|`counter`|`test_plan`|`test_result`|`verification`|`report`|`handoff`|`note`);
  - `body_tr` (validated and rendered; never raw model text), `payload` jsonb (structured output, evidence IDs);
  - `model_id` NULL, `prompt_version` NULL, `created_at`.
- **`agents.sentinel_scans`:** `scan_id`, `analysis_scope_key`, `detector_run_id`, `funds_scanned`, `cases_opened`,
  `started_at`, `finished_at`.
- **Budget:** a daily bucket `agents:YYYY-MM-DD` (Istanbul date) created on demand with `cap_usd=3.00`, using the
  existing `ai_client.reserve`/`settle`. Before each reservation, check that the total across all buckets stays under
  `P50K_AI_TOTAL_TARGET_USD` (default 25). Above it, stop with status `waiting_budget` and the reason "toplam hedef".

## 3. Orchestration (B, in the worker loop)

- **The Nöbetçi tick** runs every 60 s and on any date-context change. For the default scope (the
  `P50K_ANALYSIS_DATE` selection) and any scope with user activity in the last hour:
  - it reads the latest closed detector run for that exact scope (never another day's run);
  - it opens or refreshes cases for funds with `TRIGGERED` evidence, regulatory events first, then by the number of
    triggered detectors;
  - it records each scan;
  - it uses no LLM.
- **Each case** produces these tasks:
  1. `hypothesizer` and `skeptic` (parallel, cheap model);
  2. `verifier` (depends on both);
  3. `reporter` (depends on the verifier).
- **The scheduler** claims the highest-priority ready task (dependencies done, `not_before` passed) with
  `FOR UPDATE SKIP LOCKED` and a lease.
  - Background pacing: at most one new case starts every 5 minutes (env).
  - User-sourced tasks have priority 100 and no pacing gap.
- **Hipotezci** returns up to 3 hypotheses. Each has a type from a fixed menu (for example `peer_divergence`,
  `flow_change`, `allocation_shift`, `regulatory_action`, `data_issue`, `market_wide_move`), cited evidence IDs and
  Turkish text with placeholders.
- **Şüpheci** returns up to 3 counter-explanations and up to 3 refutation tests, chosen from a fixed menu of
  deterministic tests the Doğrulayıcı can run.
- **Doğrulayıcı** first runs the requested deterministic tests in code, so it costs nothing. Examples: peer comparison
  over a window, a category-wide move, data quality, a change in the KAP monthly series, a regulatory event check;
  each runs only with cutoff-respecting data. It stores the test results as messages with numbers in `payload`. Then
  it makes one strong-model call that rates each hypothesis and counter-explanation as `supported`, `refuted` or
  `undetermined`, with citations.
- **Raportör** makes one strong-model call that writes the report. It then files the decision proposal through the
  **existing** decision path (`decisions.py` functions, using the server-allowed options and the same packet), so the
  existing human review and override apply. The case becomes `reported`.
- **Every model output** goes through the existing `validator` (schema, citations, placeholders, wording). On failure:
  one retry, then the task becomes `failed`, the case gets a deterministic note "Bu adım doğrulanamadı; insan
  incelemesi gerekli", and no invalid text is stored or shown.
- **Egress** goes only through `egress.py` models (DEC-031). Historical scopes hide fund identity in model input.
  Models come from env (`P50K_AGENT_MODEL_FAST`, `P50K_AGENT_MODEL_STRONG`), defaulting to the configured ones.
  `store:false`, `max_retries=0` and a timeout are set.
- **Without AI** (`P50K_AI_MODE` `off`/`mock`), the deterministic parts still run and the AI tasks show "Yapay zekâ
  kapalı". Mock output appears only in `p50k_dev`.

## 4. API (B). All routes need a session; every POST needs CSRF; answers are JSON in Turkish

- **`GET /agents/team`** →
  `{scope, now, budget:{day,cap_usd,spent_usd,reserved_usd,state}, agents:[...], links:[...], counts:{...}}`.
  - Each agent: `role`, `name_tr`, `state` (`idle`|`working`|`waiting`|`waiting_budget`|`off`), `activity_tr`,
    `case_id`, `fund_code`, `fund_name`, `since`.
  - Each link (the last 20 interactions): `from`, `to`, `kind`, `at`, `case_id`.
  - Counts: `open_cases`, `queued`, `running`, `done_today`.
- **`GET /agents/queue?limit=30`** →
  `{items:[{task_id, case_id, fund_code, fund_name, role, title_tr, status, priority, source, created_at, started_at, finished_at}]}`.
- **`GET /agents/cases/{case_id}`** → the case, its tasks and its message timeline (the workspace).
- **`GET /agents/workspace/{role}?limit=20`** → that role's current and recent tasks and messages.
- **`POST /agents/page-visit`** `{path, fund_code|null}` → `{note_tr, warning_tr|null, suggestions:[{label_tr,
  prompt_tr}], case:{case_id,status}|null}`.
  - Deterministic, from stored evidence; no LLM.
  - It raises an open case's priority for that fund (deduplicated, rate-limited).
- **`POST /agents/requests`** `{fund_code, kind:'investigate'}` → `{case_id, queued:true}`.
  - Opens a case or raises its priority to user level.
  - At most 10 per user per hour; deduplicated.
- **Chat (existing endpoints, extended):**
  - The stream request accepts `page_context:{path,fund_code|null}` and general threads (`fund_code` null).
  - Threads are listed per fund or general.
  - The persona is "Raportör".
  - Tools: the existing read-only tools plus `get_case_status` and `request_investigation`. The latter calls the same
    service as `POST /agents/requests` and inherits its limits.
- **Scope.** The server always uses the analysis scope from the cookie. The client never supplies scope. Check that the
  ContextVar survives `StreamingResponse` iteration.

## 5. Web (C)

- **Remove:**
  - the `ChatPanel` sections on fund and stock pages ("Fon hakkında sorularınız");
  - the "Yayımlanmış veriler" / "Tarihe göre inceleme" / "Örnek test verileri" chips, and any similar tag that only
    restates the mode or the date;
  - leftover imports and CSS.
- **`components/agents/AgentDock.tsx`**, mounted once in the app shell so it appears on every page.
  - A floating mascot button at the bottom right: the placeholder art from DEC-035, done tastefully.
  - It carries a live state ring (working or idle) and a small badge for page notes or user-request progress.
  - Logged-out visitors get a compact sign-in prompt and no data.
- **`AgentTeamPanel`.** A wide horizontal panel anchored bottom right; on mobile, a full-width bottom sheet. Sections:
  - **Header.** "Ajan ekibi · 7/24", the analysis date, a daily budget meter and a close button.
  - **Team stage.** The five agents laid out as the workflow graph: Nöbetçi → (Hipotezci ∥ Şüpheci) → Doğrulayıcı →
    Raportör → İnsan kararı.
    - Each agent shows its state, its current activity and the fund it is working on.
    - Recent `links` animate as pulses along the edges.
    - The **Raportör is visually distinct** (larger, accent ring, "Sizinle konuşan ajan").
    - Selecting any agent opens its read-only workspace.
  - **Raportör tab.**
    - The page note, warning and suggestion chips.
    - The streamed conversation: per fund on fund pages, general elsewhere. Enter sends, Shift+Enter adds a newline,
      IME is guarded.
    - Thread history.
    - It never offers to chat with the other agents.
  - **Sıra tab.** The todo list: running, then queued (user requests highlighted), then done today, plus
    `waiting_budget` states.
- **Workspace.** An in-panel view or a route `/ekip/[role]`, read-only. It shows the current task, the inputs in plain
  language, the validated outputs, the messages exchanged with other agents and their timestamps.
- **Updates.** Poll `/agents/team` and `/agents/queue` every 2 s while the panel is open and every 15 s while it is
  closed. Pause when the tab is hidden.
- **Quality.**
  - Dark and light tokens from `web/app/design.css`.
  - Smooth open and close; reduced-motion support.
  - A focus-trapped dialog that closes on Esc, with aria-live activity updates.
  - Works at 390, 768 and 1440 px.
  - No placeholder content except the mascot art.
  - No hashes, IDs, enums or raw codes shown to users.
- **Tests.**
  - Vitest for the state mapping and the stream parser.
  - A Playwright smoke run against the synthetic stack: the dock on every primary page, the panel opening, the queue
    rendering, Enter sending.
- **Never run `npm run build` on the host;** port 3000 serves `.next`. Use `npm run typecheck` and `npm test`.

## 6. A (integration backend): finish the selected-date boundaries

Close handoff section 7.2:
- `/workflow` selects runs only for the exact historical day;
- a small safe retry for a failed idempotent date job;
- explicit cutoff overrides later than the selected day are rejected, and earlier explicit queries are reviewed;
- no current proposal, event, status or stock action leaks into historical pages, the watchlist, notifications or the
  workflow;
- `analysis_status` checks the persisted replay date and version;
- one synthetic test each for queue claim, deduplication, lease and worker payload scope.

Focused tests only; no broad Linux regression.

## 7. The 25-second recording (the target this build serves)

| Time | Shot | What must be true |
|---|---|---|
| 0–4 s | The catalog or home page. The navbar date reads 12 Eylül 2026, and the mascot pulses at the bottom right | The dock is visible on every page; the date is clear; no clutter chips |
| 4–10 s | Click the mascot. The wide panel opens on the five agents at work: Nöbetçi has opened cases, and pulses pass from Hipotezci and Şüpheci to Doğrulayıcı | Real cases from the 12 September run; smooth open animation; readable activity lines |
| 10–18 s | A fund page in the background. The Raportör shows its page note, then streams an evidence-based report in plain Turkish | Page awareness works; the report renders from validated text with real dated evidence |
| 18–25 s | The human-decision step: an analyst accepts or overrides. The Sıra list shows the next queued work and the daily budget | The override path is visible; the queue looks alive; the BlackSwan brand closes the shot |

Before recording, the real pipeline processes a handful of 12 September cases within the daily cap, so that the
panel shows finished and running work. The recording uses only real data.
