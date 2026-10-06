# Project 50K — Authoritative Decisions & Corrections

**Version:** 0.4 audit revision · **Prepared:** 2026-10-02
**Status:** implementation specification / not a claim of deployed functionality.

## Authority and scope
This file and the amendments in documents 01–09 supersede conflicting v0.1/v0.2 wording. Keep requirement IDs stable. Original documents remain in `archive/v0.2/` for audit, not as agent instructions. This package specifies a product and provides a small offline reference harness. It does not contain a deployed application or measured production detector performance.

User-confirmed decisions remain: Türkiye first; BIST → Turkish investment funds → crypto → US equities; funds are a strategic differentiator; mobile-first consumer destination with responsive web MVP; natural Turkish UI, English engineering; Google-only accounts with public browsing; one watchlist, no cost-basis accounting; in-app and email, no browser push; global Critical alerts beyond the watchlist; source-backed asset chat with web research; no trading calls; protected admin; Impeccable and human design review.

## Corrections that implementation must observe
| Decision | Binding interpretation | Why it matters |
|---|---|---|
| DEC-001 | Intraday **monitoring** does not imply intraday fund NAV. Funds use their actual published valuation cadence. No interpolated NAV candles. | Distinguish market price from valuation and disclosure timing. |
| DEC-002 | `confidence.mode=HEURISTIC_EVIDENCE` initially; display `Kanıt gücü: 78/100`, not `%78 doğru`. `calibrated_probability=null`. | Weighted evidence is not an empirically calibrated probability [R07]. |
| DEC-003 | Borsapy history placeholders are missing, never investor count zero or AUM zero. | Source implementation inserts NaN/0 [S06]. |
| DEC-004 | Allocation by asset type is not security-level holdings. Last disclosed holdings are not current holdings. | Prevent invented fund→share relationships. |
| DEC-005 | IEX volume is IEX volume; provider/venue/adjustment changes reset baselines. | No comparison of partial and consolidated volume [S08]. |
| DEC-006 | Production and public hackathon access need explicit data rights; delay, educational context or a wrapper does not establish permission. | Non-display and display/redistribution are separate [S01,S05]. |
| DEC-007 | No news match is a bounded search result, not proof that no news exists or that manipulation occurred. | Record domains, window, failed sources, search time and contradictions. |
| DEC-008 | Same syndication chain counts once; price, momentum and volatility are correlated features, not three independent confirmations. | Avoid inflated confidence. |
| DEC-009 | Large transfer is not a sale; large token account is not an independent owner. | Labels require evidence [S11,S12]. BTC is not an EVM token. |
| DEC-010 | Replay cannot call today's unrestricted web search or use revised financials/current constituent lists as historical truth. | Both event and availability times must pass the replay cutoff. |
| DEC-011 | No alert is not a clean bill of health. | UI: `İzlediğimiz verilerde yeni bir uyarı yok.` |
| DEC-012 | Global Critical email requires user opt-in and MVP admin release. A lone numerical outlier cannot trigger a mass broadcast. | Limit panic, cost and false-positive harm. |
| DEC-013 | Catalog size and actively monitored coverage are separate. | Searchable 100 coins does not mean 100 full on-chain pipelines. |
| DEC-014 | Use one Python codebase, one API process, one worker process and PostgreSQL for weekend. Redis, vector search and a second chart package are deferred. | Reduce one-developer operational load. |
| DEC-015 | EVM and Solana are proposed initial adapter paths, not an exact owner-mandated network pair. Meaningful on-chain experience is part of the selected four-market demo; actual networks require capability/rights evidence. Do not advertise an unimplemented chain. | Preserve required experience without inventing provider support. |
| DEC-016 | No framework/model patch version is assumed. Verify supported versions at build start and commit lockfiles. | Official Next.js docs displayed 16.3.8 when checked on 2026-10-02 [S15]; versions can change. |
| DEC-017 | Ratings, user feedback and hand-picked demonstrations are not detector accuracy labels. | Distinguish usefulness, factual accuracy and anomaly classification. |

## Owner-confirmed continuation decisions — 2026-10-02

