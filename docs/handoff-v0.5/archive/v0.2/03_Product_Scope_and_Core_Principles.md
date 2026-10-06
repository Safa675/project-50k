# Project 50K — Product Scope & Core Principles

**Document status:** Draft v0.1  
**Date:** 2026-10-02  
**Purpose:** Define the product boundary before detailed user and functional requirements are written.  

---

## 1. Scope Definition

Project 50K is a consumer financial-intelligence product that monitors supported assets, detects unusual or materially important events, explains those events using evidence, and alerts users based on relevance and severity.

The product has two simultaneous goals:

1. **Proactive intelligence:** detect important developments without requiring the user to configure every alert condition.
2. **Interactive investigation:** allow the user to search an asset and ask evidence-backed questions in context.

The product is intentionally not a brokerage or investment-advice engine.

---

## 2. User Roles

### 2.1 Anonymous Visitor

May:

- access the landing page;
- search supported assets;
- open public asset pages;
- view selected charts and metrics;
- view public intelligence events;
- inspect event evidence and sources subject to rate limits.

May not:

- save a watchlist;
- receive personal notifications;
- retain chat history;
- change alert preferences.

### 2.2 Authenticated User

Authentication method for MVP: **Google OAuth only**.

May:

- create and edit a watchlist;
- receive personal intelligence events;
- receive in-app and e-mail notifications;
- configure alert sensitivity;
- use asset-level AI chat with retained history;
- submit event feedback;
- manage basic account preferences.

### 2.3 Administrator

Admin access is granted through role-based authorization and an explicit allowlist of approved Google accounts for MVP.

May access an internal operations dashboard covering selected:

- platform metrics;
- user metrics;
- watchlist metrics;
- event counts;
- event categories/severity;
- ingestion/source health;
- data freshness;
- job failures;
- e-mail delivery status;
- selected anomaly thresholds;
- source enable/disable controls;
- minimum confidence settings;
- feature flags;
- AI/prompt configuration metadata.

The hackathon implementation only needs a useful subset of this scope.

---

## 3. Asset Scope

### Priority order

1. BIST equities
2. Turkish investment funds
3. Crypto
4. U.S. equities

### MVP coverage principle

Depth is more important than superficial breadth.

BIST and Turkish funds should feel like first-class product domains. Crypto and U.S. equities should demonstrate that the architecture is cross-asset without consuming the majority of the hackathon effort.

### Long-term coverage

The architecture should allow additional asset types later, but the MVP should not attempt to support every security, fund type, blockchain or global exchange.

---

## 4. Watchlist and Portfolio Scope

For MVP:

> **Watchlist = My Assets**

The user follows an asset by adding it to the watchlist.

The following are explicitly excluded from MVP:

- lot/share quantity;
- average purchase price;
- realized/unrealized P&L;
- dividend accounting;
- split-adjusted personal accounting;
- tax calculation;
- broker synchronization.

### Future consideration

Optional position weight or portfolio exposure may later improve event prioritization. Average cost should only be introduced if the product intentionally expands into portfolio accounting.

---

## 5. Core Product Modules

### 5.1 Landing / Public Marketing Site

Purpose:

- communicate the problem and value proposition quickly;
- demonstrate visual quality;
- allow immediate asset search;
- convert visitors into Google-authenticated users.

### 5.2 Universal Asset Search

Search across supported:

- BIST symbols/company names;
- Turkish fund codes/names;
- supported crypto assets;
- supported U.S. equities.

Search must identify asset type clearly and route to the correct asset page.

### 5.3 Market Intelligence Feed

A public or semi-public feed of significant events across supported markets.

Primary concept:

> **Piyasada Öne Çıkanlar**

This is distinct from the user's personal feed.

### 5.4 Personal Intelligence Feed

For authenticated users.

Shows:

- watchlist events;
- prioritized events;
- event severity;
- confidence;
- concise explanation;
- timestamp/data freshness;
- evidence/source access.

### 5.5 Asset Detail Page

Common shell plus asset-class-specific sections.

Common elements:

- identity/header;
- current status/market state;
- price chart;
- event markers/timeline;
- current intelligence summary;
- recent events;
- sources/evidence;
- AI investigation interface.

### 5.6 Asset-Specific AI Assistant

The assistant automatically receives the current asset context.

It may:

- use Project 50K's indexed data;
- retrieve official/source documents;
- perform web research using approved search tooling;
- compare current behavior with historical data;
- explain metrics in natural Turkish;
- answer follow-up questions.

It must:

