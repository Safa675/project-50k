# DEC-024 — Turkish funds first; other markets postponed

**Date:** 2026-10-06 (Europe/Istanbul)
**Source:** owner answers in chat, 2026-10-06:
- "we could limit the product with just funds at this point."
- On crypto, US equities and on-chain: "they should be postponed. first priority should be turkish funds."

This is a user-confirmed product decision. Under the handoff's authority order (`docs/handoff-v0.5/AGENTS.md`, "Authority and scope"), it ranks above earlier decision records and the v0.5 research.

## Decision

| Item | Status |
|---|---|
| Turkish investment funds (TEFAS) | **Active.** The only market in the current phase. |
| BIST equities | **Postponed.** Recorded as postponed because the owner said to limit the product "with just funds"; BIST was not named separately. |
| Crypto | **Postponed**, not dropped. |
| US equities | **Postponed**, not dropped. |
| On-chain | **Postponed**, not dropped. |

Postponed means: requirement IDs, anomaly entries, contracts, research and gates for those markets are retained unchanged and are not deleted or renumbered. They are not part of current implementation, demo or acceptance until a later owner decision brings them back.

## What this supersedes

DEC-019 (four-market weekend target with meaningful on-chain) for the current phase. Wherever the handoff says the four-market/on-chain target is binding, or that a reduced target is not approved, DEC-024 takes precedence. That wording appears in `AGENTS.md`, `CLAUDE.md`, `START_HERE.md`, `PRODUCT.md`, `research/USER_DECISIONS_2026-10-02.md` and docs 04, 21, 22, 23 and 25. The handoff files are left unedited as a historical snapshot.

## What does not change

- **DEC-018 / G01:** no organizer ruling exists; competition use of prepared material remains unresolved.
- **DEC-020:** TRY 5,000 cumulative project ceiling, excluding development Claude/Codex subscriptions; no service accounts; the ceiling does not by itself authorize any spend.
- All integrity rules in `AGENTS.md`: published-cadence NAV only, borsapy history placeholders are missing (DEC-003), evidence strength is not probability, no buy/hold/sell or personalized recommendation, source and timestamp transparency, honest replay/synthetic labeling.
- All 284 requirement IDs remain `NOT_IMPLEMENTED`.

## Anomaly catalog under DEC-024

Phase labels are the catalog's own (`docs/handoff-v0.5/docs/12_Anomaly_Catalog.md`). This table only sorts entries by market; it does not change any phase, method or threshold.

**Active in the funds phase (9):**

| ID | Name | Catalog phase | Main dependency |
|---|---|---|---|
| AN-FND-004 | Asset-type allocation shift | CORE | Dated allocation snapshots (G03) |
| AN-FND-005 | Fund access/regulatory event | CORE | Fund disclosures with entity validation |
| AN-FND-001 | Fund NAV/category divergence | NEXT | Dated category membership, at least 10 eligible peers |
| AN-FND-002 | Return-adjusted net-flow estimate | CONDITIONAL | Dated AUM history; the inspected borsapy history path has placeholders |
| AN-FND-003 | Investor count change | CONDITIONAL | Dated investor-count history; same placeholder issue |
| AN-EVT-004 | Source correction/material update | CORE | Versioned fund disclosures and data revisions |
| AN-DQ-001 | Stale or failed source | CORE | Source schedule |
| AN-DQ-002 | Missing/placeholder/invalid observation | CORE | Placeholder normalization |
| AN-DQ-003 | Corporate-action/session break | CORE | Applies where fund baselines break (for example unit changes or mergers); fund-specific rules are not yet written |

**Still LATER (2):** AN-FND-006 reported holding concentration, AN-FND-007 potential liquidity mismatch.

**Postponed with their markets (17):** AN-MKT-001 to 007, AN-EVT-001 to 003, AN-ONC-001 to 005, AN-CMP-001, and AN-CMP-002 (it needs BIST market data).

## Release gates under DEC-024

- **G03 Fund history** becomes the critical data gate for the active scope.
- **G02 BIST rights**, **G04 other feeds** and **G11 full cross-market scope** are not required for the current phase; they return with the postponed markets.
- G01 and G05 to G10 are unchanged.
- Publishing real fund data still requires scoped data rights, per `AGENTS.md`.

## Open follow-ups (not decided here)

- Whether to start forward daily collection of the latest fund snapshot (NAV, AUM, investor count, allocation) to build the dated history that AN-FND-002/003 need. The handoff allows storing latest detail as a snapshot but forbids backfilling unknown history. Any collector first needs the borsapy/TEFAS spike in `docs/handoff-v0.5/docs/10_Data_Requirements_and_Provider_Matrix.md` section 3.
- The exact fund universe for the first slice.
- Updated demo and pitch narrative (docs 04 and 23 still describe the four-market demo).
- When and in what order the postponed markets return.
