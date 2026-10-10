# DEC-027 — Event-weekend operating decisions

**Date:** 2026-10-10 (Europe/Istanbul)
**Source:** answers in chat on 2026-10-10 during Startup Weekend Urla.

## Decisions

| Item | Decision |
|---|---|
| Repository writes | The owner makes no write operations on this repository until further notice. He pulls to see changes. The team and its agents carry out all write operations, and any step only the owner can take is named explicitly. |
| History | PR #6 was squash-merged. Its protocol-before-calculation commits were kept by the file-identical merge `3a56557` into `main` (pushed 2026-10-10, as with `2f73493`). |
| Merging | Merge commits only. Never squash, rebase-merge or force-push published history, so protocol commits stay in `main`'s history. The dated-view branch is merged into `main` after its real-data checks pass. |
| Competition use (G01) | The team's position is that only the idea existed before the event, and it considers the pitch eligible without asking the organizers. For the record, this repository has commits dated 2026-10-06 to 2026-10-09, before the event started; they are kept as they are. |
| Real data in the demo | The live demo uses the real archived TEFAS/KAP-derived data on the team's own machine and shows no mock or synthetic data. Data rights remain unreviewed. There is no public release, deployment or other publication of real data without further approval. |
| Demo setup | One local app on `127.0.0.1:3060` from the dated-view checkout, the fixed-date API on 8767 and the dated API on 8768, all loopback-only. |
| Layout reviews | The owner reviews B and C of DEC-026 are delegated to the agent. It reviews screenshots at 390, 768 and 1440 px. G09 stays open. |
| Forward snapshots | Daily TEFAS snapshot collection starts on the team's machine. It writes to a separate database, `~/.local/share/project-50k/fund_snapshots_forward.sqlite3`, which no sealed bundle reads. Only latest-value fields are collected; nothing is backfilled or published. |

## Unchanged

DEC-024 scope, DEC-025 limits and the DEC-026 protocol. The TRY 5,000 ceiling is not
spending authorization. All 284 requirement statuses stay NOT_IMPLEMENTED.
