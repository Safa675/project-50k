# Project 50K — Techstars Startup Weekend MVP Scope

**Document status:** Draft v0.1  
**Event:** Techstars Startup Weekend Urla by Techstars Istanbul  
**Event dates:** 9–11 October 2026  
**Team size:** 3  
**Delivery requirement:** Working prototype for jury presentation  

---

## 1. MVP Objective

The hackathon objective is **not** to build the complete Project 50K product.

The objective is to prove one coherent product thesis:

> **A system can continuously monitor multiple financial data sources, detect a meaningful unusual event, investigate the surrounding context with AI, explain why it matters in natural Turkish, show its evidence, and notify a retail investor — without requiring the investor to configure the exact anomaly rule in advance.**

If the prototype proves this loop credibly and looks like a product people could imagine using, the MVP has succeeded.

---

## 2. Event Constraints

The event schedule creates a practical constraint stricter than “54 hours”.

### Friday, 9 October

- 17:00–17:30 Registration/networking
- 17:30–19:00 Idea presentations and team formation
- 19:00–20:00 Dinner
- 20:00–21:00 Lean Canvas training
- 21:00–22:00 Work begins

### Saturday, 10 October

- 09:00–10:00 Breakfast
- 10:00–11:00 Idea validation training
- 11:00–12:30 Work
- 12:30–14:00 Lunch
- 14:00–18:00 Mentor meetings
- 18:00–19:00 Jury-presentation training
- 19:00–20:00 Dinner
- 20:00 onward Work

### Sunday, 11 October

- 09:00–10:00 Breakfast
- 10:00–12:30 Work
- 12:30–13:30 Lunch
- 13:30–16:00 Final-presentation preparation
- 17:00–19:00 Jury presentations
- 20:00–22:00 Awards/closing

### Operational conclusion

The **core product must work by Saturday night**.

Sunday morning is for:

- integration fixes;
- demo preparation;
- data validation;
- design polish;
- deployment verification;
- pitch preparation.

Sunday afternoon should not depend on major feature development.

---

## 3. Team Model

### Role A — Engineering + Business Analysis

Primary responsibilities:

- architecture;
- repository setup;
- backend/API;
- database;
- authentication;
- data ingestion;
- anomaly/event engine;
- AI integration;
- deployment/integration;
- requirements discipline.

### Role B — Business Development + Marketing

Primary responsibilities:

- customer/problem validation;
- competitor validation;
- user interviews;
- value-proposition testing;
- landing-page messaging;
- business model hypotheses;
- pitch narrative;
- market sizing research where useful;
- evidence collection for problem urgency.

### Role C — UI/UX + Visual Design

Primary responsibilities:

- product flow;
- visual direction;
- design tokens;
- landing-page design;
- dashboard/asset-page design;
- responsive behavior;
- pitch visuals;
- implementation review;
- design quality gate.

### Cross-functional rule

The three roles should not become silos. The designer should review implemented UI continuously; the business role should test the prototype and copy; the engineer should expose technical constraints early.

---

## 4. MVP Product Surface

The MVP is a **responsive web application**.

Long-term vision remains a **mobile-first consumer product**, but mobile-native development is intentionally excluded from the weekend.

The deployed web MVP should work well on both a laptop and a phone-sized viewport so that it already communicates the eventual mobile direction.

---

## 5. MVP User Journey

A complete demo-quality flow should be:

1. Visitor lands on Project 50K.
2. Landing page explains the product in one screen.
3. Visitor searches an asset without authentication.
4. Visitor opens an asset page and sees chart + intelligence events.
5. A historical anomaly is shown directly on the timeline.
6. The user opens the event and sees:
   - severity;
   - confidence;
   - deterministic evidence;
   - official/trusted sources;
   - AI explanation.
7. User signs in with Google.
8. User adds the asset to their watchlist.
9. Personal dashboard shows watchlist intelligence and market-wide highlights.
10. User opens the asset assistant and asks a contextual question.
11. Assistant answers in Turkish with sources.
12. An in-app notification or demo e-mail demonstrates the alert system.

This single journey proves most of the product thesis.

---

## 6. P0 — Must Work for the Jury

### 6.1 Landing Page

Must:

- communicate problem/value proposition;
- look intentionally designed;
- contain prominent asset search;
- explain supported markets at a high level;
- show one compelling example intelligence event;
- provide Google sign-in CTA.

### 6.2 Universal Asset Search

Must support at least selected:

- BIST;
- funds;
- crypto;
- U.S. equities.

