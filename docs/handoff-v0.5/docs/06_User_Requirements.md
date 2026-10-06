# Project 50K — User Requirements

**Document status:** Amended draft v0.3  
**Date:** 2026-10-02  
**Requirement prefix:** `UR`  
**Primary market:** Türkiye  
**MVP surface:** Responsive web application  
**Long-term product direction:** Mobile-first consumer product

> v0.3 authority: document 00 and contracts resolve earlier ambiguities. Legacy P0/P1/P2 express product importance, not a weekend completion guarantee. Execution phases are in document 21 and traceability. All product implementation remains pending. Personas are hypotheses, not verified interview findings.

---

## 1. Purpose

This document defines **what users need to be able to accomplish** with Project 50K. It intentionally avoids prescribing implementation details unless they are already locked product constraints.

Functional behavior is specified separately in `07_Functional_Requirements.md`.

### Priority definitions

- **P0 — Must:** core product importance; not a promise that every item ships in one weekend.
- **P1 — Should:** important after the core loop is stable; may be implemented during the weekend if time permits.
- **P2 — Could:** post-MVP or expansion requirement.

---

# 2. Public Discovery and Asset Research

### UR-001 — Public asset discovery
**Priority:** P0  
A visitor shall be able to search supported assets without creating an account.

### UR-002 — Cross-asset search
**Priority:** P0  
A visitor shall be able to search across supported BIST equities, Turkish investment funds, selected crypto assets, and selected U.S. equities from a single search experience.

### UR-003 — Public asset overview
**Priority:** P0  
A visitor shall be able to open an asset page and understand the asset's current market state, recent price behavior, and important detected events.

### UR-004 — Public evidence access
**Priority:** P0  
A visitor shall be able to inspect the evidence and sources supporting a public intelligence event.

### UR-005 — Clear market/asset identity
**Priority:** P0  
A user shall be able to clearly distinguish between assets with similar symbols or names and understand which market/asset class is being viewed.

---

# 3. Authentication and Account

### UR-006 — Frictionless authentication
**Priority:** P0  
A user shall be able to create/access an account through Google sign-in without creating or managing a Project 50K password.

### UR-007 — Anonymous-to-authenticated continuity
**Priority:** P0  
A visitor who signs in from an asset page should be able to continue the current workflow without losing context.

### UR-008 — Persistent personal state
**Priority:** P0  
An authenticated user's watchlist, alert preferences, notifications, and feedback shall persist across sessions.

### UR-009 — Secure sign-out
**Priority:** P0  
An authenticated user shall be able to sign out and return to the anonymous public experience.

---

# 4. Watchlist / My Assets

### UR-010 — Add asset to watchlist
**Priority:** P0  
An authenticated user shall be able to follow an asset from search results or its asset page.

### UR-011 — Remove asset from watchlist
**Priority:** P0  
An authenticated user shall be able to stop following an asset.

### UR-012 — Unified watchlist concept
**Priority:** P0  
For the MVP, the product shall use one simple `Watchlist / My Assets` concept rather than separate portfolio and watchlist workflows.

### UR-013 — No mandatory quantity or cost basis
**Priority:** P0  
A user shall not be required to provide units, purchase price, or average cost in order to follow an asset.

### UR-014 — Optional exposure data in future
**Priority:** P2  
A user may later be able to provide optional position size or portfolio weight for relevance prioritization without turning Project 50K into a portfolio-accounting product.

---

# 5. Personal Intelligence Feed

### UR-015 — Personalized important developments
**Priority:** P0  
An authenticated user shall see important events affecting assets on their watchlist.

### UR-016 — Market-wide highlights
**Priority:** P0  
A user shall see a separate feed of important market events that are not limited to their watchlist.

### UR-017 — Critical off-watchlist awareness
**Priority:** P0  

An authenticated user may explicitly opt into genuinely critical off-watchlist notifications. MVP global circulation requires policy eligibility, valid evidence and admin release; opting out suppresses queued external delivery.

