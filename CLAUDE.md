# Project 50K — Claude Code entry

## Current scope: DEC-024 (2026-10-06)

Read `docs/decisions/DEC-024-turkish-funds-first.md` before any task. The active scope is **Turkish investment funds only**. BIST, crypto, US equities and on-chain are postponed, not dropped.

The handoff instructions imported below, and the handoff's own `CLAUDE.md`, `START_HERE.md`, `PRODUCT.md`, `research/USER_DECISIONS_2026-10-02.md` and docs 04, 21, 22, 23 and 25, say the four-market/on-chain target is binding and that a reduced target is not approved. DEC-024 supersedes those statements. Everything else in the handoff still applies: the TRY 5,000 cumulative ceiling, no service accounts, G01 open, the integrity rules, and all 284 requirement IDs `NOT_IMPLEMENTED`.

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

`.claude/` holds project skills (`/p50k-verify`, `/p50k-leak-scan`, `/p50k-demo`, `/p50k-seal-dated`, `/p50k-new-research-slice`), path-scoped rules and hooks. The hooks block file-tool edits and common shell writes or deletions of frozen files, `raw/` and files bound into sealed bundles, block force pushes, squash merges and staging private data, and report protected files that changed anyway. They are heuristics, not a boundary. See `docs/notes/agent-tooling.md`, including why there is no MCP server. External actions (spending, accounts, deployment, installing the Linux snapshot timer, contacting third parties) need the owner's say-so; DEC-027 records what the team may do on its own machine. Reply in the language of the person you work with (the owner prefers simple, short Turkish); code, commits and docs stay in English.

## Handoff instructions

@docs/handoff-v0.5/AGENTS.md