It does not need the full production universe if the search behavior is architecturally correct.

### 6.3 Google Authentication

- Google OAuth only;
- no password flows;
- anonymous browsing allowed;
- authenticated watchlist/personal features.

### 6.4 Watchlist

- add/remove asset;
- persist to user account;
- populate personal feed.

No quantity/cost basis.

### 6.5 Personal Intelligence Dashboard

Must show:

- `Portföyünde / Takip Listende Önemli Gelişmeler` style personalized section;
- watchlist events;
- `Piyasada Öne Çıkanlar` section;
- severity;
- confidence;
- compact evidence indicators;
- natural Turkish copy.

Final Turkish wording will be refined in UX work.

### 6.6 BIST Asset Page — Deepest MVP Asset

Must demonstrate:

- intraday or replayable price chart;
- volume data;
- at least one meaningful anomaly class;
- KAP/news/context evidence;
- event timeline/marker;
- source-backed AI explanation.

### 6.7 Fund Asset Page — Strategic Showcase

Must demonstrate at least two fund-specific metrics and one fund-specific anomaly, such as:

- NAV history;
- AUM/fund-size data;
- investor-count data if reliably available;
- allocation history/change;
- peer divergence;
- abnormal fund-size/flow proxy.

A compelling fund case is strategically important because it distinguishes Project 50K from a generic stock-alert product.

### 6.8 Crypto Asset Page — Cross-Asset Proof

Must demonstrate:

- price/volume anomaly;
- at least one on-chain signal or prepared on-chain event;
- combined event explanation.

The hackathon does not require comprehensive chain forensics.

### 6.9 U.S. Equity Page — Architecture Proof

Minimum:

- chart;
- price/volume anomaly;
- selected contextual event/news.

It should prove the common engine can support another equity market.

### 6.10 Event Detail

Every showcased event must include:

- event title;
- time;
- severity;
- confidence;
- “why detected” explanation;
- numerical evidence;
- sources;
- feedback buttons.

### 6.11 AI Asset Assistant

Must:

- know which asset page it is on;
- answer at least several real questions;
- use project data plus web/source research;
- cite material facts;
- answer in natural Turkish;
- be able to say that a cause cannot be established;
- avoid Buy/Hold/Sell recommendations.

### 6.12 In-App Notifications

At least one event should appear in a notification center or unread state.

### 6.13 E-mail Demonstration

At least one alert e-mail flow should work end-to-end or be demonstrably triggerable in the jury environment.

### 6.14 Minimal Admin Dashboard

Must not become a CRUD project.

P0 admin can be limited to:

- user count;
- watchlist count;
- event count;
- recent high/critical events;
- data-source/ingestion freshness;
- one or two configurable thresholds/feature flags.

Admin access: approved Google-account allowlist + server-side role check.

### 6.15 Deployment

A jury-accessible deployed URL is strongly preferred.

---

## 7. P1 — Should Build If Core Loop Is Stable

- e-mail preference UI;
- three alert-sensitivity modes;
- event history filtering;
- richer fund comparison;
- richer U.S. equity coverage;
- more on-chain signal types;
- daily digest generation;
- admin e-mail/job metrics;
- richer empty/loading/error states;
- additional historical replay cases;
- saved AI chat history UI.

---

## 8. P2 — Explicit Stretch Goals

- advanced fund ↔ underlying-stock relationship visualization;
- graph visualization of fund/security/entity relationships;
- multiple correlated on-chain wallets;
- sophisticated explainable ML visualizations;
- dynamic model threshold editing;
- automated benchmark reports;
- mobile-app prototype beyond responsive web;
- additional global exchanges.

P2 work must never jeopardize P0 demo reliability.

---

## 9. Explicitly Do Not Build During the Weekend

- native iOS app;
- native Android app;
- browser push;
- broker integrations;
- transaction execution;
- average-cost/P&L accounting;
- tax features;
- X/Telegram/Reddit monitoring;
- a full financial-data warehouse;
- every BIST/TEFAS/crypto/U.S. instrument if providers make this costly;
- a custom foundation model;
- order-level manipulation detection;
- a legally assertive “manipulation score”;
- a complex microservices platform;
- a generic CMS;
- a complete production-grade RBAC system.

---

## 10. Hackathon Data Strategy

### Principle

Use the fastest legally/technically practical sources to prove the product, while preserving provider abstraction.

### BIST

Hackathon candidate:

- `borsapy` for pragmatic BIST OHLCV/financial/KAP integration;
- direct official sources where appropriate;
- historical data cached locally/database-side for demo reliability.