**v0.3 amendment:** see document 00; original text retained in archive/v0.2.

### UR-018 — Attention prioritization
**Priority:** P0  
The feed shall prioritize events by importance and user relevance rather than presenting a raw chronological data stream only.

### UR-019 — Quiet state
**Priority:** P0  
When no meaningful event is detected, the product shall communicate that clearly rather than manufacturing activity or low-value alerts.

---

# 6. Event Understanding

### UR-020 — Event type
**Priority:** P0  
For each surfaced event, the user shall be able to understand what kind of event was detected, such as unusual market movement, abnormal volume, fund allocation change, regulatory event, or on-chain activity.

### UR-021 — Severity
**Priority:** P0  
Each intelligence event shall communicate an importance/severity level.

### UR-022 — Confidence
**Priority:** P0  

Each event shall expose evidence strength separately from severity. In v1 this is an inspectable heuristic score, not a calibrated probability of correctness, manipulation or loss. When support is insufficient the score is unavailable.

**v0.3 amendment:** see document 00; original text retained in archive/v0.2.

### UR-023 — Severity-confidence separation
**Priority:** P0  
The user shall not be led to interpret event severity and system confidence as the same concept.

### UR-024 — Why detected
**Priority:** P0  
A user shall be able to understand the quantitative or categorical reasons why an event was detected.

### UR-025 — Evidence inspection
**Priority:** P0  
A user shall be able to inspect supporting metrics, timestamps, and source evidence.

### UR-026 — Source provenance
**Priority:** P0  
Material factual claims shall show or link to their source whenever the product presents an AI-generated interpretation.

### UR-027 — Data freshness
**Priority:** P0  
The user shall be able to understand when the relevant data or source was last updated when freshness materially affects interpretation.

### UR-028 — No false legal conclusion
**Priority:** P0  
The product shall describe observed risk indicators and anomalies without presenting an unverified legal conclusion that a person, company, security, or token is engaged in market manipulation, fraud, or another offense.

---

# 7. BIST Requirements

### UR-029 — Intraday BIST intelligence
**Priority:** P0  
A user shall be able to view intraday BIST behavior for supported securities and inspect intraday anomaly events where data availability permits.

### UR-030 — BIST contextual comparison
**Priority:** P0  
A user shall be able to understand whether a BIST asset's movement differs materially from relevant market, index, or sector context when such data is available.

### UR-031 — KAP context
**Priority:** P0  
A user shall be able to see relevant KAP disclosures in the context of the security's market behavior.

### UR-032 — Fundamental context
**Priority:** P1  
A user should be able to see significant financial-statement changes or anomalies relevant to a BIST security.

### UR-033 — Regulatory context
**Priority:** P1  
A user should be able to see relevant SPK/BIST regulatory events or measures associated with a security or issuer.

---

# 8. Turkish Investment Fund Requirements

### UR-034 — Fund-specific intelligence
**Priority:** P0  
A user shall receive fund intelligence that goes beyond simple return charts.

### UR-035 — Fund historical metrics
**Priority:** P0  

A user shall see historical fund metrics only where actual dated values exist. NAV publication cadence, source date and missing AUM/investor history shall be disclosed; no interpolation may create fictional intraday fund prices.

**v0.3 amendment:** see document 00; original text retained in archive/v0.2.

### UR-036 — Fund allocation intelligence
**Priority:** P0  
A user shall be able to see meaningful changes in fund asset allocation where source data is available.

### UR-037 — Fund anomaly events
**Priority:** P0  
The system shall surface fund-specific anomalies such as unusual fund-size changes, investor-count changes, allocation shifts, or category divergence when sufficient data exists.

### UR-038 — Fund peer context
**Priority:** P1  
A user should be able to compare a fund's behavior with relevant peers or category benchmarks.