- cite material factual claims;
- prioritize high-quality sources;
- distinguish facts from interpretation;
- explicitly communicate insufficient evidence;
- avoid Buy/Hold/Sell recommendations.

### 5.7 Notification Center

Tracks alerts and read/unread state.

MVP channels:

- in-app;
- e-mail.

Not MVP:

- browser push;
- native push.

### 5.8 Admin Operations Dashboard

Internal interface for monitoring the intelligence system and selected product configuration.

---

## 6. BIST Intelligence Scope

### Market signals

Potential MVP/current scope:

- intraday return anomaly;
- abnormal volume/relative volume;
- volatility anomaly;
- price-volume combination;
- market/index divergence;
- sector divergence where mappings are available;
- unusual gap/momentum behavior where useful.

### Disclosure intelligence

- KAP event ingestion;
- event classification;
- concise natural-language explanation;
- materiality/context calculations where possible;
- correlation between disclosure timing and market behavior.

### Fundamental intelligence

Candidate metrics/events:

- revenue change;
- margin change;
- net-income change;
- operating-cash-flow divergence;
- receivable growth;
- debt change;
- unusual quarter-over-quarter/year-over-year changes.

Exact anomaly rules are deferred to the Anomaly Catalog and scientific review.

### Regulatory intelligence

- selected SPK/BIST events;
- relevant measures/restrictions where available;
- event linking to securities/entities.

### Trusted news

- ingest/identify relevant trusted news;
- associate it with the asset;
- use it as explanatory evidence, not simply as a generic feed.

---

## 7. Fund Intelligence Scope

Turkish funds are a core product domain.

Potential event classes include:

- abnormal AUM change;
- abnormal investor-count change;
- price/NAV versus AUM divergence;
- asset-allocation change;
- peer/category divergence;
- risk-rating/profile changes where available;
- regulatory event;
- unusual concentration/exposure;
- fund ↔ underlying BIST relationship events in later phases.

SPK states that daily/consolidated fund data includes fund amount, share count, investor count, portfolio value, portfolio allocation and unit price. [S1]

### Important scope rule

Project 50K does not label a fund as fraudulent or a Ponzi scheme based on a score. It detects and explains observed risk/anomaly indicators.

---

## 8. Crypto Intelligence Scope

### MVP universe

A meaningful group of approximately 75–100 popular/liquid assets, subject to final data-provider constraints.

### Market scope

- price;
- volume;
- volatility;
- liquidity where available;
- cross-market relative behavior.

### On-chain scope

Initial network focus:

- EVM-compatible ecosystem;
- Solana.

Candidate signals:

- large transfer;
- holder concentration;
- exchange inflow/outflow;
- liquidity changes;
- connected-wallet activity;
- deployer/creator-wallet behavior;
- token unlock where data can be sourced reliably.

No attempt should be made in the hackathon to build a full chain-forensics platform.

---

## 9. U.S. Equity Scope

MVP universe should be limited to a high-liquidity subset, such as a NASDAQ-100-based or similar curated universe, finalized during Data Requirements work.

MVP capabilities may include:

- price/volume anomaly;
- selected fundamentals;
- earnings/news context;
- selected official filing context.

The purpose is to prove the common Equity Engine can operate beyond BIST, not to build a full U.S. institutional terminal in 54 hours.

---

## 10. Event Model

A central design decision is that Project 50K should store **events**, not merely alerts.

A normalized event should contain fields conceptually similar to:

```text
Event
- id
- asset_id
- asset_type
- event_type
- occurred_at
- detected_at
- severity
- confidence
- title_tr
- summary_tr
- evidence[]
- sources[]
- signal_ids[]
- model/method metadata
- status
- data_freshness
```

Notifications are delivery actions generated from events. This separation supports:

- event replay;
- de-duplication;
- re-ranking;
- multiple channels;
- auditing;
- feedback;
- later model evaluation.

---

## 11. Signal → Event Architecture

Signals are smaller observations.

Examples:

```text
SIGNAL: relative_volume = 6.8x
SIGNAL: return_zscore = 4.2
SIGNAL: sector_relative_return = +7.1pp
SIGNAL: material_disclosure_found = false
```

The event engine correlates signals into a user-facing event:

```text
EVENT: UNEXPLAINED_MARKET_MOVEMENT
SEVERITY: HIGH
CONFIDENCE: 0.91
```

This makes the system more explainable than asking one model to directly label raw data.

---

## 12. Severity Model

MVP levels:

### Medium

Worth knowing; does not justify interruptive cross-market communication.

