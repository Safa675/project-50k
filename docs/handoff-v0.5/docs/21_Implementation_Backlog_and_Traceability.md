# Project 50K — Implementation Backlog & Traceability

**Version:** 0.4 audit revision · **Prepared:** 2026-10-02
**Status:** implementation specification / not a claim of deployed functionality.

## 1. Scope rule
The 284 legacy requirements describe a product backlog, not 284 tasks that one developer can finish in a weekend. Existing IDs remain stable. `CORE`, `CONDITIONAL`, `NEXT`, `LATER` are execution phases; legacy P0/P1/P2 remain historical importance labels. Safety constraints apply wherever the related feature ships.

## 2. Vertical slices
| Task | Phase | Output / acceptance | Dependencies | Owner |
|---|---|---|---|---|
| T00 | GATE | Organizer ruling for competition use; rights/cost feasibility within TRY 5,000; explicit spend/account setup | Owner answers recorded; external evidence pending | Business + developer |
| T01 | CORE | Monorepo, locked dependencies, env example, CI, error boundary | Concrete local task authorization; T00 before competition use/remote actions | Developer |
| T02 | CORE | PRODUCT/DESIGN approved, asset/event screen and landing layout | Shared tokens, user interviews | Designer |
| T03 | CORE | Google auth, private user access, protected admin role | T01, configured project | Developer |
| T04 | CORE | Canonical assets, capabilities, provider interfaces and spike reports | T01, data rights | Developer |
| T05 | CORE | BIST final bars → quality gates → simple signal → evidence event | T04 | Developer |
| T06 | CORE | Fund NAV/dated allocation signal; flow only if real history exists | T04 | Developer |
| T07 | CORE | Event detail, source drawer, chart markers, unknown states | T02,T05,T06 | Developer + designer |
| T08 | CORE | Structured AI investigation/chat with read tools and citations | T07, LLM budget | Developer |
| T09 | CORE | Watchlist, personal/global feed, in-app alerts and feedback | T03,T07 | Developer |
| T10 | CORE-CONDITIONAL | Email immediate + digest via outbox, opt-in, unsubscribe, dry-run | T09, sender/domain, legal gate | Developer |
| T11 | CORE | Minimal admin health, event inspection, pause switch, bounded config | T03,T05 | Developer |
| T12 | CORE | Time-correct replay isolated from live research and sending | T05–T08 | Developer |
| T13 | CONDITIONAL | Crypto/US market adapters and same coverage UI | T04–T09 | Developer |
| T14 | CONDITIONAL | Meaningful finalized on-chain evidence; EVM+Solana proposed, exact paths after spikes | T13, actual network access/finality/labels | Developer |
| T15 | CORE | Security/E2E/design validation and release report | Implemented slices | Whole team |
| T16 | CORE | User interviews, pitch, rehearsal and exact coverage declaration | Ongoing, T12,T15 | Business + designer |
| T17 | NEXT | Expand active universe, holdings relationships and quality dashboards | Stable core, budget | Later |
| T18 | LATER | Mobile app, broader on-chain and learned calibration; broker import is unapproved exploration | Research/rights validation | Later |

The owner selected the four-market/on-chain weekend target on 2026-10-02. CONDITIONAL marks provider/network admission dependencies, not permission to omit those paths from accepted target coverage. User-required on-chain intelligence, US coverage and email remain in product scope; EVM+Solana is the proposed initial network choice. Missing a required path means reduced delivery needing later owner acceptance. No service accounts exist; plan cumulative cost within TRY 5,000 excluding development Claude/Codex subscriptions.

## 3. Execution order
Build one working path end to end before expanding providers: public asset → sign in → follow → event → sources → chat → notification → admin pause → replay. Fund intelligence is an anchor, not a tab to add at the end. The first fund event may be a verified disclosure/allocation change instead of an unsupported fund-outflow calculation.

The frontend must handle live/delayed/replay/synthetic/unavailable from the same contract. An agent must not add green “connected” states for adapters that have not been tested.

## 4. Weekend checkpoints
Friday: idea selection/organizer clearance, short user interviews, scope, design and data spikes. Saturday morning: one BIST and one fund path. Saturday afternoon: watchlist, AI source workflow and ops controls. Saturday evening: rehearsal build including actual crypto/US/on-chain paths, exact coverage declaration and email dry-run; escalate missing required coverage. Sunday morning: defects/accessibility/replay and pitch only. The screenshot program puts presentation preparation at 13:30 and jury presentations at 17:00 on Sunday; preserve time for both.

Do not turn these checkpoints into a claim that this amount of work is guaranteed. One developer has a high integration burden. Restrict active universe/sophistication before removing provenance, auth safety, transparent confidence or design quality. Dropping a selected market/on-chain path requires a new owner decision; no such cut is approved here.

## 5. Cut order
Defer Redis, vectors, second chart library, sophisticated model training, arbitrary admin prompt editing, true portfolio accounting, social-media scraping, mobile binaries and automated mass critical pushes. Restrict active symbols before disabling source/timestamp clarity. Never ship placeholders as live data to make the demo look complete.

## 6. Agent task contract
Every task must state requirement IDs, accepted design reference, files allowed, data mode, failure states, tests and definition of done. The agent reports implemented/tested/not tested separately. Use `templates/TASK.md` and the machine traceability map. No broad “build the whole app” unreviewed run.

## v0.5 research continuation
v0.5 research adds no completed tasks. Before implementation, use the kept interpretation gates and rejected counterexamples in research/engine_lab/HYPOTHESES.json as acceptance inputs. First concrete tasks can specify source/time/fund-action/chain-finality admission and typed claim-stage outputs, then build actual four-market/on-chain paths. Offline lab code is not copied into production without the task-level review/testing process.

## 2026-10-03 risk review

Next learning priorities are exact capabilities/rights, bounded cumulative cost/horizon, same-job user value, and small actual four-path/failure integrations. These proposals neither change requirement IDs nor silently narrow final acceptance. Current synthesis: reports/RISK_REVIEW.md; register: research/risk_review/RISK_REGISTER.json.

## Problem solution and market research continuation 3 October 2026

Prioritize a reusable exposure/eligibility measurement specification and inspectable source/time/context artifacts alongside authorized implementation. Proposed observational/comparative validation and payment tests require later scoped authorization where applicable; no completed product task or new requirement is inferred. See `reports/PROBLEM_MARKET_RESEARCH.md` and the linked source-depth appendices.
