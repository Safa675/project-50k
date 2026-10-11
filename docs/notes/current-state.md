# Project 50K: current state

## Sunday product release — 2026-10-11 about 11:35 Istanbul (newest; read first)

The morning's nine takeover priorities are implemented and running. The original 10:40 handoff below is history,
not a pending WIP instruction. Read [the full release/continuation record](sunday-product-release-2026-10-11.md)
for exact checks, data admission, rollout commands, limits and the changed-file manifest.

- **Git:** core release `569c2db` on `product/build` merged through the integration worktree as `ac3cd26`, pushed to
  GitHub `main`, then safely fast-forwarded in the main checkout. Final method/login spacing and this record follow
  in an additional small commit. Mirza need not pull/push or switch any branch himself.
- **Real product:** 3070/8770, database `p50k`, migration 014, live AI, 12 September 2026 by default. Demo mode is real
  new work (`P50K_AGENT_DEMO=1`), about one background case per 120 seconds, with a USD 0.25 user reserve. Today's
  compensated bucket cap is USD 5.25; the runtime default is restored to USD 3.00 for new daily buckets. Known unsent connection failures now book zero;
  timeout/uncertain failures still retain their reservation. Previous uncertain bookings are preserved.
- **Smoke:** 3071/8771, `p50k_dev`, AI off, test endpoints on, also defaults to 12 September. Its branded login is
  polished without changing auth. Synthetic one-off tests explicitly use their own analysis context.
- **Product:** supplied agent SVGs; larger draggable/saved/clamped mascot; expanded parallel flow by default; spacious
  conversation and workspace lists; neutral fund summary; calmer review; authentic method/source trail; `/sonuclar`;
  avatar/tab icon/date chip. The expanded conversation measures 334.5 px at a 1480×712 viewport, with input visible.
- **Data:** all 50 official BIST bulletins validated/imported as 1,500 real closes. The 12 September view admits 900
  closes and 11 September membership; ForInvest capture-only rows are preserved and never backdated. The 131 later
  SPK orders are used only in the explicitly after-the-fact results comparison, never by the scan or agents.
- **Verification:** 99 focused Python checks across the five reported module groups passed on isolated PostgreSQL,
  plus the final completion-lock regression. Web typecheck/64 unit tests and Docker builds passed; three focused
  synthetic agent browser checks passed. The final 52-view audit has no HTTP failures, horizontal overflow, raw-ID
  matches or JS errors. The discovered monthly-report SVG title hydration bug was fixed. Minor final CSS changes
  receive focused component checks; no full-stack rerun is required for those.
- **Protected assets:** fallback 3060/8767/8768, frozen protocols/detectors, sealed modules, `raw/`, external archives,
  previous model decisions and data volumes are unchanged. Leak scans passed before app and integration commits.
- **Remaining limits:** stock anomaly/AI is not implemented; full browser regression was not rerun; phone keyboard
  overlap has not been tested. Commercial data rights, pricing/demand/pilot and partnerships remain unvalidated.
  Insurance stays permanently deferred. Next: record the polished THF/results/stock flow before freeze.

## Codex handoff — 2026-10-11 about 10:40 Istanbul (superseded; preserved below)

Claude's usage limit ran out mid-sprint. Read `plans/2026-10-11-codex-handoff-prompt.md`.
- **Open requests from Mirza (09:35 and 09:40):** eleven workstreams, specified in `plans/2026-10-11-sprint-briefs.md`:
  - agent panel height, `/review`, `/method`, `/sonuclar` success metrics, the fund warning card, stocks from the official
    BIST bulletins, demo mode, the avatar photo, the tab icon, and the date chip without "Retrospektif inceleme".
  - Partial code is a WIP checkpoint on `product/build`, not deployed and not merged.
- **Agent budget:** failed model calls were booked at their maximum, so a network outage blocked the team. Today's
  agent cap is compensated to $5.25 (actual spend $0.77). The real fix in `llm.py` is pending.
- **Data:** 50 official Borsa İstanbul daily bulletins (3 August to 9 October) are downloaded outside git under
  `~/.local/share/project-50k/overnight/2026-10-11/bist/thb/`. They are not imported yet.

## Review rounds and full test battery — 2026-10-11 about 08:30–09:35 Istanbul

- **Live product (3070/8770)** runs images built from `product/build` `fd03482` (main `a5e01d1`). The rollback images
  from before this section are tagged `p50k-product-api:rollback-0815` and `p50k-product-web:rollback-0815`.
