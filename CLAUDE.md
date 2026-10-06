# Project 50K — Claude Code entry

## Current scope: DEC-024 (2026-10-06)

Read `docs/decisions/DEC-024-turkish-funds-first.md` before any task. The active scope is **Turkish investment funds only**. BIST, crypto, US equities and on-chain are postponed, not dropped.

The handoff instructions imported below, and the handoff's own `CLAUDE.md`, `START_HERE.md`, `PRODUCT.md`, `research/USER_DECISIONS_2026-10-02.md` and docs 04, 21, 22, 23 and 25, say the four-market/on-chain target is binding and that a reduced target is not approved. DEC-024 supersedes those statements. Everything else in the handoff still applies: the TRY 5,000 cumulative ceiling, no service accounts, G01 open, the integrity rules, and all 284 requirement IDs `NOT_IMPLEMENTED`.

## Repository layout

- `docs/handoff-v0.5/` is the frozen v0.5 handoff. Do not edit it; its `MANIFEST.json` hashes verify it. Paths in the imported instructions below are relative to that folder.
- Record new owner decisions in `docs/decisions/` and working notes in `docs/notes/`.
- Before copying code from Safa675/bist-quant, read `docs/notes/bist-quant-reuse.md`.
- Before building any TEFAS adapter or fund detector, read `research/spikes/2026-10-06-tefas/REPORT.md`: it records which TEFAS fields are dated and which are placeholders.
- Backend code lives in `services/p50k/`; tests in `tests/unit/`. Run them from the repo root with `PYTHONPATH=services python -m unittest discover -s tests -t . -v`.

## Handoff instructions

@docs/handoff-v0.5/AGENTS.md
