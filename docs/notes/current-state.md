# Project 50K: current state

Updated 2026-10-10 (Europe/Istanbul), the Saturday of Startup Weekend Urla (9–11 October 2026). Start here.
[codex-context-2026-10-07.md](codex-context-2026-10-07.md) keeps the detailed data-source facts (its section 5),
the case study (section 6), the evaluation rules (section 7) and the do-not-claim list (section 11); those still
apply. Where the two files differ, this one is newer.

## In one minute

- **Product:** Turkish-language monitoring of Turkish investment funds. When something notable happens to a fund,
  show what changed, when it became known and its sources. No advice, no prediction, no fraud claims.
- **Scope:** Turkish investment funds only ([DEC-024](../decisions/DEC-024-turkish-funds-first.md)). The event
  pitch is fund-risk and disclosure monitoring for fund distributors and their compliance teams
  ([DEC-025](../decisions/DEC-025-b2b-fund-monitoring-pitch.md)). Stocks stay postponed: institutional use of
  Borsa Istanbul data needs a paid data distribution agreement.
- **Built:** a private local research app for the 100 funds with the most investors, served from sealed bundles of
  real archived data. It has a fixed 16 September 2026 view and a dated D1 view at 12 preregistered dates. Turkish
  Next.js UI and read-only FastAPI, both on loopback.
- **Not built:** sign-in, accounts, hosting, alerts, email, AI investigation, live data. All 284 requirement IDs
  remain `NOT_IMPLEMENTED`.
- **Blocks evaluation:** the development/test split of the liquidated funds is undecided. The 1,922 other
  downloaded price files stay unopened, and no accuracy figure exists.

## Decisions after the handoff

| Record | Date | Decision |
|---|---|---|
| [DEC-024](../decisions/DEC-024-turkish-funds-first.md) | 2026-10-06 | Turkish funds first; BIST, crypto, US equities and on-chain postponed, not dropped |
| [DEC-025](../decisions/DEC-025-b2b-fund-monitoring-pitch.md) | 2026-10-09 | Pitch B2B fund-risk monitoring; B2B demand is a hypothesis; scope stays on funds |
| [DEC-026](../decisions/DEC-026-dated-d1-research-view.md) | 2026-10-10 | Dated D1 view at 12 preregistered dates, D1 only, with a separate API and `/dates` pages |
| [DEC-027](../decisions/DEC-027-event-weekend-operations.md) | 2026-10-10 | The owner only pulls and the team makes all writes. Merge commits only. Real data appears only in the private local demo. Forward snapshots run on the team's machine |

Still binding:

- the TRY 5,000 cumulative ceiling, which is not spending authorization;
- no service accounts;
- unreviewed data rights for TEFAS, KAP and MKK data;
- the release gates in `docs/handoff-v0.5/docs/25_Release_Gates_and_Open_Decisions.md`, as DEC-024 scopes them:
  G03 is the critical data gate, and G02, G04 and G11 return only with the postponed markets.

**Owner actions needed now: none.** The owner pulls `main` to see changes. One owner decision is still pending,
asked on 2026-10-07: the development/test split (see Open questions). GitHub repository settings, such as
collaborators and branch protection, remain his.

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

- **Development/test split:** the owner's decision, pending since 2026-10-07. The proposal splits by company; see
  section 7 of the codex context. Until it is decided, compute nothing on the 1,922 unopened price files.
- **G01, competition eligibility:** the team's position and the pre-event commit dates are recorded in DEC-027. No
  organizer ruling was requested.
- **G03, dated fund history:** open. Forward snapshots now build dated size, unit and investor history from
  2026-10-09.
- **G09, design:** open. The owner approved the fixed-view layout, and the agent reviewed the dated-view layouts.
- **G10, detector validity:** open. There is no measured evaluation; the per-date counts are descriptive.
- **Data rights:** unreviewed for TEFAS, KAP and MKK data. Nothing real is published.
- **Pitch facts to verify:** check SPK decision 52/1589 of 28 August 2026 against the bulletin before quoting it.
  B2B demand has no interviews, pricing test or letter of intent.

## Next recommended work

1. **Per-date estimated flow.** Write a new versioned protocol, committed alone before any calculation, that applies
   DEC-026's pre-recorded (M-2, M-1) rule.
2. **Windows test hygiene.** Make the root suite pass on Windows. The causes are a missing `tzdata`, CRLF test
   fixtures, the cp1252 console, SQLite file handles and `SO_REUSEADDR`. Start on the test side. The SQLite lock
   errors may involve the registered `evidence_store.py`, and changing that file needs an approved reseal.
3. **The owner's split decision.** It unblocks the sealed-test runner (slice E in the codex context) and any
   measured evaluation.

## Do not claim

Section 11 of the codex context still applies. In addition, the pitch and demo must not claim:

- that the dated view "caught", "warned about" or "would have flagged" a fund early, or any lead time;
- that the per-date counts are detection performance;
- that institutions want to buy the product (demand is a hypothesis);
- that SPK's reasons for the 17 September order are known.
