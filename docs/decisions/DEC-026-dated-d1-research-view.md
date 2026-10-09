# DEC-026 — Dated D1 research view over 12 preregistered dates

**Date:** 2026-10-10 (Europe/Istanbul)
**Source:** answers in chat on 2026-10-09:
- build the D1-only dated view now and make it demo-ready on Saturday night;
- use the 12 month-end dates;
- push one new branch to origin;
- develop in a separate clone that keeps LF line endings.

## Decision

| Item | Choice |
|---|---|
| Dates | 12: the last shared-calendar TEFAS date of each month from October 2025 to August 2026, plus the preregistered window end 2026-09-16 (the default) |
| Range | [2025-10-06, 2026-09-16]; no earlier dates and no post-order dates |
| Findings | D1 only. Estimated flow and concentration are shown as "Bu tarih görünümünde hesaplanmadı." |
| Names and categories | Snapshot rows retrieved at or before the D1 calibration run (2026-10-07T08:52:12Z) |
| Serving | A separate loopback API and launcher, with `/dates` pages; the fixed-date app is unchanged |
| Control | List page only: a native select plus "Tarihi göster" |
| Branch | `claude/dated-d1-view`. Pushing this branch is authorized; merging or opening a PR needs a further decision |
| Merge | Merge commit only, never a squash |
| Development/test split | Per-date D1 over the 100 opened funds is development exploration; no unopened file is read |
| Sealing | Only on a machine that holds the private archive, in an LF checkout, after this decision, the protocol and the runtime are committed |

The rules are in
`research/events/2026-09-17-spk-liquidations/fund_review_dated/PROTOCOL.md`.

## Pre-recorded rule for a later flow amendment

Nothing here computes flow; using this rule needs its own versioned protocol.

For a cutoff in month M, the flow pair is the calendar pair (M-2, M-1):

- one monthly (AB) report for each of the two months;
- both published at or before the cutoff;
- the same pair for every fund;
- no substitution of an earlier pair and no publication allowance;
- never a weekly report.

Every grid date falls at least 16 days after the previous month end, and recorded
publication lags are 2-10 days. At 2026-09-16 the rule gives the fixed view's
July/August pair.

## Deviations carried over from the fixed view

The dated view still uses a recorded-date filter instead of FR-109 replay. Bundles
are identified by a content fingerprint instead of a registered UUID. Timestamps use
+03:00 offsets instead of UTC. The universe and categories are current ones. These
remain research-contract exceptions.

## Unchanged

DEC-024's scope and DEC-025's limits. G01, G03, G09 and G10 stay open. The TRY 5,000
ceiling is not spending authorization. All 284 requirement statuses stay
NOT_IMPLEMENTED. The frozen detector files, the handoff, and the v1 and v2 runtime
are untouched.
