# Project 50K — Functional Requirements

**Document status:** Draft v0.2  
**Date:** 2026-10-02  
**Requirement prefix:** `FR`  
**Primary references:** `06_User_Requirements.md`, `04_MVP_Techstars_Startup_Weekend_Scope.md`

---

## 1. Purpose

This document specifies the system behaviors required to satisfy the Project 50K user requirements. It focuses on **observable system functionality** and is intended to guide implementation, agentic coding, testing, and later architecture decisions.

### Priority definitions

- **P0:** required for the Techstars MVP/core loop.
- **P1:** implement if the P0 loop is stable or immediately after MVP.
- **P2:** planned extension.

---

# 2. Asset Model and Search

### FR-001 — Canonical asset entity
**Priority:** P0  
The system shall represent every supported asset using a canonical internal identifier independent of provider-specific symbols.

Minimum metadata:

- asset ID;
- display symbol/code;
- canonical name;
- asset class;
- market/exchange/network;
- currency where relevant;
- country where relevant;
- provider identifiers;
- active/inactive status.

**Supports:** UR-002, UR-005

### FR-002 — Asset-class enumeration
**Priority:** P0  
The system shall support at least the following canonical asset classes in the MVP:

- `BIST_EQUITY`;
- `TR_INVESTMENT_FUND`;
- `CRYPTO`;
- `US_EQUITY`.

**Supports:** UR-002

### FR-003 — Universal search endpoint
**Priority:** P0  
The backend shall expose a search function that returns matches across all supported asset classes from one query.

**Supports:** UR-001, UR-002

### FR-004 — Search disambiguation
**Priority:** P0  
Search results shall include sufficient metadata to disambiguate similarly named assets, including market/asset class and canonical name.

**Supports:** UR-005

### FR-005 — Anonymous search access
**Priority:** P0  
Asset search and supported public asset pages shall be accessible without authentication.

**Supports:** UR-001, UR-003

---

# 3. Authentication and Authorization

### FR-006 — Google OAuth only
**Priority:** P0  
The MVP authentication system shall support Google OAuth as the only end-user authentication method.

The system shall not expose password registration, password reset, or e-mail verification workflows for Project 50K credentials.

**Supports:** UR-006

### FR-007 — User account creation/update
**Priority:** P0  
On successful Google sign-in, the system shall create or update a Project 50K user record linked to the external identity.

**Supports:** UR-006, UR-008

### FR-008 — Session-aware redirect
**Priority:** P0  
When a user signs in during an asset/watchlist workflow, the application shall return the user to the intended context whenever technically feasible.

**Supports:** UR-007

### FR-009 — Role model
**Priority:** P0  
The system shall support at least:

- `USER`;
- `ADMIN`.

**Supports:** UR-067

### FR-010 — Admin allowlist
**Priority:** P0  
Admin role assignment for the MVP shall be controlled by a server-side allowlist or equivalent protected configuration; a client-side e-mail check alone is insufficient.

**Supports:** UR-067

### FR-011 — Protected admin routes and APIs
**Priority:** P0  
All admin pages and admin APIs shall verify authenticated admin authorization server-side.

**Supports:** UR-067

---

# 4. Watchlist

### FR-012 — Add watchlist item
**Priority:** P0  
An authenticated user shall be able to add a supported asset to their watchlist.

**Supports:** UR-010

### FR-013 — Remove watchlist item
**Priority:** P0  
An authenticated user shall be able to remove a supported asset from their watchlist.

**Supports:** UR-011

### FR-014 — Watchlist uniqueness
**Priority:** P0  
The system shall prevent duplicate watchlist entries for the same user and asset.

**Supports:** UR-010, UR-012

### FR-015 — Persistent watchlist
**Priority:** P0  
Watchlist membership shall be stored in the database and restored across sessions/devices for the same authenticated user.

**Supports:** UR-008, UR-012

### FR-016 — No quantity/cost requirement
**Priority:** P0  
The watchlist data model shall not require quantity, purchase price, or average cost fields for MVP functionality.

**Supports:** UR-013

---

# 5. Market and Reference Data Ingestion

### FR-017 — Provider abstraction
**Priority:** P0  
Data ingestion shall use provider interfaces/adapters rather than embedding provider-specific calls directly throughout product logic.