- **Later the same morning:**
  - A step whose model call fails retries after a minute, up to the attempt limit. The laptop slept from 08:25 to
    09:02, which broke in-flight calls; case AJ1 was retried through a user request.
  - The Raportör's page note refreshes after requests and while the case runs, so its case link follows a new round.
  - "İnsan kararına git" closes the panel.
  - The workspace page shows the agent team's progress.
- **Draft recording** (outside git): `C:\Users\mirza\Desktop\Hackathon\recordings\BlackSwan-demo-draft.mp4`, about
  46 seconds. It is a scripted capture of the real product with live AI, and the team's working time plays 8× faster
  under an on-screen label.
- **Changes** (DEC-035 addendum):
  - Doğrulayıcı runs every standard test after Şüpheci's picks.
  - A request on a reported case that no human has reviewed opens a new review round.
  - Fund pages label team proposals "Ajan ekibinin Raportör önerisi".
  - The panel's worker count matches the agent cards.
- **THF's second round** (user request, live AI) is reported. Its monthly-report test flags the August report,
  published 2 September 2026, as a notable change in units and total value, the jump recorded in
  `codex-context-2026-10-07.md`. The case flow shows the code-computed figures, and the new proposal awaits human
  review. The first round is closed but kept.
- **Checks run:**
  - 40 focused Python tests passed: agents, agent database, analysis scope and decisions.
  - Web typecheck and 49 unit tests passed.
  - 10 agent Playwright tests passed on smoke.
  - Real-product screenshots were checked.

## Agent team release — 2026-10-11 about 08:10 Istanbul

- **Live product:** http://127.0.0.1:3070, with API 8770, running the images built from `product/build` commit
  `7b5cf46` (DEC-035). The real database `p50k` has migrations through `013_agent_team.sql`. The default analysis
  date is **12 September 2026**, and AI is live.
- **The always-on agent team runs in the worker.**
  - Nöbetçi scanned all 2,133 funds as of 12 September and opened 189 cases, the replay's any-triggered funds.
  - Each case runs Hipotezci ∥ Şüpheci → Doğrulayıcı (code-computed tests) → Raportör, which files a proposal into
    the existing human review.
  - The daily budget bucket is `agents:YYYY-MM-DD` with a $3 cap; background pace is about one case every 5 minutes;
    user requests jump the queue.
  - The first real case was reported for $0.048.
- **Web.**
  - A mascot dock (placeholder art, per DEC-035) is on every page and opens the team panel: the five-agent graph,
    the Raportör tab with per-fund or general persistent conversations, the Sıra queue, read-only workspaces and
    `/ekip`.
  - The "Fon hakkında sorularınız" section and the status chips are removed.
- **Checks run:**
  - 62 focused Python tests passed; 1 setup needs owner access and did not run, so it is not a pass.
  - 49 web unit tests passed.
  - 11 Playwright tests passed on the smoke stack (3071/8771, `p50k_dev`, AI off).
  - Screenshots were checked.
  - The adversarial reviewer pass was lost to usage limits.
- **Known issues:** one worker heartbeat `_DeadlockError` at startup; non-fatal, and work continues.
- **Demo:** a ~25-second screen recording (DEC-035 storyboard in `docs/notes/agent-team-design-2026-10-10.md`,
  section 7).
- **Next:**
  1. Keep the team healthy and record.
  2. Merge `product/build` into `main` through the integration worktree with protected-path checks.
  3. Add stock checks for Nöbetçi with the Borsa İstanbul v2 source (after the recording).

## Claude takeover checkpoint — 2026-10-10 about 21:45 Istanbul

Read [the complete Claude handoff](../../plans/2026-10-10-claude-resume-handoff.md)
before continuing. Main and the running product remain the released `9a2a993`
merge (`84438f7` product code, `e65c8e6` verification). The app worktree contains
new work being checkpointed separately; it has **not been deployed or merged**.

Mirza's latest DEC-034 direction is product depth, persistent asset conversations,
Enter-to-send, coherent catalog/results tabs, real monthly data and a genuine
12 September review. He expressly deprioritized repeated Linux/backup meta work.

The unchanged full-universe historical calculation has completed in the real DB:
2,133 funds, 17,064 results, four of eight case funds triggered D1 (THF, TP2,
PRY, PNU), 69 price-triggered funds overall. No later event was admitted; the
other four case funds remain without a price trigger. See the linked replay notes.
Existing KAP reports supply dated units/size for all eight case funds. New code
connects that data and preserves chat by owner/fund/date. Migration 012 is applied
only in synthetic `p50k_dev`; production remains at 11 migrations.

