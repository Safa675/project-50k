# Open asks for the team

A living list of what the build needs from people, so nothing waits silently. Agents add an entry whenever they
need a decision or an action, and mark it done with the date and outcome. Mirza relays asks to Safa and Barış.
Newest first within each person. Times are Europe/Istanbul.

## Mirza (technical lead)

| Since | Type | Ask | Status |
|---|---|---|---|
| 2026-10-10 | Action | Refresh Figma design tools for all 22 supplied nodes | Installed/enabled verified; Mirza confirms Connected. Current long-running session has no callable Figma methods; session refresh required. Do not reinstall or send tokens |
| 2026-10-10 | Decision | Stocks are in product scope (DEC-032): include real stock support in the hackathon demo, or complete the historical fund case first and implement stocks next? | Closed 2026-10-10: Mirza requires stocks working in the hackathon demo. Implement new isolated stock support on resume; no claim it already works |
| 2026-10-10 | Action | Finish immediate work, then stop for alignment | Confirmed: finish current chat/import/documentation block, then pause until Mirza resumes; start no new feature now |
| 2026-10-10 | Decision | Read and confirm the build plan | Closed 2026-10-10: confirmed by delegation (DEC-030); agents ask only about problematic items |
| 2026-10-10 | Decision | D1: build in the separate worktree folder `C:\Users\mirza\Desktop\Hackathon\project-50k-app` (opened in VS Code), because the main checkout feeds the live demo | Closed 2026-10-10: Mirza confirmed; worktree created on `product/build` |
| 2026-10-10 | Action, after T1.1 creates the worktree | Put the OpenAI API key in the worktree's gitignored `secrets/openai_api_key` (never in chat or git), and configure budget alerts | Key supplied and runtime model/decision/chat smoke passed; on-demand AI live. Budget-alert configuration still open. DEC-030 keeps $25 a target and the internal $20 cap |
| 2026-10-10 | Decision | D7: only derived evidence goes to OpenAI (detector values, dates, categories, public fund codes and names, SPK metadata and short quotes). No raw series, TEFAS size/units/investors, KAP text or personal data | Closed 2026-10-10: Mirza approved; recorded in DEC-031. Safa's answer remains open |
| 2026-10-10 | Decision | D9: profiles, SPK bulletin PDFs 2024–2026 and additional KAP report lists; all output in the external overnight folder | Closed 2026-10-10: Mirza authorized all three, confirmed the laptop stays on, and requested immediate starts. Preserve one paced stream per host |
| 2026-10-10 | Action | Relay the Safa and Barış asks below | Open |
| 2026-10-10 | Action, by 17:00 | T1.7a: check the 2026/61 fund mapping (the closest-name match and 10 exact matches) before the events are marked confirmed | Closed 2026-10-10: closest identity human-confirmed; Mirza authorized ten independent exact checks, all passed against the list and official PDF. 131 confirmed versions appended; unknown publication time still prevents triggers |
| 2026-10-10 | Action, before 21:00 | T4.0: prepare the machine for the overnight jobs (AC power, sleep set to Never, Windows Update paused until Monday, Docker Desktop starting at login); check the logs at 07:00 | Open |

## Safa (business, repository owner)

| Since | Type | Ask | Status |
|---|---|---|---|
| 2026-10-10 | Decision, Saturday evening after the mentor meetings (original deadline 22:00) | Headline story and final business plan: insurance or B2B | Story closed 2026-10-10 by Mirza: B2B evidence data/API via an agent workflow for banks and financial institutions (DEC-032). Insurance permanently deferred; detailed commercial plan still open |
| 2026-10-10 | Decision | Insurance details: trigger scope, payout shape, policyholder and channel | Deferred permanently with insurance by DEC-032; historical ask retained, no active implementation |
| 2026-10-10 | Decision | B2B buyer and revenue model; first institutional workflow, pilot and pricing | Buyer class and revenue direction closed 2026-10-10 (DEC-032): banks/financial institutions, evidence data/API access. Exact workflow, pilot, price and demand validation remain open |
| 2026-10-10 | Decision | Which banks or financial institutions may be named in the pitch, and with what wording (no implied partnership). The default is to name no institution | Open |
| 2026-10-10 | Decision | Disclaimer wording for the insurer-review print view and real-fund use of that print view; B2B naming | Insurer-review print view deferred permanently by DEC-032. Product name is BlackSwan (DEC-030); B2B copy still requires descriptive evidence wording and the existing integrity labels |
| 2026-10-10 | Decision | Agree with D7 (only derived evidence goes to OpenAI)? | Open |
| 2026-10-10 | Action | Share the data sources he found (links or files) and their terms | Open |
| 2026-10-10 | Action, optional | Copy his full 2026-10-06 snapshot database (2,133 funds) to Mirza privately, not through git | Open |
| 2026-10-10 | Check, after the event | Capital-markets opinion (6362, SPK investment advice) and commercial data-rights routes (MKK for KAP, Takasbank for TEFAS, entitled stock feeds). Real data remains on localhost until reviewed | Open. Insurance-law work is deferred with insurance (DEC-032); B2B direction is not redistribution authorization |
| 2026-10-10 | Decision | May the product keep the UI primitives adapted from his Bilun project (`frontend/BILUN-NOTICE.txt`, "all rights reserved"), or should Barış's components replace them? | Open |
| 2026-10-07 | Decision | Development/test split | Closed 2026-10-10: Mirza opened all funds (DEC-029) |

## Barış (design)

| Since | Type | Ask | Status |
|---|---|---|---|
| 2026-10-10 | Action, by Saturday 23:00 (otherwise the current tokens ship) | The design system as values: colours, typography, spacing, radii, shadows and component states (a Figma variables export, or a style guide with the values written on it) | Open: Mirza promises the design system soon; existing tokens remain until received |
| 2026-10-10 | Action | The screens he is designing, as exports or a viewable Figma link; the product name and logo to show | Open: Mirza promises logos soon; BlackSwan text wordmark remains until received |
| 2026-10-10 | Decision | Whether a public landing page (with no real data) is wanted beside the login-protected app | Open |

## Team

| Since | Type | Ask | Status |
|---|---|---|---|
| 2026-10-10 | Decision | The product name | Closed 2026-10-10: **BlackSwan** (DEC-030); Mirza supplies logos and designs later |
| 2026-10-10 | Decision | Pitch wording within the do-not-claim list in `docs/notes/current-state.md` | Open |