At minimum, separate provider abstractions should exist for:

- equity market data;
- fund data;
- disclosure/regulatory data;
- crypto market data;
- on-chain data;
- news data.

**Supports:** maintainability and later licensed-provider migration.

### FR-018 — Timestamp normalization
**Priority:** P0  
All ingested observations shall store source timestamps and a normalized timestamp representation suitable for cross-source correlation.

**Supports:** UR-027

### FR-019 — Data freshness metadata
**Priority:** P0  
Ingested datasets used for user-facing events shall expose or retain sufficient metadata to determine freshness and last successful ingestion.

**Supports:** UR-027, UR-068

### FR-020 — Idempotent ingestion
**Priority:** P0  
Repeated ingestion of the same source event or market observation shall not create uncontrolled duplicates.

### FR-021 — Ingestion failure recording
**Priority:** P0  
The system shall record ingestion failures with provider, job type, timestamp, and error status for administrative visibility.

**Supports:** UR-068

### FR-022 — Scheduled and on-demand ingestion
**Priority:** P0  
The architecture shall support scheduled collection and developer/admin-triggered collection for demo/recovery scenarios.

### FR-023 — Data-source status
**Priority:** P0  
The system shall expose a derived health state for each important data source, such as healthy, delayed, stale, or failed.

**Supports:** UR-068

---

# 6. BIST Intelligence

### FR-024 — BIST OHLCV ingestion
**Priority:** P0  
The system shall ingest sufficient BIST price/volume history to calculate the selected MVP intraday anomaly signals for showcased securities.

**Supports:** UR-029

### FR-025 — BIST benchmark context
**Priority:** P0  
For supported securities, the system shall ingest or derive relevant index/market context and, where available, sector context.

**Supports:** UR-030

### FR-026 — KAP event ingestion
**Priority:** P0  
The system shall ingest relevant KAP disclosures for supported BIST issuers or retrieve them on demand.

**Supports:** UR-031

### FR-027 — KAP event classification
**Priority:** P0  
The system shall classify KAP disclosures into useful event categories using deterministic rules, AI classification, or a hybrid approach.

Examples:

- new contract/order;
- capital action;
- financial result;
- management/governance;
- material corporate event;
- other.

**Supports:** UR-031

### FR-028 — KAP materiality context
**Priority:** P1  
Where sufficient structured data exists, the system should calculate contextual ratios such as disclosed contract size relative to recent revenue or another relevant baseline.

**Supports:** UR-031, UR-032

### FR-029 — Fundamental dataset support
**Priority:** P1  
The system should ingest selected BIST financial-statement metrics sufficient to calculate the MVP fundamental anomaly rules.

**Supports:** UR-032

### FR-030 — Regulatory-event ingestion
**Priority:** P1  
The system should ingest relevant SPK/BIST measures or regulatory events for supported securities/issuers.

**Supports:** UR-033

---

# 7. Turkish Fund Intelligence

### FR-031 — Fund master-data ingestion
**Priority:** P0  
The system shall ingest sufficient metadata to identify and search supported Turkish investment funds.

**Supports:** UR-034, UR-035

### FR-032 — Fund price/NAV history
**Priority:** P0  
The system shall store supported historical fund price/NAV observations for anomaly and chart use.

**Supports:** UR-035

### FR-033 — Fund AUM/size metric support
**Priority:** P0 where source available  
The system shall ingest or derive fund size/AUM information when reliably available.

**Supports:** UR-037

### FR-034 — Investor-count metric support
**Priority:** P0 where source available  
The system shall ingest investor-count history when reliably available; if unavailable from the selected source, the UI and detector shall degrade gracefully rather than fabricate the metric.

**Supports:** UR-037

### FR-035 — Fund allocation ingestion
**Priority:** P0  
The system shall ingest fund allocation snapshots/history sufficient to detect meaningful asset-allocation changes.

**Supports:** UR-036

### FR-036 — Fund peer/category mapping
**Priority:** P1  
The system should map supported funds to relevant category/peer groups for comparative analysis.

**Supports:** UR-038

### FR-037 — Fund anomaly calculations
**Priority:** P0  
The anomaly engine shall support at least one fund-specific P0 detector and should support multiple when source data permits, including candidates such as:

- unusual fund-size change;
- investor-count change;
- allocation shift;
- peer/category divergence.