Immediate checks at handoff: web typecheck passed; 30 web unit tests passed;
29 targeted chat/history/KAP-series tests passed on isolated PostgreSQL in
9.709 seconds with zero skips. The combined new API/UI images and historical
browser flow remain unbuilt/unverified. No active download or paid job remains.

An official BIST September 11 bulletin with prices and dated BIST 30 membership
has been downloaded externally, but has **not** been admitted/imported. It offers
a concrete next stock-history source; the existing capture-only stock protocol
must not be backdated. Exact files and all remaining checks are in the handoff.

Latest read-only real ledger: 32 paid calls, USD 0.2995650 booked, zero reserved;
two succeeded jobs, none queued/running. Preserve the product database and all
external files. The last backup predates the newly computed historical run.

Updated 2026-10-10 (Europe/Istanbul), the Saturday of Startup Weekend Urla (9–11 October 2026). Start here.
[codex-context-2026-10-07.md](codex-context-2026-10-07.md) keeps the detailed data-source facts (its section 5),
the case study (section 6), the evaluation rules (section 7) and the do-not-claim list (section 11); those still
apply, except that DEC-029 replaces section 7's development/test split. Where the two files differ, this one is
newer.

## In one minute

- **Latest usability release (DEC-033).** The product now uses plain-language source/results, dated last-known
  prices, verified asset logos and actual streamed AI explanations. "Bu sonuca nasıl ulaştık?" explains the
  registered methods beside results and on `/method`. Internal hashes/codes remain in audit/API records.
  Code checkpoint `84438f7`; [completion report](blackswan-user-experience-completion.md). All 16 browser tests,
  21 web unit tests, typecheck/build and separate PostgreSQL checks pass. Chat v4 passed three live questions;
  proposal v3 passed eight readable, evidence-supported cases. These are small development checks.
  Linux verification: 831 passed, 73 skipped; frozen suites 9/88 passed. Latest backup/restore verified
  39 tables and eleven migrations, including the new paragraph audit and live proposal records.
- **Name: BlackSwan** ([DEC-030](../decisions/DEC-030-blackswan-working-agreements.md)). Codex continues the build from `plans/2026-10-10-codex-handoff-prompt.md`, written 2026-10-10 14:35.
- **Team ([DEC-028](../decisions/DEC-028-deploy-ready-ai-native-build.md)).**
  - Mirza: technical lead; all development and data gathering.
  - Safa: business person and repository owner; he only pulls.
  - Barış: designer of the pitch deck and the website's design system.
- **Goal ([DEC-032](../decisions/DEC-032-b2b-evidence-data-api.md)).** Evidence data for Turkish funds and Turkish
  stocks. The historical fund case is first; Mirza requires real stock support in the hackathon demo too.
- **Product (confirmed).** B2B evidence data and API access through an agent workflow for banks and financial
  institutions. Insurance is permanently deferred. Buyer class and revenue direction are decided; customer
  demand, pricing, partnerships and redistribution rights remain unvalidated. See
  [product direction](product-direction.md).
- **Build target (DEC-028).** A deploy-ready full-stack product with real data on localhost, not deployed.
  - Stack: Next.js frontend, FastAPI backend, PostgreSQL with its own email/password auth, and a worker, in Docker.
  - Code freeze: Sunday 2026-10-11 13:00.
- **AI-native (DEC-028, non-negotiable).**
  - An OpenAI LLM decides from the deterministic detector evidence.
  - A human can override every LLM decision.
  - Users chat with the LLM in the UI.
- **Data ([DEC-029](../decisions/DEC-029-open-all-funds.md)).** Every downloaded fund is open for product use.
  There is no held-out test set, so every detector figure is a development result.
- **Built so far.**
  - A private local research app for the 100 funds with the most investors, served from sealed bundles of real
    archived data. It has a fixed 16 September 2026 view and a dated D1 view at 12 preregistered dates.
  - The data layer and the preregistered detectors D1–D5.
  - Forward TEFAS snapshot collection.
  - BlackSwan Phase 1: Docker PostgreSQL, role-separated migrations, immutable evidence/AI storage,
    real archive import, health API/worker, public web page and tested proxy. Details below.
  - The research app remains the fallback demo.
- **Product built.** Login, fund catalog/detail/charts, immutable evidence, live derived-evidence AI
  decisions/chat, human review, the B2B workflow overview and protected API documentation. Real BIST 30
  catalog, daily charts and source-backed API contain 30 stocks, 870 daily closes and five observed
  corporate-action records. Stock classification/AI is not implemented.
