# DEC-025 — Pitch B2B fund-risk monitoring; scope stays on funds

**Date:** 2026-10-09 (Europe/Istanbul)
**Source:** answer in chat, 2026-10-09: "Pitch B2B on funds", meaning a pitch built
around fund-risk and disclosure monitoring for distributors and compliance teams.
The alternatives were staying B2C on funds and pivoting to B2B on BIST stocks.

## Decision

- The Startup Weekend pitch presents the product as fund-risk and disclosure
  monitoring for fund distributors (brokerages, fintech apps, advisers) and their
  compliance teams. Retail investors stay the end users wherever a distributor
  embeds the product (B2B2C).
- The scope stays Turkish investment funds (DEC-024). BIST stocks stay postponed. A
  stock product for institutions would be licensed non-display use under a Borsa
  Istanbul Data Distribution Agreement; its fees exceed the TRY 5,000 ceiling, and
  licensing takes longer than the event.

## Evidence considered on 2026-10-09

- Institutions are heavily involved in funds:
  - Banks and brokerages distribute funds through TEFAS.
  - The largest portfolio management companies are bank-owned.
  - MKK's VAP screen of 2026-10-02 counts about 221,000 institutional fund
    investors, against about 15,000 institutional direct equity investors
    (`docs/handoff-v0.5/research/problem_market/TURKEY_MARKET_EVIDENCE.md`). These
    are headcounts, not assets.
- SPK's order of 17 September 2026 stopped purchases and redemptions in 131 funds
  through every distribution channel, affecting 455,758 investors
  (`docs/handoff-v0.5/research/problem_market/OFFICIAL_INCIDENT_CASES.md`).
  Distributors handled the fallout.
- Press and compliance-firm summaries report an SPK decision of 28 August 2026
  (52/1589) that adds weekly KAP portfolio reports for TEFAS-traded free funds and
  MKK announcements when one holder crosses 30-90% of a fund. Verify this against
  the SPK bulletin before quoting it.
- Borsa Istanbul's data FAQ requires a signed Data Distribution Agreement for
  non-display use (https://www.borsaistanbul.com/sss/veri-dagitim-ve-endeks-lisanslama,
  read 2026-10-09).

## Limits

- Demand is unvalidated: there are no buyer interviews, no pricing test and no
  letter of intent. Pitch B2B demand as a hypothesis to test, not as a fact.
- Data rights for TEFAS, KAP and MKK data in a B2B product are not reviewed. Real
  data is not published.
- Conflict of interest: banks own many of the funds they distribute. Disclose it
  and review it before any issuer- or distributor-funded model.
- Agents do not contact institutions without explicit authorization.

## Unchanged

DEC-024's scope. G01, G03, G09 and G10 stay open. The TRY 5,000 ceiling is not
spending authorization. All 284 requirement statuses stay NOT_IMPLEMENTED.