### High

Strongly relevant to a watchlist user and may justify immediate communication depending on user preferences.

### Critical

Exceptional event with strong evidence and material potential relevance. May trigger market-wide communication even if the asset is outside the watchlist.

Severity measures **potential importance**, not certainty.

---

## 13. Confidence Model

Confidence measures **strength of evidence for the classification**.

A high-severity event can have moderate confidence, and a low/medium-severity event can have very high confidence.

Initial confidence factors may include:

- number of independent supporting signals;
- source reliability;
- data completeness;
- data freshness;
- cross-model/signal agreement;
- anomaly magnitude;
- historical calibration/validation results.

A detailed formula must not be invented before model evaluation. The eventual confidence system should be scientifically and empirically justified.

---

## 14. Notification Rules

### Watchlist assets

User selects a sensitivity level such as:

- Critical only
- High + Critical
- Medium + High + Critical

Exact labels in Turkish will be designed later.

### Non-watchlist assets

Only **Critical** market-wide events are eligible for proactive e-mail/in-app delivery.

Users must retain the ability to disable market-wide notifications.

### E-mail

- immediate for eligible High/Critical personal events;
- immediate for eligible Critical market-wide events;
- lower-priority information may be grouped into a digest.

### Browser push

Out of scope for MVP.

### Native push

Future mobile core feature.

---

## 15. Feedback Scope

Every intelligence event should support lightweight user feedback:

- `Faydalıydı`
- `Alakasızdı`

Potential future options:

- too frequent;
- too technical;
- explained poorly;
- event already known.

MVP feedback should be minimal but persist event/user outcome data for future ranking/model evaluation.

---

## 16. AI Behavior Requirements — Product-Level

Before the detailed AI Requirements document, the following principles are already locked:

1. AI may perform web research.
2. Material factual claims must be source-backed.
3. Official/regulatory sources receive higher evidentiary weight.
4. AI must distinguish observation from interpretation.
5. AI must be able to state that a cause cannot be established.
6. AI must not fabricate a causal explanation merely because an anomaly exists.
7. AI must not output personalized Buy/Hold/Sell instructions.
8. AI must not declare market manipulation as a legal fact based only on Project 50K signals.
9. Numerical facts should come from structured/deterministic data where possible.
10. LLM provider access should be abstracted behind an internal interface.

---

## 17. Language and Localization Principles

### User-facing product

- Turkish only for MVP;
- natural Turkish;
- established Turkish financial terminology;
- avoid literal translations of English fintech jargon;
- explain technical terms progressively.

Example:

Avoid:

> “Abnormal volume event detected.” → “Anormal hacim olayı tespit edildi.”

Prefer:

> **İşlem hacminde sıra dışı artış**

Avoid:

> “Disclosure mismatch.”

Prefer:

> **Fiyat hareketini açıklayabilecek yeni bir KAP bildirimi bulunamadı.**

### Engineering

- code identifiers in English;
- API fields in English;
- DB schema in English;
- prompts in English unless Turkish output examples are needed;
- documentation in English.

---

## 18. Design Principles

### Quality bar

UI quality is a product requirement.

### Desired character

> Financial intelligence terminal × editorial clarity × modern consumer product

### Avoid

- template-like fintech dashboard appearance;
- excessive glassmorphism;
- AI-style purple/blue gradients by default;
- glow-heavy crypto aesthetics;
- nested card containers;
- excessive status chips;
- weak typographic hierarchy;
- decorative complexity without functional value.

### Agentic-development rule

Frontend agents should receive product and design context, not vague instructions such as “make this beautiful”.

The team will use Impeccable during design implementation and review. Impeccable provides a `PRODUCT.md` / `DESIGN.md` workflow and automated checks intended to detect common AI-generated UI defaults. [S2]

A dedicated Design System / UX specification will later define:

- typography;
- spacing;
- color system;
- event severity treatment;
- data-visualization rules;
- responsive behavior;
- motion rules;
- accessibility;
- empty/error/loading states.

---

## 19. Technical Stack — Locked Direction for MVP

### Frontend

- Next.js 16.x (App Router)
- React
- TypeScript
- Tailwind CSS 4.x
- custom design tokens
- headless accessible UI primitives
- TradingView Lightweight Charts for primary financial charts
- Apache ECharts for selected analytical visualizations

### Backend

- Python
- FastAPI
- Pydantic
- provider/service architecture

### Data/ML

- Polars
- NumPy
- SciPy
- scikit-learn
- statsmodels
- additional anomaly methods chosen after literature review

