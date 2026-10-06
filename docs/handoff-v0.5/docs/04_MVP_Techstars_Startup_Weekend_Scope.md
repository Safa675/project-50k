# Project 50K — MVP / Techstars Startup Weekend Scope

**Version:** 0.4 audit + owner decisions · **Date:** 2026-10-02
**Status:** specification; not implemented product functionality.

## Event and team
User-provided local materials describe Startup Weekend Urla, 9–11 October 2026, at Bilişim Vadisi İzmir Kampüsü. Three-person team: developer/BA, marketing/business development, and UI/UX/design. The published local schedule includes validation/mentoring and presentation preparation, not 54 uninterrupted coding hours.

The pasted application text says the startup idea must not previously have been worked on. Written organizer clarification is required before competition use of pre-event research/specifications/design/reference code. General Techstars information [S33] does not override this local condition. No competition-compliance guarantee is made by this package.

## Selected weekend target and implementation sequence
The owner selected the four-market demonstration on 2026-10-02: BIST, Turkish investment funds, crypto and US equities, including meaningful on-chain experience. Some pre-event preparation is authorized. No organizer ruling or service accounts exist; the total project ceiling is TRY 5,000, excluding Claude/Codex development accounts only. See research/USER_DECISIONS_2026-10-02.md.

Build a BIST intraday and fund-specific evidence loop first, sharing search, Google account, watchlist, AI, event detail, feeds, notifications and admin. Then complete the selected crypto/US/on-chain demonstration paths. This sequence is not owner acceptance of a reduced BIST+fund endpoint. Provider/network/data-mode feasibility and costs remain unverified.

| Layer | First execution objective | Acceptance boundary |
|---|---|---|
| Landing/design | Original responsive Turkish landing and asset/event system | Designer review; no fake customers or performance claims |
| Accounts | Google-only, public browsing, private watchlist and roles | Real auth/isolation tests, not front-end-only protection |
| BIST | 10–20 active showcase securities where permitted; completed bars and context | Intraday/venue/delay visible; numerical and temporal guards |
| Funds | 5–10 showcase funds with dated NAV/allocation/disclosures | No fabricated intraday NAV or AUM/investor histories |
| Intelligence | Simple numerical baseline + useful source-backed LLM investigation/chat | Citations, abstention, heuristic evidence score, no advice |
| Notifications | In-app core; email/digest after sender/rights/consent gates | Dry-run clearly marked; no synthetic/replay sends |
| Administration | Health/freshness, inspect events, pause, typed settings | Server role and audit |
| Demonstration | Frozen timestamp-correct replay + actual current fetch where allowed | No claim that synthetic fixtures are real historical proof |
| Crypto/US | Required demonstration paths; proposed 10–20 pairs / 5–10 US active, broader catalog possible | Actual licensed capabilities/modes; missing paths mean reduced delivery |
| On-chain | Required meaningful finalized on-chain evidence path; EVM+Solana proposed, exact networks after spikes | Source/time/finality/attribution limits visible; a decorative token tab or mock ownership label does not satisfy it |

75–100 crypto and 100–200 US names remain broader catalog targets, not promises of simultaneous live/on-chain coverage. A provider plan may impose lower limits. A reduced showcase is not equivalent to full implementation of all original P0 requirements.

## Definition of a credible demo
A visitor sees a useful Turkish event, understands its source/time/limitations, signs in, follows an asset, inspects evidence, asks a contextual question and receives an appropriate in-app event. Admin health shows the real data mode. A fund event demonstrates genuine fund-specific meaning. The demo includes a source-backed crypto market event, meaningful finalized on-chain evidence and a US equity event as well as BIST/funds. It discloses live versus delayed/replay/synthetic, active coverage and omitted features. This target is not a guarantee of complete market universes or all original requirements.

## Definition of not done
A screenshot, generated prose, hardcoded risk score, synthetic-only chart labeled live, auth mock, fake source link or one successful API request without rights does not complete the corresponding requirement. No model performance percentage is allowed without a reviewed evaluation.

## Schedule
Authorized pre-event preparation: specifications, research, capability/cost inventory and task planning; keep an honest contribution log. Organizer permission for competition use remains unresolved. Friday: clarify that gate, validate problem, confirm design/data spikes for all four markets and on-chain. Saturday: implement anchors then crypto/US/on-chain through shared contracts and safety/citation checks. Saturday evening: freeze the actual full-target demo path and rehearse; escalate missing required paths to the owner instead of silently reducing scope. Sunday morning: defects, evidence and pitch; preserve presentation-preparation time from 13:30 and jury session from 17:00 in supplied schedule.

## Fallback and cuts
Use authorized archived data for replay; synthetic fixtures are a separate plainly labeled last-resort demonstration of mechanics. Cut active universe and sophistication, not source transparency, private-data safety or fund focus. Dropping a selected market/on-chain path is a scope change needing later owner acceptance. Defer Redis/pgvector/extra chart library, advanced model training, social feeds, full mobile builds and elaborate admin functions.

## Acceptance and remaining gates
Documents 20,21,25 define test cases/tasks/gates. No data source has been live-tested or rights-approved in this preparation package. The offline reference tests validate limited arithmetic/policy only. The actual app, auth, provider integration, email and deployment remain unimplemented.