**Supports:** UR-037

### FR-038 — Fund-to-equity relation model
**Priority:** P2  
The data model shall be extensible to represent fund holdings/exposure relationships with BIST securities if sufficiently granular holding data becomes available.

**Supports:** UR-039

---

# 8. Crypto and On-Chain Intelligence

### FR-039 — Curated crypto universe
**Priority:** P0  
The system shall maintain a curated MVP universe of approximately 75–100 popular/liquid crypto assets, subject to reliable data-provider support.

**Supports:** UR-040

### FR-040 — Crypto market data ingestion
**Priority:** P0  
The system shall ingest price/volume history for the curated crypto universe.

**Supports:** UR-041

### FR-041 — EVM on-chain adapter
**Priority:** P0  
The architecture shall support at least selected EVM-compatible on-chain signals for MVP showcase assets.

**Supports:** UR-042

### FR-042 — Solana on-chain adapter
**Priority:** P0  
The architecture shall support at least selected Solana on-chain signals for MVP showcase assets.

**Supports:** UR-042

### FR-043 — On-chain event normalization
**Priority:** P0  
On-chain observations used by the intelligence engine shall be normalized into structured event/signal types independent of the source provider.

Examples:

- large transfer;
- exchange inflow/outflow;
- holder concentration change;
- liquidity change;
- wallet-cluster activity.

**Supports:** UR-042, UR-043

### FR-044 — Crypto multi-signal event creation
**Priority:** P0  
The decision engine shall be able to combine market anomaly signals with one or more on-chain signals into a single intelligence event.

**Supports:** UR-043

---

# 9. U.S. Equity Intelligence

### FR-045 — Restricted U.S. universe
**Priority:** P0  
The MVP shall support a restricted universe of liquid/popular U.S. equities rather than attempting complete U.S. market coverage.

Target range for planning: approximately 100–200 symbols, subject to provider limits.

**Supports:** UR-045

### FR-046 — U.S. OHLCV ingestion
**Priority:** P0  
The system shall ingest sufficient market data to demonstrate price/volume anomaly detection for selected U.S. equities.

**Supports:** UR-046

### FR-047 — U.S. contextual source integration
**Priority:** P1  
The system should retrieve selected earnings, filing, issuer, and trusted-news context for supported U.S. assets.

**Supports:** UR-047

---

# 10. Statistical and Deterministic Signal Engine

### FR-048 — Signal interface
**Priority:** P0  
Each anomaly/signal detector shall produce a structured output containing at least:

- signal type;
- asset ID;
- observation time/window;
- numeric/categorical evidence;
- baseline/reference used;
- normalized strength where applicable;
- detector version;
- data-quality/freshness indicators.

### FR-049 — Relative volume detector
**Priority:** P0  
The MVP shall implement an abnormal/relative volume detector for applicable market assets.

### FR-050 — Price-return anomaly detector
**Priority:** P0  
The MVP shall implement a detector for unusual price return relative to an asset's historical behavior and/or appropriate contextual baseline.

### FR-051 — Volatility anomaly detector
**Priority:** P0 or P1 depending on weekend capacity  
The engine shall support unusual realized/intraday volatility detection.

### FR-052 — Benchmark divergence detector
**Priority:** P0 for showcased BIST case  
The engine shall support divergence between an asset and a relevant market/index/sector benchmark when the mapping/data is available.

### FR-053 — Composite signal support
**Priority:** P0  
The system shall support event logic based on multiple independent signals rather than only single-threshold triggers.

### FR-054 — Detector versioning
**Priority:** P0  
Each generated signal/event shall be traceable to a detector configuration/version so that historical results are reproducible.

---

# 11. AI Intelligence Layer

### FR-055 — Structured AI tasks
**Priority:** P0  
AI/LLM calls used in the intelligence pipeline shall operate through defined tasks with structured expected outputs rather than unrestricted free-form generation.

Candidate tasks include:

- disclosure classification;
- news/event classification;
- materiality interpretation;
- cross-source synthesis;
- evidence-summary generation;
- asset-chat research.

### FR-056 — AI provider abstraction
**Priority:** P0  
The application shall call AI models through an internal provider/service abstraction so that core product logic is not permanently coupled to one model vendor.