Production licensing must be treated separately. Borsa İstanbul states that market data is distributed through licensed distributors and that non-display use, including surveillance/risk/investment-analysis systems, requires a direct data agreement. [S1][S2]

### Funds

Candidate:

- TEFAS data through `borsapy` and/or a dedicated TEFAS client;
- SPK official fund information;
- pre-cache selected demo funds.

SPK states that daily fund amount, share count, investor count, portfolio value, allocation and unit-price information can be accessed/visualized and links to its portfolio-value web service. [S3]

### Crypto

- market API for selected 75–100 popular/liquid assets;
- EVM and Solana data through a practical API/provider;
- preselect one high-quality historical on-chain demo case.

### U.S.

- limited liquid universe;
- pragmatic market-data source;
- official SEC/source context where useful;
- no need for institutional-depth coverage.

### News

Only trusted sources. Do not build a general news scraper as the core weekend project.

---

## 11. Historical Replay Strategy

The strongest jury demonstration should not depend on a major anomaly randomly occurring during the presentation.

Use **historical replay** for proof, while also showing that current data ingestion works.

### Required replay cases

At least:

1. **BIST case** — unusual price/volume plus KAP/news context.
2. **Fund case** — unusual size/investor/allocation/peer behavior.
3. **Crypto case** — price/volume plus an on-chain signal.

Optional:

4. U.S. equity event.

### Replay UX

The asset chart can visually mark:

- anomaly timestamp;
- disclosure/news timestamp;
- event window;
- supporting metric changes.

The jury should be able to see that the event engine is based on real historical inputs rather than a hard-coded text card.

---

## 12. Minimal Anomaly Engine for MVP

Do not attempt to implement the final research-grade engine during the weekend.

A credible baseline can combine:

- rolling returns;
- robust z-score or similar historical deviation measure;
- relative volume;
- rolling volatility;
- sector/index relative return;
- simple fund change metrics;
- selected on-chain event thresholds;
- deterministic event correlation.

Example BIST event logic:

```text
IF
  return_anomaly is high
  AND relative_volume is high
  AND sector_relative_move is high
THEN
  create candidate event

AI investigation:
  search KAP + trusted news around event window

IF material explanation found:
  classify as explained material event
ELSE:
  classify as unexplained unusual market movement
```

This logic is sufficient for a hackathon if evidence is real and the explanation is strong.

### Scientific caveat

Thresholds used during the weekend are prototype thresholds. The production anomaly engine must later be redesigned using literature review, backtesting, calibrated evaluation, false-positive analysis and confidence calibration.

---

## 13. AI-Native MVP Requirements

The AI component must do visible, non-trivial work.

### Required AI tasks

- read/classify a disclosure or trusted article;
- identify possible explanatory events for an anomaly;
- synthesize market + disclosure/news evidence;
- generate a concise Turkish event explanation;
- answer an asset-specific question with citations;
- communicate uncertainty.

### Not acceptable as the only AI feature

> “Send event JSON to an LLM and ask it to rewrite the text.”

That would make the product AI-enhanced, not AI-native.

---

## 14. Confidence — MVP Implementation

The final confidence model is a research topic. The hackathon needs a transparent prototype, not false precision.

A provisional confidence calculation may combine normalized components such as:

- deterministic-signal strength;
- number of independent signals;
- evidence/source quality;
- freshness/completeness;
- cross-source agreement.

The UI can show a percentage, but an event detail should explain the underlying reason in plain language.

The percentage must not be represented as a probability that manipulation/fraud occurred.

---

## 15. UI/Design Quality Plan

The product must not look like a generic generated hackathon dashboard.

### Workflow

```text
Product intent
→ UX structure
→ visual direction
→ design tokens
→ implementation
→ Impeccable audit
→ designer critique
→ polish
```

Impeccable explicitly supports storing product context in `PRODUCT.md`, recording the visual system in `DESIGN.md`, and detecting recurring AI-generated UI patterns. [S4]

### Friday design deliverables

Before heavy frontend implementation, define:

- visual reference/mood direction;
- typography;
- base surfaces;
- primary/secondary text hierarchy;
- severity treatment;
- chart treatment;
- spacing scale;
- border/radius philosophy;
- core component examples;
- mobile breakpoints/priority behavior.

### Important rule

Do not hand an agent the prompt “make a modern fintech dashboard.”

Give the agent explicit product context and design constraints.

---

## 16. Recommended Technical Stack

### Web

