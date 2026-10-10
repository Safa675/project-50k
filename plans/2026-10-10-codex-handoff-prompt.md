# Codex handoff prompt: BlackSwan (Project 50K), 2026-10-10 about 14:35 Istanbul

Start Codex in `C:\Users\mirza\Desktop\Hackathon\project-50k`, then paste the prompt below.

**Machine:**
- Windows 11, with Git Bash and PowerShell.
- Docker 29.8, Compose v5.5.1 and WSL2.
- Node 24.14.1 and uv 0.12.17.
- Python: `.venv\Scripts\python.exe`. The bare `python` is the Microsoft Store stub.

---

## Prompt

You are taking over Project 50K, whose product name is **BlackSwan**, from Claude Code in the middle of Startup
Weekend Urla. Features freeze on Sunday 2026-10-11 at 10:30 and code freezes at 13:00 (Istanbul). Your user is
Mirza, the technical lead; reply in clear, concise English. **Nothing may be lost: read before you act.**

### 1. Read first, in this order

1. `AGENTS.md`, the binding rules for coding agents.
2. `docs/notes/current-state.md`, `docs/notes/team-asks.md` and `docs/notes/product-direction.md`.
3. `docs/decisions/DEC-024` to `DEC-030`:
   - DEC-028: the deploy-ready, AI-native build;
   - DEC-029: every fund opened;
   - DEC-030: the BlackSwan name and the working agreements.
4. `plans/2026-10-10-product-build-plan.md`, the build plan, confirmed by delegation under DEC-030. Read sections 2
   (decisions D1–D14), 3, 6, 7, 10 (timeline) and 11 (todo list).
5. `docs/notes/research-2026-10-10/`: the research behind the plan. It covers the code inventory, specs mapping, data
   sources, regulation, runtime design, the TradingAgents study and design, and two adversarial reviews of the plan.

### 2. Hard rules

Claude Code's hooks do not protect you, so follow these by hand.

**Files and data**
- **Never edit:**
  - `docs/handoff-v0.5/**`;
  - any committed `PROTOCOL.md` or `PREREGISTRATION.md`;
  - `research/events/2026-09-17-spk-liquidations/price_detectors/{detectors.py,PREREGISTRATION.md,results.json}`;
  - anything under `raw/`.
- **Never edit files bound into the sealed demo bundles**, or the live demo answers 503:
  - every path in `tests/unit/registered_sources.lock.json`;
  - `services/p50k/research_reviews/dated_*.py`;
  - the event's `run.py` runners;
  - `top100_funds.txt`.

  Put new code in new modules that import these read-only.
- **Real data stays out of git.** That means no real TEFAS or KAP values and no fund names except THF, TP2, TLY, DFI,
  DOH, PRY, KHA and PNU. Tests use synthetic data.
- **Leak scan before every commit.** Exit code 1 or 2 blocks the commit:
  `$env:P50K_RAW_DIR='C:\Users\mirza\Desktop\Hackathon\project-50k\raw'; $env:PYTHONUTF8='1'; .venv\Scripts\python.exe .claude\skills\p50k-leak-scan\leak_scan.py`.

**The live demo**
- The main checkout is load-bearing for the demo. Do not:
  - switch its branch;
  - pull changes that touch registered files;
  - touch `raw/snapshots/fund_snapshots.sqlite3`.
- Build in the separate git worktree (plan D1): `C:\Users\mirza\Desktop\Hackathon\project-50k-app`, branch
  `product/build`.
- The demo itself runs from `C:\Users\mirza\Desktop\Hackathon\project-50k-dated`, on 127.0.0.1:3060 (web), 8767 (fixed
  API) and 8768 (dated API). Never stop it, and never run `npm run build` in that clone.
- To restart it, from that clone run:
  `powershell -ExecutionPolicy Bypass -File .claude/skills/p50k-demo/start-demo.ps1 -Restart`.

**Git**
- Merge commits only (`git merge --no-ff`). Never squash, rebase-merge, force-push or delete remote branches.
- Never run `git add -f`, `git clean -x/-X` or `git stash --all`.
- Safa (the repository owner) only pulls.
- A pull into the main checkout is safe only if `git diff --name-only` shows no registered path.