### FR-057 — Evidence packet input
**Priority:** P0  
The AI explanation layer shall receive a structured evidence packet assembled by Project 50K rather than being asked to invent the event from a raw prompt alone.

### FR-058 — Source-aware AI output
**Priority:** P0  
AI-generated factual explanations shall retain references to the source evidence used in the answer.

**Supports:** UR-026, UR-052

### FR-059 — Official-source preference
**Priority:** P0  
When multiple sources describe the same event, retrieval/ranking logic shall prefer official/regulatory/issuer sources where practical.

**Supports:** UR-053

### FR-060 — Web research tool for asset assistant
**Priority:** P0  
The contextual asset assistant shall be able to invoke approved web research tooling for current information when project-indexed data is insufficient.

**Supports:** UR-051

### FR-061 — Insufficient-evidence response path
**Priority:** P0  
The AI layer shall support a structured `insufficient_evidence` or equivalent state and shall generate a clear user-facing response rather than forcing a causal explanation.

**Supports:** UR-054

### FR-062 — No recommendation mode
**Priority:** P0  
Project-owned prompts and response post-processing shall avoid generating Buy/Hold/Sell calls or personalized trading instructions as the product's own recommendation.

**Supports:** UR-055

### FR-063 — Turkish response localization
**Priority:** P0  
User-facing AI output shall be generated or post-edited in natural `tr-TR` financial language.

**Supports:** UR-049, UR-074

---

# 12. Decision and Event Engine

### FR-064 — Event entity
**Priority:** P0  
The system shall create a normalized `IntelligenceEvent` entity separate from raw signals.

Minimum fields:

- event ID;
- asset ID;
- event type;
- title/summary;
- start/detection time;
- severity;
- confidence;
- status;
- supporting signal IDs;
- evidence/source references;
- explanation version;
- detector/decision-engine version;
- replay/live origin.

### FR-065 — Cross-signal correlation
**Priority:** P0  
The decision engine shall be able to correlate multiple signals occurring within a relevant time/context window.

### FR-066 — Severity calculation
**Priority:** P0  
Severity shall be calculated from configured event logic and evidence magnitude; it shall not be determined solely by an LLM's self-assessment.

**Supports:** UR-021

### FR-067 — Confidence calculation
**Priority:** P0  
Confidence shall be calculated separately from severity using measurable factors such as evidence count/independence, signal strength, data quality/freshness, source authority, model calibration, and agreement between relevant components.

An LLM shall not simply be asked to invent its own numeric confidence.

**Supports:** UR-022, UR-023

### FR-068 — Confidence component storage
**Priority:** P0  
The system shall retain the factors contributing to confidence so the score can later be inspected/calibrated.

### FR-069 — Event de-duplication/merging
**Priority:** P0  
Repeated detections of the same underlying event within a configured time window shall be merged or updated rather than producing uncontrolled duplicate alerts.

### FR-070 — Event lifecycle
**Priority:** P1  
The system should support event states such as detected, updated, resolved/expired, and invalidated when new evidence changes the interpretation.

### FR-071 — Legal-language guard
**Priority:** P0  
For manipulation/fraud-related risk patterns, generated event labels and explanations shall use anomaly/risk-indicator language rather than asserting unverified criminal or regulatory conclusions.

**Supports:** UR-028

---

# 13. Event Presentation

### FR-072 — Event card summary
**Priority:** P0  
An event card shall display at least:

- asset;
- event title;
- event time;
- severity;
- confidence;
- concise evidence summary.

### FR-073 — Event detail view
**Priority:** P0  
The user shall be able to open an event detail view containing:

- explanation;
- supporting metrics;
- relevant chart/time context;
- source links;
- data freshness;
- feedback controls.

### FR-074 — Evidence-first rendering
**Priority:** P0  
If an AI explanation fails or is unavailable, the event detail shall still be able to display the deterministic/statistical evidence rather than hiding the event completely.

### FR-075 — Event chart markers
**Priority:** P0 for showcased cases  
The asset chart shall support visual markers for intelligence events and selected disclosures/news items.

---

# 14. Asset Detail Pages

### FR-076 — Common asset-page shell
**Priority:** P0  
All asset classes shall share a coherent page structure while allowing asset-class-specific modules.