### UR-039 — Fund-to-market relationship intelligence
**Priority:** P2  
A user may later be able to inspect meaningful relationships between fund behavior/holdings and underlying BIST securities when sufficient reliable data exists.

---

# 9. Crypto Requirements

### UR-040 — Popular crypto coverage
**Priority:** P0  

A user shall be able to discover a meaningful curated set of popular crypto assets, with active monitoring and on-chain coverage disclosed separately from catalog membership.

**v0.3 amendment:** see document 00; original text retained in archive/v0.2.

### UR-041 — Crypto market anomalies
**Priority:** P0  
A user shall be able to see price, volume, and volatility-related crypto anomalies.

### UR-042 — On-chain intelligence
**Priority:** P0  
For supported networks/assets, a user shall be able to see at least selected on-chain signals such as whale transfers, concentration, exchange flows, liquidity-related changes, or related wallet activity.

### UR-043 — Multi-signal crypto event
**Priority:** P0  
The user shall be able to see when market and on-chain signals combine into a single higher-context event.

### UR-044 — Network transparency
**Priority:** P0 — safety/coverage requirement when feature is exposed

A user shall see the exact blockchain/network and asset identity of an on-chain signal. Partial token-account coverage shall not be represented as complete beneficial ownership.

**v0.3 amendment:** see document 00; original text retained in archive/v0.2.

---

# 10. U.S. Equity Requirements

### UR-045 — Selected U.S. equity coverage
**Priority:** P0  
A user shall be able to search and inspect a restricted but meaningful universe of liquid/popular U.S. equities in the MVP.

### UR-046 — U.S. market anomalies
**Priority:** P0  
A user shall be able to view market anomaly events for supported U.S. equities.

### UR-047 — U.S. contextual events
**Priority:** P1  
A user should be able to view selected earnings, filing, or trustworthy-news context relevant to supported U.S. equities.

---

# 11. AI Asset Assistant

### UR-048 — Asset-aware conversation
**Priority:** P0  
A user shall be able to ask questions from an asset page without repeatedly specifying which asset is being discussed.

### UR-049 — Natural Turkish answers
**Priority:** P0  
The assistant shall respond in natural Turkish using established financial terminology rather than literal or awkward machine-translated expressions.

### UR-050 — Project data usage
**Priority:** P0  
The assistant shall use Project 50K's structured market/event data when answering questions about the current asset.

### UR-051 — Web research capability
**Priority:** P0  
The assistant shall be able to research current public information on the web when needed, subject to source-quality and grounding requirements.

### UR-052 — Source-backed AI claims
**Priority:** P0  
Material factual claims in AI responses shall be accompanied by sources that the user can inspect.

### UR-053 — Source hierarchy awareness
**Priority:** P0  
The assistant shall prefer official/regulatory and issuer sources over lower-authority sources when available.

### UR-054 — Insufficient-evidence answer
**Priority:** P0  
The assistant shall be able to state clearly that the available evidence is insufficient to explain a movement or reach a conclusion.

### UR-055 — No direct investment recommendation
**Priority:** P0  
The assistant shall not provide Project 50K-authored Buy/Hold/Sell recommendations or act as an automated personalized investment adviser.

### UR-056 — Conversational drill-down
**Priority:** P1  
A user should be able to move from a detected event to historical comparison, source interpretation, and follow-up explanation through conversation.

---

# 12. Notifications and E-mail

### UR-057 — In-app notifications
**Priority:** P0  
An authenticated user shall receive in-app notifications for eligible intelligence events.

### UR-058 — Immediate high-importance e-mail
**Priority:** P0  

An authenticated user shall be able to opt into immediate email for eligible high/critical personal events and approved critical market-wide events. Real delivery requires verified sender, legal/rights gates, idempotency and send-time consent checks.

**v0.3 amendment:** see document 00; original text retained in archive/v0.2.

### UR-059 — Market-wide spam protection
**Priority:** P0  
The product shall apply a materially higher threshold to unsolicited off-watchlist alerts than to watchlist alerts.