**Product**
- **No placeholders (DEC-030):** no lorem ipsum, fake values, "coming soon" screens, blank template rows, mock AI
  output or notes to the team. If something cannot be done properly, tell Mirza.
- **These are not placeholders, and they stay:**
  - the required integrity labels: data mode, "geliştirme sonucu", "veri hakları incelenmedi", "yatırım tavsiyesi
    değildir";
  - real empty, error and stale states;
  - the plain-text "BlackSwan" wordmark until Mirza's logos arrive;
  - the current research-app colours and fonts until Barış's design system arrives.

  If Mirza says he would rather not show any of these, follow him.
- **AI (DEC-028):**
  - Detectors compute every number.
  - The OpenAI model chooses only among options the server allows. It never writes numbers, and it cites evidence
    IDs.
  - All AI text passes the validator before it is shown.
  - Decisions are append-only, with human override.
  - Chat tools are read-only.
  - No fraud, advice or prediction wording.
- **API budget:** $25 is a target, not a hard cap. Don't waste it; raise it only with a valid reason and Mirza's OK.
  The internal $20 cap and its buckets (plan section 6) apply.

**Secrets and outside actions**
- Mirza puts the OpenAI key in the worktree's gitignored `secrets/openai_api_key`. Never read, print or log `.env*` or
  `secrets/`, and use `docker compose config --no-interpolate`.
- Spending, new accounts, deployment and contacting third parties need explicit authorization from Mirza or Safa.

**Working with Mirza**
- **Persistent reminders (DEC-030):** if Mirza has not answered a question or confirmed information that affects
  everything, raise it again in every reply until he does. Only for truly critical items.
- Confirm plan items yourself when they serve the team's interest. Ask Mirza only about problematic ones, with clear
  options and your recommendation.
- Never report a test as passed that you did not run.

### 3. State at handoff (2026-10-10, about 14:35)

**Repository.** `main` is pushed, with nothing uncommitted. Merged today:
- the dated D1 view;
- agent tooling (`.claude/` skills, hooks and rules);
- DEC-028/029/030;
- the plan and the research.

**Running now:**
1. **The live demo** (section 2).
2. **The all-fund TEFAS snapshot download,** started 14:30.
   - It collects 2,136 funds, about 4,272 requests at 1.5 s pacing, so roughly 2–3 hours.
   - Output: `%USERPROFILE%\.local\share\project-50k\overnight\2026-10-10\snapshots-all.sqlite3`, with its log in
     `snapshots-all.log` in the same folder.
   - Mirza's laptop must stay on and online until it finishes. Check the log; if it stopped early, rerun it.
   - Mirza wants downloads started as soon as they can run (DEC-030), not held for the night.
   - It is restartable: rerun the same command, and dated rows already stored are kept. From the main checkout:
     `$env:PYTHONDONTWRITEBYTECODE='1'; $env:PYTHONPATH='services'; .venv\Scripts\python.exe -m p50k.jobs.fund_snapshots --db "$HOME\.local\share\project-50k\overnight\2026-10-10\snapshots-all.sqlite3"`

**Scheduled.** The Windows task "P50K fund snapshots" runs weekdays at 21:00 into
`fund_snapshots_forward.sqlite3`. Its first run is Monday 2026-10-12.

**Data.**
- `raw/tefas/prices`: 2,022 files with 1,673,412 non-null prices, 2021-10-07 to 2026-10-07.
- The forward snapshot database: 1,071 funds as of 2026-10-09.
- KAP: 106 fund folders, 1,342 PDFs and 101 parsed series.
- The SPK bulletin 2026/61, and `liquidated_funds.json` (131 funds).
- `raw/tefas/responses/`: the 2026-10-06 all-fund list, whose `fonTurAciklama` field is the plan's single category
  source.

**Not built yet:** the BlackSwan product itself: the worktree, compose stack, PostgreSQL, API, worker, AI layer and
web app.

### 4. Ask Mirza first

Ask these clearly, each with its recommendation (in brackets), and record his answers. D7 goes into DEC-031.