### FR-077 — BIST page modules
**Priority:** P0  
The showcased BIST page shall include:

- price chart;
- volume/context;
- recent intelligence events;
- KAP/news evidence;
- AI assistant.

### FR-078 — Fund page modules
**Priority:** P0  
The showcased fund page shall include:

- NAV/price history;
- selected fund metrics;
- allocation information when available;
- recent fund intelligence events;
- AI assistant.

### FR-079 — Crypto page modules
**Priority:** P0  
The showcased crypto page shall include:

- market chart;
- market anomaly evidence;
- selected on-chain intelligence;
- combined events;
- AI assistant.

### FR-080 — U.S. equity page modules
**Priority:** P0  
The showcased U.S. equity page shall include:

- price chart;
- price/volume anomaly evidence;
- selected contextual event/news;
- AI assistant or common assistant shell.

---

# 15. Dashboard and Feeds

### FR-081 — Personal watchlist feed
**Priority:** P0  
The authenticated dashboard shall query and display eligible recent events for assets in the user's watchlist.

**Supports:** UR-015

### FR-082 — Market highlights feed
**Priority:** P0  
The application shall display a separate market-wide intelligence feed independent of watchlist membership.

**Supports:** UR-016

### FR-083 — Feed ranking
**Priority:** P0  
Feed ordering shall consider severity, confidence, freshness, and user relevance rather than relying exclusively on reverse chronology.

**Supports:** UR-018

### FR-084 — Quiet-state handling
**Priority:** P0  
The dashboard shall display an intentional quiet/healthy state when no eligible event is present.

**Supports:** UR-019

---

# 16. Notifications and E-mail

### FR-085 — Notification eligibility engine
**Priority:** P0  
The system shall determine notification eligibility separately from event creation.

### FR-086 — Watchlist notification policy
**Priority:** P0  
Events for watchlist assets shall be eligible for in-app/e-mail according to severity and user preference.

### FR-087 — Off-watchlist critical policy
**Priority:** P0  
Only events meeting the configured `Critical` global threshold shall be eligible for unsolicited off-watchlist immediate notifications in the MVP.

**Supports:** UR-017, UR-059

### FR-088 — In-app notification record
**Priority:** P0  
Eligible alerts shall create an in-app notification record with read/unread state.

### FR-089 — Immediate e-mail delivery
**Priority:** P0  
The system shall support immediate transactional e-mail delivery for eligible high/critical alerts.

### FR-090 — Notification idempotency
**Priority:** P0  
The same event/user/channel combination shall not be delivered repeatedly unless the event materially updates and the policy explicitly permits an update alert.

### FR-091 — Alert sensitivity modes
**Priority:** P1  
The system should support simple sensitivity profiles such as:

- Critical Only;
- Important + Critical;
- All Eligible.

### FR-092 — Digest generation
**Priority:** P1  
The system should be able to compile lower-urgency events into a scheduled digest.

### FR-093 — Browser push excluded
**Priority:** P0 constraint  
The MVP shall not require browser push implementation.

---

# 17. Contextual AI Chat

### FR-094 — Asset-context injection
**Priority:** P0  
When chat is opened from an asset page, the backend shall automatically provide canonical asset identity and relevant recent intelligence context.

### FR-095 — Conversation persistence
**Priority:** P1  
Authenticated users should be able to retain recent asset chat history.

### FR-096 — Source rendering in chat
**Priority:** P0  
The UI shall render inspectable source references for material factual claims returned by the assistant.

### FR-097 — Tool-result separation
**Priority:** P0  
The assistant architecture shall distinguish retrieved/tool-derived facts from model-generated synthesis so that source grounding can be preserved.

### FR-098 — Chat failure fallback
**Priority:** P0  
If web research or one data source fails, the assistant shall either answer from available grounded evidence with a limitation statement or state that it cannot reliably answer.

---

# 18. Feedback

### FR-099 — Event feedback controls
**Priority:** P0  
Event detail/card views shall provide at least two quick feedback actions such as `Useful` and `Not Relevant`.

### FR-100 — Feedback persistence
**Priority:** P0  
Feedback shall be stored with user ID, event ID, response value, and timestamp.

### FR-101 — Feedback analytics
**Priority:** P1  
Admin/product analytics should aggregate event feedback by event type, severity, and detector version.

---