- **Design.** All 22 supplied Figma contexts and screenshots are implemented as ten base pages/states and twelve
  hover/context variants, running at `http://127.0.0.1:3070`. Typecheck/build, 14 browser tests and 16 web unit tests
  pass; see [Figma implementation](figma-implementation-2026-10-10.md) and its linked completion report.
- **Remaining.** Wider quality coverage and separately budgeted batch wiring/pass; optional challenger/committee workflow;
  Sunday freeze backup/tag and cold-boot/demo rehearsal. The frozen
  requirement registry remains unchanged; implementation is reported by slice.
- **Plan.** `plans/2026-10-10-product-build-plan.md`, confirmed by delegation (DEC-030). The open questions are in `team-asks.md`.
- **Current data checkpoint.** 2,133 funds; 1,755,010 stored price rows; 3,304 snapshots; 12,111 KAP document
  entries; one immutable calibration. Latest detector run: 17,064 results. External outputs stay in
  `~/.local/share/project-50k/overnight/2026-10-10/`; provider failures remain explicit.
- **Git and resume.** Mirza resumed and delegated pushes, merges and safe pulls to Codex. Build work stays
  in `project-50k-app` on `product/build`, in the same repository. Main was safely advanced to `3b7bf4c`
  before Figma integration; subsequent pulls must preserve the live demo registered paths.

Final Figma code checkpoint `0b394a1`: Linux root 816 passed / 72 skipped (70
PostgreSQL, two Windows-only); frozen detector nine and handoff 88 passed.
Separate PostgreSQL evidence/watchlist/chat/API 42 and migration 16 passed with
zero skips. The real product has ten migrations, zero mock decisions and live
AI enabled. Seven completed paid calls conservatively book USD 0.0615725; no
queued/running jobs at the release check. Every result remains developmental.
The second backup/restore rehearsal includes final imported data and all ten
migrations: 38 table counts, evidence checksums and permissions matched. Its
ignored dump and full recovery limits are recorded in
[the backup report](blackswan-backup-restore-rehearsal.md).

After usability tuning, at 20:59 Istanbul: 15/20 tuning attempts used, USD 0.09712
of the USD 1 tuning bucket spent; total AI booked USD 0.267445; zero reservations
or queued/running jobs. No 300-fund batch ran. Current backend completion is an
engineering estimate of roughly 85% of the local hackathon scope; stock anomaly
classification and stock AI are still unimplemented. No production-readiness or
validated financial-performance claim follows from that estimate.

## Codex takeover and milestone history, 2026-10-10

The following records retain checks at each milestone. The current checkpoint and resumed-build section
supersede milestone-only pending items.

- Mirza pulled 14 commits into the main checkout, from `19989c5` to `603a09d`. It is clean on `main`; the same
  fallback listener processes remain on 3060/8767/8768. The main checkout is still load-bearing: do not switch
  branches or change registered files, and verify registered paths before any future pull.
- Mirza approved all four takeover recommendations. [DEC-031](../decisions/DEC-031-derived-evidence-openai-egress.md)
  records D7 and the other answers; the delegated ten exact-name spot checks are now complete.
- Build work now runs in `C:\Users\mirza\Desktop\Hackathon\project-50k-app`, branch `product/build`.
- Docker Desktop started locally; the four pinned images were pulled. The product extra is locked and installed.
- D9 downloads are authorized immediately, not only overnight. Restartable runners preserve one paced stream per host
  and write only to the external overnight folder. SPK completed 194 PDFs; KAP is collecting the authorized missing
  TEFAS-traded report lists using the official public directory. Profiles and refreshed prices wait for the existing
  all-fund snapshot collector before requesting TEFAS.
- Baseline at `19989c5`: frontend typecheck/build exit 0, 118 unit tests and 65 browser tests pass; frozen Python
  suites pass 9 and 88 tests. Root Windows suite: 663 tests, 6 failures, 30 errors, 1 skip. Diagnostic: 663 tests,
  the three known residual failing names only (1 failure, 2 errors), 1 skip. Linux baseline at that commit passes
  all 663 root, 9 frozen detector and 88 handoff tests, with no skips.
- Archive audit: 2,133 listed funds; 2,022 price files contain 1,725,078 dated rows, including 1,673,412 positive
  prices and 51,666 nulls. The importer must preserve missing rows, not count only positive prices.
