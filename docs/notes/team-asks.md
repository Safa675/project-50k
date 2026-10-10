# Open asks for the team

A living list of what the build needs from people, so nothing waits silently. Agents add an entry whenever they
need a decision or an action, and mark it done with the date and outcome. Mirza relays asks to Safa and Barış.
Newest first within each person. Times are Europe/Istanbul.

## Mirza (technical lead)

| Since | Type | Ask | Status |
|---|---|---|---|
| 2026-10-10 | Decision | Read and confirm the build plan, `plans/2026-10-10-product-build-plan.md`: decisions D1–D14 (D12 is the TradingAgents-inspired agent team), the timeline and the after-freeze list | Open |
| 2026-10-10 | Action, after T1.1 creates the worktree | Put the OpenAI API key in the worktree's gitignored `secrets/openai_api_key` (never in chat or git), and set a $25 hard limit with alerts on the OpenAI project | Open |
| 2026-10-10 | Decision | D7: only derived evidence goes to OpenAI (detector values, dates, categories, public fund codes and names, event text). No raw series, PDFs or personal data | Open |
| 2026-10-10 | Decision | D9: unattended overnight collection from public TEFAS, SPK and KAP endpoints at the agreed pacing, into new directories; keep the machine on | Open |
| 2026-10-10 | Action | Relay the Safa and Barış asks below | Open |
| 2026-10-10 | Action, by 17:00 | T1.7a: check the 2026/61 fund mapping (the closest-name match and 10 exact matches) before the events are marked confirmed | Open |
| 2026-10-10 | Action, before 21:00 | T4.0: prepare the machine for the overnight jobs (AC power, sleep set to Never, Windows Update paused until Monday, Docker Desktop starting at login); check the logs at 07:00 | Open |

## Safa (business, repository owner)

| Since | Type | Ask | Status |
|---|---|---|---|
| 2026-10-10 | Decision, Saturday evening after the mentor meetings (by 22:00; with no pick by 23:00 the build defaults to B2B) | Headline story and final business plan: insurance (as the trigger and evidence engine for a licensed insurer, possibly with a policy-writer agent that drafts a PDF for the insurer's review), B2B anomaly data, or both kept thin | Open |
| 2026-10-10 | Decision | Insurance details, if chosen: trigger scope (SPK-ordered TEFAS halts and liquidations; licence cancellations? price falls excluded), payout shape, policyholder (investor or a group policy through the distributor), channel (bank apps, or brokerage apps through an agency or broker partner) | Open |
| 2026-10-10 | Decision | B2B details, if chosen: the first buyer, and which decision our data changes for them; the revenue model hypothesis | Open |
| 2026-10-10 | Decision | Which institutions may be named in the pitch, and with what wording (no implied partnership). The default is to name no insurer | Open |
| 2026-10-10 | Decision | Disclaimer wording for the insurer-review print view; whether a print view about a real fund may appear in the live demo (localhost only); if B2B, a product name without "risk raporu" or "sinyal" | Open |
| 2026-10-10 | Decision | Agree with D7 (only derived evidence goes to OpenAI)? | Open |
| 2026-10-10 | Action | Share the data sources he found (links or files) and their terms | Open |
| 2026-10-10 | Action, optional | Copy his full 2026-10-06 snapshot database (2,133 funds) to Mirza privately, not through git | Open |
| 2026-10-10 | Check, after the event | Legal opinions on insurance law (5684, SEDDK) and capital markets (6362, SPK investment advice); data-rights routes (MKK for KAP, Takasbank for TEFAS). Until then the pitch frames us as a trigger and evidence provider and as descriptive risk data, never as an insurer or a signal seller | Open |
| 2026-10-10 | Decision | May the product keep the UI primitives adapted from his Bilun project (`frontend/BILUN-NOTICE.txt`, "all rights reserved"), or should Barış's components replace them? | Open |
| 2026-10-07 | Decision | Development/test split | Closed 2026-10-10: Mirza opened all funds (DEC-029) |

## Barış (design)

| Since | Type | Ask | Status |
|---|---|---|---|
| 2026-10-10 | Action, by Saturday 23:00 (otherwise the current tokens ship) | The design system as values: colours, typography, spacing, radii, shadows and component states (a Figma variables export, or a style guide with the values written on it) | Open |
| 2026-10-10 | Action | The screens he is designing, as exports or a viewable Figma link; the product name and logo to show | Open |
| 2026-10-10 | Decision | Whether a public landing page (with no real data) is wanted beside the login-protected app | Open |

## Team

| Since | Type | Ask | Status |
|---|---|---|---|
| 2026-10-10 | Decision | The product name shown in the app and the pitch ("Project 50K" is a codename; "İzvanta" is a proposal) | Open |
| 2026-10-10 | Decision | Pitch wording within the do-not-claim list in `docs/notes/current-state.md` | Open |