# 19. Admin Operations Dashboard

### FR-102 — Admin KPI summary
**Priority:** P0  
The admin dashboard shall display at least:

- total users;
- watchlist count;
- generated event count;
- recent high/critical event count;
- notification/e-mail activity where available.

### FR-103 — Data freshness panel
**Priority:** P0  
The admin dashboard shall display freshness/health information for major data providers/jobs.

### FR-104 — Recent event inspection
**Priority:** P0  
An admin shall be able to inspect recent intelligence events and their severity/confidence.

### FR-105 — Controlled threshold configuration
**Priority:** P0 limited  
The admin dashboard shall expose only a small explicit set of safe configuration values/feature flags during the MVP.

Arbitrary code or unrestricted detector expressions shall not be editable through the admin UI.

### FR-106 — Configuration persistence and audit
**Priority:** P1  
Admin configuration changes should record who changed what and when.

### FR-107 — AI version visibility
**Priority:** P1  
The admin dashboard should display active AI model/prompt/config version metadata.

---

# 20. Historical Replay and Demo Support

### FR-108 — Historical replay dataset
**Priority:** P0  
The MVP shall contain at least one curated historical case for BIST and should contain at least one fund/crypto case that can be replayed reliably during the jury demo.

### FR-109 — Time-bounded replay
**Priority:** P0  
Replay logic shall prevent the detector/explanation layer from using future information that would not have been available at the replay timestamp when demonstrating detection validity.

### FR-110 — Replay/live event parity
**Priority:** P0  
Historical replay shall produce the same normalized event structure used by current/live events.

### FR-111 — Demo mode fallback
**Priority:** P0  
The application may provide an explicit internal demo/replay mode so jury presentation does not depend on a live anomaly happening during the presentation.

---

# 21. Landing Page

### FR-112 — Value proposition above the fold
**Priority:** P0  
The landing page shall communicate the monitoring/anomaly-intelligence value proposition within the first viewport.

### FR-113 — Search from landing
**Priority:** P0  
The landing page shall provide direct access to asset search.

### FR-114 — Example intelligence event
**Priority:** P0  
The landing page shall include at least one convincing example of an intelligence event rather than relying exclusively on marketing copy.

### FR-115 — Product-scope communication
**Priority:** P0  
The landing page shall communicate that the product covers BIST and Turkish funds as primary markets with crypto and U.S. equity expansion/support.

### FR-116 — Sign-in CTA
**Priority:** P0  
The landing page shall provide a clear Google sign-in CTA for users who want watchlist/alerts.

---

# 22. Localization and UI Content

### FR-117 — `tr-TR` default UI
**Priority:** P0  
The user-facing MVP shall default to Turkish (`tr-TR`).

### FR-118 — English internal identifiers
**Priority:** P0  
Code identifiers, API fields, database names, internal prompts, and engineering documentation shall use English unless a source field must preserve an original Turkish label.

### FR-119 — Financial terminology glossary
**Priority:** P1  
The project should maintain a small approved terminology glossary for recurring Turkish financial terms to improve UI/AI consistency.

---

# 23. Analytics and Auditability

### FR-120 — Event-generation audit record
**Priority:** P0  
Each event shall retain enough metadata to identify the signals, evidence, detector version, and explanation version used to create it.

### FR-121 — Notification audit record
**Priority:** P0  
Each attempted notification shall record channel, user, event, status, and timestamp.

### FR-122 — AI request metadata
**Priority:** P1  
AI calls used for production intelligence should record non-secret metadata such as task type, model/config version, latency, and success/failure state.

---

# 24. Functional Acceptance Definition for MVP

The MVP is functionally acceptable for jury presentation when the following end-to-end sequence works reliably:

1. an anonymous visitor opens the deployed application;
2. searches a BIST asset;
3. opens its asset page;
4. sees a chart with a historical/current event marker;
5. opens the event;
6. sees severity, confidence, evidence, and sources;
7. reads a natural-Turkish AI explanation;
8. signs in with Google;
9. adds the asset to the watchlist;
10. sees the event in the personal dashboard/feed;
11. asks the asset assistant a contextual question and receives a sourced answer;
12. submits event feedback;
13. an eligible event can create an in-app notification and a demonstrable e-mail;
14. the admin can see system/event metrics and data freshness.