- Phase 1 foundations run on loopback 3070/8770, with PostgreSQL on 5433 under the dev overlay. Real archive counts
  reconcile: 2,133 funds, 1,725,078 prices, 1,173 snapshots, 1,292 KAP document entries, 1,255 report-index rows,
  and 131 candidate regulatory events. Repeat imports add zero observation rows. Permissions and isolated proxy
  checks pass; real-data access defaults to denied until Phase 3 auth. AI is off. See the
  [completion report](blackswan-phase1-completion.md) for actual checks and limitations.
- At Phase 1, key readiness and the ten exact-name checks were pending. Both were subsequently completed:
  Mirza supplied the key and authorized the independent audit. Unknown publication times still prevent
  regulatory triggers. K1–K6 remain carried forward; the frozen requirement registry was not changed.
- Final Phase 1 implementation `8c07f66`: Linux root 741 tests OK (16 explained skips), frozen 9 and 88 pass.
  The 14 skipped PostgreSQL checks pass separately in isolated `p50k_dev`; two skips require Windows.
- Product branch was pushed and merged into remote `main` with merge commit `67af615` using a separate temporary
  worktree. At that milestone the main checkout still held `19989c5`; Mirza's later safe pull to `603a09d` is
  recorded above. K4 still means decoupling the demo, not permission to alter registered paths.
- Phase 2: v2 protocol committed alone at `e9b7ba7`; real run has 17,064 evidence/results for 2,133 funds,
  one immutable calibration, and an idempotent rerun. API/DTO checks pass and all 131 events remain candidates.
  Linux `c8bd652`: 810 tests OK (37 explained skips); frozen 9 and 88 pass. See the
  [Phase 2 completion report](blackswan-phase2-completion.md). Phase 3 full-stack work is underway.
- Phase 3 `2158638`: login/session auth, protected real fund pages/evidence, original/effective decision display,
  review, bounded AI wrapper/egress/validator and leased worker. Isolated browser login→override→logout passes.
  Linux 827 OK (44 explained skips), frozen 9/88 pass; [completion report](blackswan-phase3-completion.md).
- Final Phase 3 Python `6714f43`: Linux 829 tests OK (46 explained skips); the actual isolated queue→proposal→
  override/rejection flow and concurrent reservation/lease tests pass. No calibrated detector code changed.
- Local admin credentials were generated into ignored `secrets/local-admin-login.json` without displaying them.
  Product is healthy on 3070/8770, real mock count zero. Key supplied; live model/decision/chat smoke passed. On-demand AI is live under the existing caps.
- Snapshots, profiles and KAP cohort completed; SPK has 194 discovered PDFs. Prices continue externally; source failures are retained in status logs.
- T5.1 refresh imported 13,101 additional prices, 2,131 snapshots and 10,819 KAP indexes. Catalog/categories and
  calibration remain unchanged; two newly discovered snapshot codes stay external. New data is admitted at acquisition
  (KAP: conservative import admission because response-completion time is unknown), never backdated.
- Refreshed run `133a58c1-606c-42f4-8750-0102af458bcb`: 17,064 results, 2,133 funds, as-of 2026-10-09,
  same immutable calibration. All regulatory signals abstain. Ten authorized exact-name checks passed; 131
  confirmed event versions retain unknown publication time and remain ineligible to trigger.
- T5.2 owner-scoped chat backend, four read-only tools, budget/daily/call limits, validated SSE and UI exist.
  Synthetic PostgreSQL integration passes 48 tests with zero skips; web unit 9 and browser 7 pass.
  Live proposal and chat smoke passed (five calls, conservative booked USD 0.048630). Latest Linux suite
  at `726c81d`: 858 OK, 55 explained skips; frozen 9/88 pass. See [chat/refresh report](blackswan-chat-refresh-completion.md).
  At that milestone, live validation quality, stocks and the agent-team/B2B story were unfinished;
  subsequent stock and B2B workflow implementation is recorded below.
- DEC-032 records Mirza's confirmed B2B direction: evidence data/API for banks and financial institutions through
  an agent workflow; Turkish funds and stocks required in the hackathon demo, historical fund case first, insurance
  permanently deferred. Mirza requested an alignment pause after this block and subsequently resumed.
  He selected current BIST 30, supplied Figma designs and the logo, and requested parallel implementation.
  Work continues tonight and Sunday morning within the existing freezes.

## Decisions after the handoff