- Next.js 16.x App Router
- React + TypeScript
- Tailwind CSS 4.x
- custom design system/tokens
- headless accessible primitives
- TradingView Lightweight Charts
- ECharts where required

### API / Intelligence

- Python
- FastAPI
- Pydantic
- Polars / NumPy / SciPy / scikit-learn / statsmodels

### Persistence/Auth

- Supabase PostgreSQL
- Supabase Auth
- Google OAuth only
- pgvector when semantic retrieval is useful

Supabase provides official Next.js Auth guidance and direct Google-provider integration. [S5][S6]

### Jobs/cache

- Redis
- dedicated Python worker
- simple scheduler suitable for the weekend

### Messaging

- Resend or equivalent transactional e-mail provider

### Deploy

- Vercel — frontend
- Railway — API + worker
- Supabase — DB/Auth

### Repository

Recommended monorepo:

```text
project-50k/
├── apps/
│   ├── web/
│   └── api/
├── workers/
│   ├── ingestion/
│   └── intelligence/
├── packages/
│   ├── contracts/
│   ├── design-system/
│   └── config/
├── research/
├── docs/
└── infra/
```

---

## 17. Suggested Implementation Timeline

### Before the event, without implementing the startup itself

Because the event requires a previously unworked startup idea, respect event rules. Preparation should focus on research, documentation, account/API readiness, design references and understanding tools rather than building the actual prototype in advance.

Useful preparation:

- confirm API/account access;
- understand deployment flow;
- finalize requirements;
- conduct literature/competitor research;
- prepare non-product-specific coding environment;
- ensure Google OAuth configuration can be completed quickly;
- understand Impeccable workflow.

### Friday night — Foundation

Goal by end of Friday:

- final value proposition;
- repo initialized;
- architecture locked;
- database schema baseline;
- auth spike working or nearly working;
- one BIST/fund data source successfully fetched;
- design direction defined;
- landing skeleton started.

### Saturday morning — Core data + product shell

- authentication complete;
- search data model;
- watchlist CRUD;
- asset page shell;
- ingestion service;
- historical dataset cached;
- first deterministic anomaly detector working.

### Saturday afternoon — Intelligence loop

- event model;
- BIST historical anomaly replay;
- fund anomaly case;
- AI investigation/context;
- citations/sources;
- personal/public feed integration.

Mentor meetings should be used to validate:

- product positioning;
- fund USP;
- user comprehension;
- business model;
- notification value;
- legal language.

### Saturday evening/night — End-to-end product

Before stopping Saturday:

- full primary demo flow works;
- deployed environment exists;
- at least BIST + fund cases are reliable;
- AI assistant works;
- in-app notification works;
- e-mail path works or is very close;
- design is coherent enough that Sunday is polish, not rescue.

### Sunday morning — Freeze and polish

- integrate crypto demo;
- optional U.S. proof;
- admin minimal view;
- fix bugs;
- verify citations;
- test Google login;
- test on clean browser/account;
- responsive pass;
- run Impeccable audit;
- designer polish;
- prepare demo fallback.

### Sunday 13:30 — Feature freeze

After this point:

- no architectural changes;
- no new ambitious features;
- pitch/rehearsal/demo reliability only.

---

## 18. Demo Reliability Plan

Hackathon demos fail when they depend entirely on live third-party APIs.

The application should support:

### Live/current mode

Shows that ingestion and current data work.

### Historical replay mode

Uses cached, real historical data for selected events.

### Fallback snapshot

If an upstream provider fails during the jury presentation, selected real data should already be stored in the database so the event and evidence can still be demonstrated.

The fallback must not misrepresent synthetic data as live.

---

## 19. Demo Storyline

A strong sequence:

### Scene 1 — Problem

“An investor follows BIST, funds and crypto. The data exists, but the investor has to continuously search and decide what matters.”

### Scene 2 — Dashboard

Open personal dashboard:

> “Takip ettiğin varlıklarda bugün 2 önemli gelişme var.”

### Scene 3 — BIST event

Open BIST stock:

- chart anomaly;
- abnormal volume;
- sector comparison;
- KAP/news investigation;
- severity + confidence;
- evidence.

### Scene 4 — AI follow-up

Ask:

> “Bu hareketi açıklayan doğrulanmış bir gelişme var mı?”

AI responds with sources or explicitly says it cannot establish one.

### Scene 5 — Fund differentiation

Open fund:

- show abnormal fund metric/allocation;
- demonstrate a fund-specific intelligence event.

This is important for differentiation.

### Scene 6 — Cross-asset proof

Briefly show crypto event with an on-chain signal.