1. **D7: what data may go to OpenAI?**
   - [Recommended: derived evidence only.]
   - **Sent:** detector values, thresholds and states; dates; categories; public fund codes and names; SPK event
     metadata and short quotes.
   - **Not sent:** raw price series; TEFAS size, units and investor counts; KAP text; personal data.
   - Calls use `store: false`, and users are told that chat questions go to OpenAI.
   - Until he answers, AI runs only in mock mode, in the development database.
2. **D9: what else may download?** The all-fund snapshot is already running. Each item below writes only to the
   overnight folder.
   - (a) TEFAS fund profiles: needs a small fetcher; about 1 hour at 1.5 s.
   - (b) SPK bulletin PDFs for 2024–2026: needs a downloader; about 230 files, roughly 25 minutes at 6 s.
   - (c) Optional, overnight: KAP report lists for about 970 more funds; 6 s pacing, about 3–7 hours. The machine must
     stay on, with sleep off and Windows Update paused.
   - [Recommended: (a) and (b) this afternoon; (c) only if the machine can stay on.]
3. **D1:** build in the separate worktree folder `project-50k-app`, which Mirza opens in VS Code? [Yes.]
4. **T1.7a:** one closest-name match in the 2026/61 fund mapping needs Mirza's check before the events are marked
   `CONFIRMED`. Show him that fund and its match.

Also pending, from `docs/notes/team-asks.md`:
- Safa: the story pick by about 22:00 (the build defaults to B2B at 23:00), plus his other asks.
- Barış: design tokens by 23:00; logos and designs later.

### 5. Then build: plan Phase 1, in this order (plan sections 10 and 11)

1. Pre-pull the pinned images: `postgres:18.6`, `python:3.13-slim`, `node:24-slim` and uv.
2. **T1.1:**
   - the worktree;
   - a deny-all `.dockerignore`;
   - ignores for `secrets/`, `backups/`, test output, `*.sqlite3`, `*.dump` and `compose.override.yaml`;
   - the `secrets/` folder.
3. **T0.2:** Mirza puts the key in `secrets/`.
4. **T1.3:** a `product` extra, locked: `openai` 3.28.0, `psycopg[binary,pool]` 3.3.x, `argon2-cffi` 25.1.0. Verify
   the versions on PyPI.
5. **T1.4:** plain SQL migrations.
   - Schemas: `ref`, `obs`, `det`, `ai`, `auth`, `b2b` and `ops`.
   - An owner role and the `p50k_app` role.
   - Append-only triggers on the AI and evidence tables.
   - A small migration runner.
6. **T1.2:** compose.
   - The `postgres:18.6` volume mounts at `/var/lib/postgresql`.
   - Ports 127.0.0.1:3070, 8770 and 5433.
   - Host binds go in `compose.override.yaml`.
   - Run the proxy, cookie, CSRF and server-sent-events check.
7. **T1.5:** settings and redacting logs.
8. **T1.7:** the `import-archive` CLI, through staging tables with `ON CONFLICT DO NOTHING`. Verify the row counts.

**Milestone M1, by 17:30:** the archive is in PostgreSQL and its row counts match.

Then Phase 2:
- the v2 detector protocol, committed **alone** before any computation;
- `run-detectors`;
- the API;
- the overnight runners.

Then Phase 3:
- login;
- the OpenAI wrapper with caps;
- egress;
- the validator;
- decisions;
- the review queue;
- the web app.

All of these follow the plan, which also lists the work moved after the freeze and the never-cut items.

**Verification.**
- Run the Python suites in a WSL2 clone, to avoid the known Windows-only failures, and keep a baseline of failing test
  names.
- Keep the research suites green.
- Report exact commands and results.

**After each block of work:**
1. Update `docs/notes/current-state.md` and `docs/notes/team-asks.md`.
2. Commit on a branch.
3. Merge into `main` with `--no-ff`, then push.

**Carried over, never drop:**
- K1: per-date estimated flow;
- K2: the Windows research-suite fixes;
- K3: the forward snapshot task;
- K4: decoupling the demo from the main checkout after the event;
- K5: the do-not-claim list in `docs/notes/current-state.md`;
- K6: the after-event research list.
