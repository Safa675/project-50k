# Project 50K — Claude Code entry

## Current direction: DEC-028 and DEC-029 (2026-10-10)

- **Team.** Mirza is the technical lead: all development and data gathering. Safa is the business person and repository owner; he only pulls. Barış designs the pitch deck and the website's design system.
- **Build target.** A deploy-ready full-stack product (frontend, backend, PostgreSQL, worker, all connected) that runs on localhost with real data. It is not deployed. Code freeze: Sunday 2026-10-11 13:00.
- **AI-native, never forget.**
  - An LLM (OpenAI API, Mirza's key in a gitignored `.env`, $25 limit) decides responsibly from deterministic detector evidence, and users chat with it in the UI.
  - Detectors compute every score.
  - Every LLM decision is stored with its evidence, and a human must be able to override it.
- **Stack.** Plain PostgreSQL with the product's own email/password auth, in Docker.
- **Data.** Every downloaded fund is open for product use (DEC-029); every detector figure is a development result.
- **Specs.** The handoff's product requirements and earlier product decisions are guides, not hard rules: raise important collisions with Mirza, or with Safa, Barış or the team when it is their call. The integrity rules stay binding.
- **DEC-030 working agreements (2026-10-10).**
  - The product is called **BlackSwan**; Mirza will supply logos and designs.
  - **No placeholders** in the product: no lorem ipsum, fake values, "coming soon" screens, blank template rows, mock AI output or notes to the team. Messages for Mirza go in chat. Required integrity labels are real content, not placeholders.
  - **The $25 OpenAI budget is a target, not a hard cap.** Don't waste it; raise it only with a valid reason and Mirza's OK.
  - **The plan is confirmed by delegation.** Confirm items that serve the team's interest yourself; ask Mirza only about problematic ones, with clear options and a recommendation.
  - **Persistent reminders.** If Mirza misses something important (an unanswered question or unconfirmed information that affects everything), raise it again in every reply until he answers. Only for truly critical items.
- **Codex handoff (newest):** `plans/2026-10-11-codex-handoff-prompt.md` holds the full state, open workstreams and next steps as of 2026-10-11 10:40; specs are in `plans/2026-10-11-sprint-briefs.md`. The 2026-10-10 handoffs are history.
- **Read before product work:**
  - `docs/notes/product-direction.md` (insurance policies or B2B anomaly data; still open);
  - `docs/notes/team-asks.md` (open asks: add yours);
  - the current plan in `plans/`.

## Current scope: DEC-024 (2026-10-06)

Read `docs/decisions/DEC-024-turkish-funds-first.md` before any task. The active scope is **Turkish investment funds only**. BIST, crypto, US equities and on-chain are postponed, not dropped.

The handoff instructions imported below, and the handoff's own `CLAUDE.md`, `START_HERE.md`, `PRODUCT.md`, `research/USER_DECISIONS_2026-10-02.md` and docs 04, 21, 22, 23 and 25, say the four-market/on-chain target is binding and that a reduced target is not approved. DEC-024 supersedes those statements. Everything else in the handoff still applies as a guide (DEC-028): the TRY 5,000 cumulative ceiling, no service accounts beyond the OpenAI key DEC-028 authorizes, G01's status as recorded in DEC-027, the integrity rules (binding), and all 284 requirement IDs `NOT_IMPLEMENTED` until delivered and tested.

## Repository layout

- `docs/handoff-v0.5/` is the frozen v0.5 handoff. Do not edit it; its `MANIFEST.json` hashes verify it. Paths in the imported instructions below are relative to that folder.
- Record new owner decisions in `docs/decisions/` and working notes in `docs/notes/`.
- Before copying code from Safa675/bist-quant, read `docs/notes/bist-quant-reuse.md`.
- Before building any TEFAS adapter or fund detector, read `research/spikes/2026-10-06-tefas/REPORT.md`: it records which TEFAS fields are dated and which are placeholders.
- The daily TEFAS snapshot job is `services/p50k/jobs/fund_snapshots.py`. Its data lives in `~/.local/share/project-50k/`, outside git; never commit real TEFAS or KAP values (data rights not reviewed). Schedules are in `ops/systemd/` (Linux) and `ops/windows/`; the team's Windows machine collects into a separate `fund_snapshots_forward.sqlite3` (DEC-027).
- Where the project stands, what is decided and open, and what to do next: `docs/notes/current-state.md`. The detailed 2026-10-07 record (data-source facts, case study, evaluation rules) is `docs/notes/codex-context-2026-10-07.md`. Codex reads the root `AGENTS.md`; change it together with this file so they never disagree.
- Backend code lives in `services/p50k/`; tests in `tests/unit/`. Run them from the repo root with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/bin/python -m unittest discover -s tests -t . -v` (Windows: `.venv/Scripts/python.exe`; the bare `python` there is usually the Microsoft Store stub). `/p50k-verify` runs every suite and separates known Windows platform failures from regressions.
- Dated D1 view: [DEC-026](docs/decisions/DEC-026-dated-d1-research-view.md) and `research/events/2026-09-17-spk-liquidations/fund_review_dated/PROTOCOL.md` (frozen once a real date index is sealed). Event-weekend rules are in [DEC-027](docs/decisions/DEC-027-event-weekend-operations.md): the owner only pulls; merge with merge commits only, never squash or force-push, so protocol commits stay in `main`'s history.

## Agent tooling

`.claude/` holds project skills (`/p50k-meta` for persisting new context and keeping instructions consistent, `/p50k-verify`, `/p50k-leak-scan`, `/p50k-demo`, `/p50k-seal-dated`, `/p50k-new-research-slice`), path-scoped rules and hooks. When the user gives new context, decisions or preferences, run `/p50k-meta` before continuing. The hooks block file-tool edits and common shell writes or deletions of frozen files, `raw/` and files bound into sealed bundles, block force pushes, squash merges and staging private data, and report protected files that changed anyway. They are heuristics, not a boundary. See `docs/notes/agent-tooling.md`, including why there is no MCP server. External actions (spending, new accounts, deployment, installing the Linux snapshot timer, contacting third parties) need explicit authorization from Mirza or Safa. DEC-028 authorizes the OpenAI key with a $25 limit, and DEC-027 the forward snapshots on the team's machine. Reply in the language of the person you work with: Mirza wants concise English; Safa prefers simple, short Turkish. Code, commits and docs stay in English.

## Handoff instructions

@docs/handoff-v0.5/AGENTS.md