### Persistence

- Supabase PostgreSQL
- pgvector for retrieval/semantic use cases

### Authentication

- Supabase Auth
- Google OAuth only for MVP
- cookie/SSR-compatible Next.js session handling
- server-side authorization for admin routes

Supabase publishes an official Next.js authentication quickstart, and its Google provider supports web and native applications, which also reduces migration friction when the mobile product is built later. [S3][S4]

### Jobs and cache

- Redis
- dedicated Python worker
- simple, reliable MVP scheduling rather than premature workflow-engine complexity

### E-mail

- transactional provider such as Resend

### Deployment

- Vercel — web
- Railway — FastAPI + worker
- Supabase — Postgres/Auth

### Error/operational visibility

At minimum:

- structured logs;
- health endpoints;
- ingestion timestamps;
- visible failed jobs in admin.

Full observability tooling can be added after MVP.

---

## 20. Provider-Abstraction Principle

Data access must be wrapped behind interfaces.

Example:

```text
MarketDataProvider
FundDataProvider
DisclosureProvider
RegulatoryProvider
NewsProvider
OnChainProvider
LLMProvider
EmailProvider
```

Hackathon implementations may use pragmatic libraries/APIs such as `borsapy`, but domain logic must not directly depend on provider-specific response structures.

This is particularly important because Borsa İstanbul data commercialization may require licensed-provider or direct contractual arrangements. Borsa İstanbul explicitly categorizes non-display use in surveillance/risk/investment-analysis systems and requires a direct data agreement for such use. [S5]

---

## 21. Public vs Private Data Principles

- Public asset intelligence can be visible without login.
- Personal watchlists, preferences, feedback, e-mail and chat history require authentication.
- Only data needed for product value should be collected.
- Sensitive credentials/API secrets remain server-side.
- Admin access must never rely only on hidden UI; authorization must be server-enforced.
- Source provenance should be stored with intelligence events.

Detailed privacy/security requirements will be written separately.

---

## 22. Non-Goals / Explicitly Out of Scope for MVP

- brokerage execution;
- Buy/Hold/Sell recommendations;
- personalized investment advice;
- automatic trading;
- portfolio cost basis and tax calculation;
- broker account connection;
- social-media monitoring;
- Telegram/X sentiment scraping;
- browser push;
- native iOS/Android applications;
- every global security;
- every blockchain;
- full order-book manipulation detection;
- legal finding of manipulation/fraud;
- production-grade BIST licensed data commercialization;
- complete admin configuration surface;
- fully automated model retraining.

---

## 23. Future Mobile Product

Mobile is not an optional side application. It is the intended long-term primary consumer surface for:

- immediate alerts;
- native push;
- watchlist status;
- daily brief;
- quick event investigation;
- conversational follow-up.

The web experience can remain the richer research surface.

Backend, database, authentication and event contracts must therefore avoid web-only assumptions.

---

## 24. Core Principles — Locked

1. **Proactive monitoring beats manual searching.**
2. **The event is the core unit of product value.**
3. **Signals must be inspectable.**
4. **Evidence comes before narrative.**
5. **AI is a reasoning layer, not decoration.**
6. **Objective calculations should remain deterministic where possible.**
7. **Confidence and severity are separate.**
8. **The user owns the investment decision.**
9. **No unsupported causal explanations.**
10. **Official sources receive priority.**
11. **Turkish language must sound native to Turkish investors.**
12. **BIST and funds are strategic depth areas.**
13. **Crypto requires on-chain context, not only candles.**
14. **Alert fatigue is a product failure.**
15. **Web MVP, mobile-first future.**
16. **Design craftsmanship is part of correctness.**
17. **Data providers must be replaceable.**
18. **Scientific literature and empirical backtesting will shape anomaly methodology.**

---

## 25. Sources

- **[S1] SPK — Portföy Değerleri:** https://www.spk.gov.tr/kurumlar/fonlar/yatirim-fonlari/menkul-kiymet-yatirim-fonlari/portfoy-degerleri
- **[S2] Impeccable:** https://impeccable.style/
- **[S3] Supabase — Auth with Next.js:** https://supabase.com/docs/guides/auth/quickstarts/nextjs
- **[S4] Supabase — Sign in with Google:** https://supabase.com/docs/guides/auth/social-login/auth-google
- **[S5] Borsa İstanbul — Veri Dağıtım ve Endeks Lisanslama:** https://www.borsaistanbul.com/sss/veri-dagitim-ve-endeks-lisanslama