| Record | Date | Decision |
|---|---|---|
| [DEC-024](../decisions/DEC-024-turkish-funds-first.md) | 2026-10-06 | Turkish funds first; BIST, crypto, US equities and on-chain postponed, not dropped |
| [DEC-025](../decisions/DEC-025-b2b-fund-monitoring-pitch.md) | 2026-10-09 | Pitch B2B fund-risk monitoring; B2B demand is a hypothesis; scope stays on funds |
| [DEC-026](../decisions/DEC-026-dated-d1-research-view.md) | 2026-10-10 | Dated D1 view at 12 preregistered dates, D1 only, with a separate API and `/dates` pages |
| [DEC-027](../decisions/DEC-027-event-weekend-operations.md) | 2026-10-10 | The owner only pulls and the team makes all writes. Merge commits only. Real data appears only in the private local demo. Forward snapshots run on the team's machine |
| [DEC-028](../decisions/DEC-028-deploy-ready-ai-native-build.md) | 2026-10-10 | Team roles; deploy-ready, AI-native build on localhost; OpenAI with a $25 limit; plain PostgreSQL with its own auth; code freeze Sunday 13:00; earlier specs are guides |
| [DEC-029](../decisions/DEC-029-open-all-funds.md) | 2026-10-10 | Every downloaded fund is open for product use; the development/test split is dropped |
| [DEC-030](../decisions/DEC-030-blackswan-working-agreements.md) | 2026-10-10 | Product name BlackSwan; no placeholders; $25 a target, not a hard cap; plan confirmed by delegation; persistent reminders for critical unanswered items; downloads started; Codex handoff |
| [DEC-031](../decisions/DEC-031-derived-evidence-openai-egress.md) | 2026-10-10 | Mirza approved derived-evidence-only OpenAI processing, all D9 downloads now, the product worktree, and the closest-name identity; the later delegated ten-check audit is complete; Safa's separate D7 answer remains open |
| [DEC-032](../decisions/DEC-032-b2b-evidence-data-api.md) | 2026-10-10 | B2B evidence data and API through an agent workflow for banks and financial institutions; insurance permanently deferred; Turkish funds and stocks required in the hackathon demo, historical fund case first; stock implementation proceeded after Mirza resumed |

Still binding (the integrity rules hold even though product requirements flex):

- the TRY 5,000 cumulative ceiling, which is not spending authorization;
- no service accounts beyond the OpenAI key DEC-028 authorizes;
- unreviewed data rights for TEFAS, KAP and MKK data, so real data stays on localhost;
- the release gates in `docs/handoff-v0.5/docs/25_Release_Gates_and_Open_Decisions.md`, scoped by DEC-024 and
  DEC-032: G03 remains the fund-history gate; stock implementation must address G02 data rights. G04/G11 for the
  remaining postponed markets are not brought into the hackathon by this direction decision.

**Who needs to do what:** see [team asks](team-asks.md). The owner, Safa, only pulls `main`. The B2B story is
confirmed; his open asks are the first customer workflow, pricing validation, regulatory/data-rights checks and
his data sources. GitHub repository settings, such as collaborators and branch protection, remain his.

## What exists

| Area | Where | Notes |
|---|---|---|
| Data layer | `services/p50k/providers/`, `services/p50k/jobs/` | TEFAS client, KAP report reader, holdings parsers, retry and circuit breaker, snapshot and price-history jobs |
| Evidence store and replay | `services/p50k/evidence_store.py`, `services/p50k/replay.py` | [Slice note](evidence-store-replay-slice.md) |
| Research (development results only) | `research/events/2026-09-17-spk-liquidations/` | Preregistered price detectors D1–D5. Notes on [fund flow](fund-flow-research-slice.md), [allocation](fund-allocation-research-slice.md), [THF equity](thf-equity-divergence-research.md) and [THF futures](thf-futures-contribution-research.md) |
| Fixed-date app | `services/p50k/api/`, `frontend/`, `ops/local/run_app.py` | All 100 funds at 2026-09-16: D1, July–August estimated flow, disclosed-holdings concentration and KAP PDFs. See the [completion note](top100-fund-app-completion.md) and the [concentration note](fund-concentration-app-slice.md) |
| Dated D1 view | `/dates` pages, `services/p50k/api/dated_*.py`, `ops/local/run_dated_app.py` | 12 dates. See the [completion note](fund-review-dated-slice.md) and the [design note](fund-review-dated-design.md) |
| Snapshot collection | `services/p50k/jobs/fund_snapshots.py`, `ops/systemd/`, `ops/windows/` | Forward collection on the team's machine since 2026-10-10 (DEC-027) |
| Agent tooling | `.claude/`, `CLAUDE.md`, `AGENTS.md` | Skills, hooks and path rules: [agent-tooling.md](agent-tooling.md) |