### UR-060 — Alert sensitivity preference
**Priority:** P1  
A user should be able to select a simple alert sensitivity profile such as Critical Only, Important + Critical, or All Eligible Alerts.

### UR-061 — Digest e-mail
**Priority:** P1  
A user should be able to receive a periodic digest for lower-urgency developments instead of receiving every event as an immediate e-mail.

### UR-062 — No browser push requirement
**Priority:** P0 constraint  
The MVP shall not require browser push notifications.

### UR-063 — Native push future direction
**Priority:** P2  
The future mobile product should use native push notifications as a core alert channel.

---

# 13. User Feedback

### UR-064 — Event relevance feedback
**Priority:** P0  
A user shall be able to indicate that an event was useful/relevant or irrelevant/not useful.

### UR-065 — Feedback without friction
**Priority:** P0  
Submitting event feedback shall require no more than a simple single-action interaction unless the user voluntarily provides additional detail.

### UR-066 — Feedback history for improvement
**Priority:** P1  
The product should retain event feedback so that product/decision-engine quality can be evaluated over time.

---

# 14. Admin / Operations Requirements

### UR-067 — Protected admin access
**Priority:** P0  
Only explicitly authorized Google accounts shall be able to access the admin area.

### UR-068 — Operational health
**Priority:** P0  
An admin shall be able to understand whether key data sources and ingestion jobs are current and functioning.

### UR-069 — Event monitoring
**Priority:** P0  
An admin shall be able to inspect recent generated events and high/critical events.

### UR-070 — Product metrics
**Priority:** P0  
An admin shall be able to view a minimal set of product metrics such as user count, watchlist count, event count, and notification activity.

### UR-071 — Controlled configuration
**Priority:** P0  
An admin shall be able to adjust a small approved set of thresholds or feature flags without requiring a code deployment.

### UR-072 — AI configuration visibility
**Priority:** P1  
An admin should be able to identify the active AI model/configuration or prompt version associated with generated intelligence.

---

# 15. Language and Design Requirements

### UR-073 — Turkish product language
**Priority:** P0  
The user-facing MVP shall use Turkish as its primary application language.

### UR-074 — Native financial terminology
**Priority:** P0  
UI copy shall use established Turkish financial-market terminology and avoid awkward literal translations.

### UR-075 — Progressive disclosure
**Priority:** P0  
The product shall present a concise explanation first and allow the user to reveal deeper metrics, methodology, and evidence when desired.

### UR-076 — Deliberate visual design
**Priority:** P0  
The product shall feel intentionally designed and shall avoid generic AI-generated fintech-dashboard patterns that reduce trust or clarity.

### UR-077 — Responsive web usability
**Priority:** P0  
The MVP shall be usable on common desktop and mobile web viewport sizes even though native mobile applications are outside the weekend scope.

---

# 16. Historical Proof and Live Monitoring

### UR-078 — Historical anomaly replay
**Priority:** P0  
A user/jury member shall be able to inspect at least one historical case showing that the system would have detected a meaningful event using historical data.

### UR-079 — Current/live capability proof
**Priority:** P0  
The MVP shall demonstrate that the architecture can ingest current or near-current data even if historical replay is used as the primary reliable jury demonstration.

### UR-080 — Explainable replay
**Priority:** P0  
Historical replay shall preserve the same event evidence, severity/confidence concept, and explanation workflow as current events.

---

# 17. Explicit Non-Requirements for MVP

The following are intentionally **not user requirements for the Techstars MVP**:

- trade execution;
- brokerage account connection;
- portfolio P&L accounting;
- tax calculation;
- mandatory cost-basis tracking;
- automatic trading;
- copy trading;
- social-media monitoring as a core source;
- browser push notifications;
- native iOS/Android application;
- unrestricted coverage of every global security and every blockchain;
- definitive legal determination of fraud/manipulation;
- personalized Buy/Hold/Sell recommendations.