The exact answers and interpretations are recorded in research/USER_DECISIONS_2026-10-02.md and reports/OPEN_DECISIONS.md.

| Decision | Binding interpretation |
|---|---|
| DEC-018 | No written organizer ruling exists; competition use of prepared material remains unresolved. |
| DEC-019 | Selected weekend target: BIST + Turkish funds + crypto + US equities, including meaningful on-chain. Pre-event preparation is owner-authorized. Anchor-first sequencing is not reduced final acceptance. |
| DEC-020 | No existing project service accounts. TRY 5,000 total project ceiling, excluding development Claude/Codex subscriptions only; runtime services remain inside it. Ceiling is cumulative, not monthly, and does not automatically authorize spending. |
| DEC-021 | Use this updated v0.4 package and its owner decision record for subsequent tasks; do not re-ask answered questions or repeat the completed audit. |

## Event-specific gate: pre-event preparation
The user's pasted local application form says the startup idea must not have been worked on previously. It also requires a working prototype on 11 October. Whether this research/specification and any generated reference materials count as prohibited preparation is unresolved. Do not assume generic Startup Weekend rules override the local form [S33].

**Action before competition use of prepared material:** obtain the organizer’s written ruling on prior ideation, literature review, specifications, design assets, reusable scaffolding and reference test code; retain the answer. The owner confirmed no ruling and authorized pre-event preparation on 2026-10-02. That authorization permits the current documentation/planning work but does not establish an organizer exception. No concealment or retrospective claims that all work was produced at the event. Research/specification completion does not mean competition eligibility.

## Planning baseline — proposed implementation cut
- Catalog: broad metadata where legal and available; each asset exposes capabilities and coverage.
- Active first vertical slice: 10–20 BIST symbols, 5–10 funds with dated data, 10–20 crypto market pairs, 5–10 US symbols. These are capacity defaults, not changes to the product vision.
- Broader 75–100 crypto and 100–200 US catalogs remain targets, not guaranteed full live coverage.
- BIST intraday + fund-specific event are the first reliable implementation anchors. Crypto, US and meaningful on-chain are also required by the selected weekend target; provider/network spikes run early. Missing them is a reduced result requiring later owner acceptance.
- A degraded demo must state what is recorded, simulated, delayed, unavailable or live. It is not equivalent to full MVP acceptance.

## Approval boundaries
No deployment, paid subscription, email broadcast, account provisioning, repository write or organizer contact is authorized/executed by this package. Team members must approve spend, provide credentials securely and clear release gates. User-facing feature decisions above are confirmed; engineering thresholds, quotas and visual tokens below are proposed defaults to test.

## v0.4 audit authority
The new Work audit/correction is explicitly authorized by the attached continuation instruction. G01 remains a gate on competition use of prepared materials; it does not block this documentation audit or unrelated product planning. See reports/AUDIT_REPORT.md and reports/CORRECTION_LOG.md for justified fixes. The subsequent owner answers select the four-market/on-chain demo target and TRY 5,000 total ceiling, confirm no service accounts/ruling, and authorize preparation. Design tokens, reduced scope and external actions remain unapproved. Use the updated owner decision record, not earlier unanswered review wording.

## DEC-022 — Authorized research extension, 2026-10-02
The owner requested further scientific engine research, hypotheses, offline tests, durable findings and creative naming/design/imagegen experiments. This is delivered as v0.5 research; see research/USER_RESEARCH_REQUEST_2026-10-02.md and reports/RESEARCH_REPORT.md. Confirmed decisions retain priority. Constructed counterexamples refine interpretation boundaries, not product-completion or empirical accuracy. Name/logo/colors are proposed; no reduced market scope, spend or external action is approved.

### DEC-023 — Weakness/risk research authorization, 2026-10-03

Owner requested weaknesses, disadvantages and caution-point research in chat. Authorized document/public-source review, local arithmetic sensitivity and evidence filing. No new implementation acceptance, spending, deployment, contact or scope reduction is approved. Existing owner decisions and external gates remain intact. See reports/RISK_REVIEW.md.