## Private data and sealed outputs

None of this is in git ([local data layout](local-raw-data-layout.md)). Sealed bundles record the absolute paths
they were sealed with, so every machine seals its own.

- **Owner's Linux laptop:** the original archive under `raw/` and `~/.local/share/project-50k/`, including the
  fixed-date bundles sealed there.
- **Team's Windows machine:**
  - The main checkout holds a copy of the archive and the fixed-date bundles `40c04903…` (v1) and `086d934a…` (v2,
    with concentration).
  - A second LF clone holds the dated index `6623c78d…` and runs the demo.
  - Forward snapshots go to `~/.local/share/project-50k/fund_snapshots_forward.sqlite3`. No sealed bundle reads
    that file.

## Running the demo

On the team's Windows machine the demo runs from the dated-view clone and serves:

- the fixed view at `http://127.0.0.1:3060/`;
- the dated view at `http://127.0.0.1:3060/dates`.

The bundle paths are in that clone's `.claude/p50k-demo.local.json`. Run these from the dated-view clone's root;
from another checkout they leave the demo alone:

```powershell
powershell -ExecutionPolicy Bypass -File .claude/skills/p50k-demo/start-demo.ps1 -Restart
powershell -ExecutionPolicy Bypass -File .claude/skills/p50k-demo/stop-demo.ps1
```

**The main checkout is load-bearing.** The demo's fixed bundle lives in the main checkout's `raw/`. On every load
it re-hashes the main checkout's registered files and `raw/snapshots/fund_snapshots.sqlite3`. While the demo runs,
in the main checkout:

- do not switch branches;
- do not pull or edit changes to registered files;
- do not touch that database.

Otherwise the fixed view answers 503. Do not run `npm run build` in the dated-view clone while the demo runs:
Next.js deletes the `.next` folder the running server uses.

On Linux:

1. Pull `main`.
2. Seal the fixed-date bundles:
   - seal v1 as in the README's local app section;
   - then extend it with concentration:
     `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/bin/python research/events/2026-09-17-spk-liquidations/fund_concentration_app/run.py --base-bundle raw/research/fund-review-app/<v1>`.
     It prints the v2 directory.
3. Seal the dated index from the v1 bundle: see "Optional dated D1 view" in
   [ops/local/README.md](../../ops/local/README.md).
4. Start the demo with `.claude/skills/p50k-demo/start-demo.sh <v2 bundle> <dated index>`.

The `/p50k-demo` and `/p50k-seal-dated` skills hold the details.

## Verification baseline

Recorded at `33c6064` on the team's Windows machine; the commands are in `/p50k-verify`.

- **Python root suite:** 605 tests.
  - The documented command reports 43 failures and 33 errors. All are known Windows platform effects.
  - The Windows diagnostic variant leaves three known residuals.
  - The suite has not been run on Linux at this commit.
- **Frozen suites:** the frozen detectors pass 9 tests and the frozen handoff passes 88.
- **Frontend:**
  - typecheck and build exit 0;
  - 118 unit tests pass;
  - 65 browser tests pass.
- **Hooks:** `node --test .claude/hooks/hooks.test.mjs`.

Treat any new failure name as a finding, not only a changed count.

## Open questions and gates

- **Development/test split:** closed by DEC-029. All funds are open, there is no held-out test set, and every
  detector figure is a development result.
- **Headline product story:** closed by DEC-032: B2B evidence data and API for banks and financial institutions.
  Insurance is permanently deferred.
- **Stock timing/universe:** closed by Mirza: current BIST 30 must work in the demo. The real catalog/chart/
  evidence/API slice is built; stock classification and AI remain separate unimplemented work.
- **Regulation:** Safa checks the capital-markets and data-rights route before any commercial claim or external
  resale. Insurance research is retained as history, not an active build or legal-work task.
- **G01, competition eligibility:** the team's position and the pre-event commit dates are recorded in DEC-027. No
  organizer ruling was requested.
- **G03, dated fund history:** open. Forward snapshots now build dated size, unit and investor history from
  2026-10-09.
- **G09, design:** supplied Figma designs are implemented, with final integration checks in progress.
  The approved research layouts remain the fallback; the frozen gate registry is unchanged.