### Scene 7 — Product vision

Explain that the weekend build is web, while the long-term consumer product is mobile-first because the core use case is proactive alerts.

---

## 20. Acceptance Criteria

The MVP is demo-ready only if all of the following are true:

### Product

- [ ] Landing page communicates value in under ~30 seconds.
- [ ] Anonymous asset search works.
- [ ] Google login works.
- [ ] Watchlist persists.
- [ ] Personal feed displays watchlist intelligence.
- [ ] Market-wide highlights exist.
- [ ] BIST event flow works end-to-end.
- [ ] Fund event flow works end-to-end.
- [ ] Crypto cross-asset example works.
- [ ] U.S. example exists if time permits without risking core demo.
- [ ] Event has severity + confidence + evidence + sources.
- [ ] Feedback button persists.
- [ ] Asset chat answers with citations.
- [ ] AI can admit insufficient evidence.
- [ ] No Buy/Hold/Sell recommendation appears.
- [ ] In-app notification exists.
- [ ] E-mail demo works.
- [ ] Minimal admin route is protected and useful.

### Engineering

- [ ] Deployed URL works.
- [ ] Secrets are server-side.
- [ ] Admin authorization is server-enforced.
- [ ] Data-source failures do not crash the full application.
- [ ] Demo historical data is cached.
- [ ] Event source/provenance is stored.
- [ ] Current data freshness is visible internally.

### Design

- [ ] Works on jury laptop resolution.
- [ ] Works acceptably on a phone viewport.
- [ ] No generic template aesthetic.
- [ ] Typography/hierarchy is coherent.
- [ ] Severity is understandable without excessive color dependence.
- [ ] Loading/error/empty states exist for core screens.
- [ ] Impeccable audit performed.
- [ ] Designer performs final critique pass.

---

## 21. Hackathon Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| Data API fails | High | Cache selected historical/current data; provider abstraction |
| Scope explosion | Critical | P0/P1/P2 discipline; BIST + fund depth first |
| AI hallucination | High | source-backed answers, structured context, explicit unknown response |
| Weak anomaly demo | Critical | curated historical replay cases |
| Generic UI | Medium/High | designer-led system + Impeccable quality gate |
| Google OAuth delay | Medium | configure early Friday/Saturday morning |
| E-mail configuration failure | Medium | test early; have visible in-app alert as fallback |
| Too many alerts | Medium | simple severity thresholds and dedupe |
| Fund data gaps | High | validate demo funds before finalizing storyline |
| On-chain complexity | Medium | one strong signal/case rather than full forensics |
| BIST licensing question from jury | Medium | explain MVP/demo source vs production licensed-provider strategy clearly |
| No live anomaly during demo | Critical | historical replay is primary proof; live mode is secondary |

---

## 22. Jury Positioning

The project should not be pitched as:

> “An AI app for investing.”

Nor:

> “A TradingView competitor.”

Nor:

> “A manipulation detector.”

A stronger positioning is:

> **Project 50K is an AI-native market intelligence and early-warning system for retail investors. It continuously monitors market behavior, funds, disclosures, trusted news and on-chain signals; detects unusual multi-signal events; and explains what deserves attention with evidence.**

For Türkiye, emphasize:

> **BIST + TEFAS/funds + KAP/SPK intelligence**

as the local wedge.

---

## 23. Post-Hackathon Direction

If the prototype validates well, the next sequence should be:

1. scientific literature review;
2. formal Anomaly Catalog;
3. user personas;
4. user requirements;
5. functional requirements;
6. data-provider/legal analysis;
7. calibrated backtesting/evaluation;
8. mobile product design;
9. production BIST data licensing/provider decision;
10. closed beta.

---

## 24. Sources

- **[S1] Borsa İstanbul — Veri Yayını:** https://www.borsaistanbul.com/veriler/veri-yayini
- **[S2] Borsa İstanbul — Veri Dağıtım ve Endeks Lisanslama:** https://www.borsaistanbul.com/sss/veri-dagitim-ve-endeks-lisanslama
- **[S3] SPK — Portföy Değerleri:** https://www.spk.gov.tr/kurumlar/fonlar/yatirim-fonlari/menkul-kiymet-yatirim-fonlari/portfoy-degerleri
- **[S4] Impeccable:** https://impeccable.style/
- **[S5] Supabase — Auth with Next.js:** https://supabase.com/docs/guides/auth/quickstarts/nextjs
- **[S6] Supabase — Sign in with Google:** https://supabase.com/docs/guides/auth/social-login/auth-google
