# Project 50K: current state

Updated 2026-10-10 (Europe/Istanbul), the Saturday of Startup Weekend Urla (9–11 October 2026). Start here.
[codex-context-2026-10-07.md](codex-context-2026-10-07.md) keeps the detailed data-source facts (its section 5),
the case study (section 6), the evaluation rules (section 7) and the do-not-claim list (section 11); those still
apply, except that DEC-029 replaces section 7's development/test split. Where the two files differ, this one is
newer.

## In one minute

- **Name: BlackSwan** ([DEC-030](../decisions/DEC-030-blackswan-working-agreements.md)). Codex continues the build from `plans/2026-10-10-codex-handoff-prompt.md`, written 2026-10-10 14:35.
- **Team ([DEC-028](../decisions/DEC-028-deploy-ready-ai-native-build.md)).**
  - Mirza: technical lead; all development and data gathering.
  - Safa: business person and repository owner; he only pulls.
  - Barış: designer of the pitch deck and the website's design system.
- **Goal.** Scientific, mathematical anomaly detection for Turkish investment funds. Stocks come later, only if
  time and licensed data allow.
- **Product (open).** Two candidate offers run on one shared core (see [product direction](product-direction.md)):
  - insurance policies designed from fund-risk data, sold B2B to insurers, brokers and banks;
  - B2B anomaly data.
  The team picks the headline story on Saturday evening.
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
- **Not built yet.** Live model/account checks, chat, agent-team/story screens and overnight refresh import.
  Product auth, fund API/screens, AI queue/validator/decision storage and review now exist. All 284 legacy end-to-end requirement IDs remain
  `NOT_IMPLEMENTED`; Phase 1 support is reported by slice.
- **Plan.** `plans/2026-10-10-product-build-plan.md`, confirmed by delegation (DEC-030). The open questions are in `team-asks.md`.
- **Running at handoff:** the all-fund TEFAS snapshot download (started 14:30, 2,136 funds, into `~/.local/share/project-50k/overnight/2026-10-10/`) and the live research demo.

## Codex takeover, 2026-10-10

- Main remains clean on `main` at `19989c5`; the live demo stays on its original ports.
- Mirza approved all four takeover recommendations. [DEC-031](../decisions/DEC-031-derived-evidence-openai-egress.md)
  records D7 and the other answers; the ten exact-name spot checks remain pending.
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
- T0.2 key readiness and T1.7a ten exact-match human checks remain pending; all SPK events remain candidates.
  K1–K6 and every do-not-claim item below remain carried forward. No frozen requirement registry was changed.
- Final Phase 1 implementation `8c07f66`: Linux root 741 tests OK (16 explained skips), frozen 9 and 88 pass.
  The 14 skipped PostgreSQL checks pass separately in isolated `p50k_dev`; two skips require Windows.
- Product branch was pushed and merged into remote `main` with merge commit `67af615` using a separate temporary
  worktree. The main checkout still holds `19989c5`, unchanged for the live demo. Do not pull it until K4.
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
  Product is healthy on 3070/8770, real mock count zero. OpenAI key file is absent; live AI remains off.
- Snapshots and KAP lists completed; SPK has 194 discovered PDFs. Profiles/prices continue externally.

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
| [DEC-031](../decisions/DEC-031-derived-evidence-openai-egress.md) | 2026-10-10 | Mirza approved derived-evidence-only OpenAI processing, all D9 downloads now, the product worktree, and the closest-name identity; Safa's D7 answer and ten exact-name checks remain open |

Still binding (the integrity rules hold even though product requirements flex):

- the TRY 5,000 cumulative ceiling, which is not spending authorization;
- no service accounts beyond the OpenAI key DEC-028 authorizes;
- unreviewed data rights for TEFAS, KAP and MKK data, so real data stays on localhost;
- the release gates in `docs/handoff-v0.5/docs/25_Release_Gates_and_Open_Decisions.md`, as DEC-024 scopes them:
  G03 is the critical data gate, and G02, G04 and G11 return only with the postponed markets.

**Who needs to do what:** see [team asks](team-asks.md). The owner, Safa, only pulls `main`. His open asks are the
headline story (due Saturday evening), the regulatory checks and his data sources. GitHub repository settings, such
as collaborators and branch protection, remain his.

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
- **Headline product story:** insurance policies or B2B anomaly data. Safa decides with the team, Saturday evening.
- **Regulation:** for insurance (SEDDK) and for selling signals (SPK), Safa checks before the pitch claims either
  (see `product-direction.md`).
- **G01, competition eligibility:** the team's position and the pre-event commit dates are recorded in DEC-027. No
  organizer ruling was requested.
- **G03, dated fund history:** open. Forward snapshots now build dated size, unit and investor history from
  2026-10-09.
- **G09, design:** open. The owner approved the fixed-view layout, and the agent reviewed the dated-view layouts.
- **G10, detector validity:** open. There is no measured evaluation; the per-date counts are descriptive.
- **Data rights:** unreviewed for TEFAS, KAP and MKK data. Nothing real is published.
- **Pitch facts to verify:** check SPK decision 52/1589 of 28 August 2026 against the bulletin before quoting it.
  B2B demand has no interviews, pricing test or letter of intent.

## Next work

**The product build plan** (`plans/2026-10-10-product-build-plan.md`) is confirmed. Phase 1 foundations have landed;
Phase 2 starts with the v2 detector protocol committed alone before computation. Items
recommended before 2026-10-10 are carried into that plan, not dropped:

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