- **G10, detector validity:** open. There is no measured evaluation; the per-date counts are descriptive.
- **Data rights:** unreviewed for TEFAS, KAP and MKK data. Nothing real is published.
- **Pitch facts to verify:** check SPK decision 52/1589 of 28 August 2026 against the bulletin before quoting it.
  B2B demand has no interviews, pricing test or letter of intent.

## Next work

**The product build plan** (`plans/2026-10-10-product-build-plan.md`) is confirmed, with DEC-032 setting the active
B2B story and fund/stock product scope. Phase 1 foundations, Phase 2 fund detectors/API and Phase 3 auth/review
have landed. Mirza resumed; real stocks, the B2B workflow overview and supplied Figma designs are present.
Finish integration checks, measured live tuning/batch gates, demo preparation and freeze operations.
Challenger/committee work remains conditional. Earlier recommendations are retained in the plan:

1. **Per-date estimated flow.** Now a candidate detector inside the product pipeline. Fix its parameters in a dated
   note first, using DEC-026's pre-recorded (M-2, M-1) rule.
2. **Windows test hygiene.** Largely solved by running the Python suites in a Linux container. Remaining causes: a
   missing `tzdata`, CRLF test fixtures, the cp1252 console, SQLite file handles and `SO_REUSEADDR`. The SQLite lock
   errors may involve the registered `evidence_store.py`, and changing that file needs an approved reseal.
3. **The split decision.** Closed by DEC-029.

## Do not claim

Section 11 of the codex context still applies. In addition, the pitch and demo must not claim:

- that the dated view "caught", "warned about" or "would have flagged" a fund early, or any lead time;
- that the per-date counts are detection performance;
- that institutions want to buy the product (demand is a hypothesis);
- that SPK's reasons for the 17 September order are known;
- that any detector figure is validated accuracy (there is no held-out test, DEC-029);
- that the LLM's decisions are predictions, or advice to buy, hold or sell;
- that a policy price is actuarially sound before base rates exist.

## Resumed stock and design build

Mirza resumed the build and confirmed current BIST 30 as the stock universe.
He delegated all Git work, including safe pulls. Root verified protected paths
and fast-forwarded local main to `3b7bf4c`; development stays in the app worktree.

Stock data-only protocol was committed alone at `853d3ae`, before ingestion.
The first real BIST30 capture contains 30 current members, 870 daily closes
(2026-09-01 through 2026-10-09) and five observed corporate-action records.
All 33 MCP structured-response captures were hash-verified. Normalized manifest
SHA `8e26ff013cf667f773566986b8341a545b9813a653c82bba20fd758536c770b5`.
Actual import succeeded; repeat added zero rows. Availability is capture time,
price adjustment is UNVERIFIED, and rights remain UNREVIEWED. This is stock
catalog/chart/evidence/API support, without a stock anomaly classifier or AI
materiality decision. Fund calibration and sealed sources are unchanged.

A real B2B workflow overview reports ingestion, deterministic evidence, AI
proposal and human-review counts, with current-run provenance and API docs.
It explicitly describes the existing single-proposal/human-review workflow;
there is no fabricated challenger/committee transcript. Synthetic stock and
workflow checks pass; stock UI browser integration passes eight tests.

Mirza supplied [22 Figma nodes](figma-implementation-2026-10-10.md). Figma access is fixed: all contexts and
screenshots were read. Four agents implemented the shared shell, landing/method, funds, watchlists/
notifications, development detail and contextual chat in parallel. Tokens, the exact logo and SVG assets
are local; Figma sample financial values were not copied into the product.

Final fund refresh: 1,755,010 prices, 3,304 snapshots and 12,111 KAP document entries for the unchanged
2,133-fund universe. Run `4dcee718-6c5b-4506-b251-2ed563260b60` contains 17,064 results using the original
single calibration. Six live paid model/decision/chat calls have completed; measured tuning quality and
the gated batch remain unfinished. Earlier cost figures above are milestone figures, not the final ledger.

Collection finished with explicit source gaps: 2,129 price files and four failures; 2,134 profile files,
one profile failure and five empty responses; the 1,071-fund KAP cohort completed through 996 on-disk
lists and reused existing inputs; all 194 discovered SPK PDFs completed. Failed or empty responses are
not invented observations. Outputs remain in the external overnight folder.

The [backup/restore rehearsal](blackswan-backup-restore-rehearsal.md) verified a consistent snapshot of
34 tables and eight migrations, including permissions and immutability. Its dump predates the final
refresh and migrations 009/010, so it is not a backup of the completed design/watchlist build. Repeat
backup after final data/review changes at the Sunday freeze.
