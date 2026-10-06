# Project 50K — Problem Analysis & Opportunity

**Document status:** Draft v0.1  
**Date:** 2026-10-02  
**Scope:** Problem space, opportunity framing, initial market hypotheses  

---

## 1. Purpose of This Document

This document defines the customer and market problems Project 50K is intended to solve. It deliberately avoids prematurely locking detailed functional requirements or model choices. The purpose is to ensure that later product, UX, AI, and engineering decisions remain connected to real user problems rather than becoming a collection of attractive fintech features.

---

## 2. Primary Problem Statement

Retail investors operate in an environment where relevant information is fragmented across many sources and arrives faster than a human can continuously evaluate it.

The central problem is not:

> “Investors do not have enough financial data.”

It is:

> **Investors cannot continuously determine which changes across market data, disclosures, financial statements, funds, news, regulation, and on-chain activity actually deserve attention.**

A user may have access to charts, KAP, TEFAS, financial news, company statements, crypto explorers and portfolio applications. Yet the user still has to perform the difficult cognitive work:

- notice that something unusual is happening;
- decide whether it is statistically meaningful;
- search for an explanation;
- judge source credibility;
- compare the event with the asset's historical behavior;
- understand whether the event is large relative to the company/fund;
- determine whether multiple signals reinforce one another;
- and decide whether further investigation is warranted.

Project 50K aims to automate much of this **monitoring and triage work**, while leaving the investment decision to the user.

---

## 3. Problem Category A — Information Fragmentation

### BIST example

A serious BIST investor may need to move among:

- price/volume charts;
- KAP;
- company financial statements;
- BIST index/sector data;
- SPK/BIST regulatory announcements;
- financial news;
- possibly broker or market-data tools.

These sources are individually useful. The missing layer is the **relationship among them**.

A 7% price increase means something different when:

- the sector is also up 7%;
- the company has just announced a material contract;
- volume is normal;
- volume is 8× normal;
- no public explanation can be found;
- a regulatory event has occurred;
- or several of these conditions happen simultaneously.

The investor often performs this correlation manually.

### Product opportunity

Create one normalized event model that can say:

> “The price and volume move are historically unusual, the stock is diverging from its sector, and no material public disclosure or trusted-news event has yet been identified.”

The value is the **combination**, not the individual data points.

---

## 4. Problem Category B — Alert Configuration Burden

Conventional alerts usually require the user to decide in advance what matters:

- notify me when price > X;
- notify me when daily change > Y%;
- notify me when RSI crosses a threshold;
- notify me when an article contains a keyword.

This assumes the user already knows which conditions will matter.

But a meaningful anomaly may be relative rather than absolute.

Examples:

- +3% may be extraordinary for one asset and normal for another;
- volume 2× average may matter in one market regime and be ordinary in another;
- a small fund-flow change may be important for a niche fund but immaterial for a large fund;
- a crypto transfer may only matter when combined with low liquidity and exchange inflow.

### Product opportunity

Project 50K should learn or calculate a context-specific baseline, then monitor deviation from that baseline automatically.

The user should not need to know which statistical condition to configure.

---

## 5. Problem Category C — Market Noise and Attention Scarcity

Financial products frequently compete by increasing the amount of content shown to the user:

- more charts;
- more indicators;
- more news;
- more screeners;
- more notifications.

For Project 50K, more content is not automatically better.

The product should optimize for:

> **important information per unit of user attention.**

This implies several requirements:

- events need severity;
- alerts need deduplication;
- related signals should be grouped into one event;
- watchlist events should be personalized;
- unsolicited market-wide alerts should require a very high threshold;
- lower-priority developments should be summarized in digests;
- evidence should be available without overwhelming the first screen.

---

## 6. Problem Category D — Weak Explanations of “Why This Matters”

A raw event is often not enough.

Example:

> “Company X signed a TRY 5.2bn contract.”

A retail investor still needs to know whether TRY 5.2bn is economically large for Company X.

A more useful intelligence product can compare the event with relevant context, for example:

- trailing revenue;
- market capitalization;
- order backlog, if reliable data is available;
- prior similar disclosures;
- current sector conditions.

Similarly, a fund's allocation changing from 40% to 70% equities is more meaningful than displaying two isolated allocation snapshots.

### Product opportunity

Use deterministic financial calculations plus AI-based semantic interpretation to convert information into **contextual materiality**.

---

## 7. Problem Category E — Trust and Source Quality

AI creates a new failure mode in finance: a fluent explanation may sound credible even when evidence is weak or wrong.

Project 50K therefore needs an explicit evidence hierarchy.

### Proposed evidence hierarchy

**Tier 1 — Regulatory and official**

- SPK
- KAP
- Borsa İstanbul
- TEFAS / official fund data
- SEC / official filings

**Tier 2 — Issuer-originated**

- investor-relations disclosures;
- official company announcements.

**Tier 3 — Trusted financial journalism/data providers**

- approved sources selected during Data Requirements work.

**Tier 4 — Other credible public sources**

Used cautiously and clearly attributed.

**Future — Social/community data**

X, Telegram, Reddit and similar sources are outside the hackathon MVP due to data-access, reliability and noise concerns.

### Product opportunity

Make evidence provenance visible rather than hiding it behind the AI response.

---

## 8. Problem Category F — Investment-Fund Intelligence in Türkiye

Investment funds are a particularly strong problem space for Project 50K.

SPK states that daily and consolidated fund information includes amount, share count, investor count, portfolio value, portfolio allocation and unit price, with TEFAS and a portfolio-value web service made available for fund data. [S1]

This creates an unusually rich base for consumer intelligence such as:

- abnormal growth or decline in fund size;
- unusual investor-count changes;
- NAV movement versus AUM movement;
- large allocation changes;
- category/peer divergence;
- concentration changes;
- regulatory-status changes;
- relationships between fund holdings and unusual BIST behavior.

### Current relevance

On 23 September 2026, SPK stated that 131 funds belonging to seven portfolio-management companies were subject to liquidation decisions dated 17 September, and that MKK records showed 455,758 unique investors in these funds. [S2]

On 18 September 2026, SPK explained that work on the investment-fund guide followed observations, particularly involving free investment funds and money-market funds, where certain funds of specific portfolio-management companies had caused price movements in low-free-float shares that could not be explained by economic reality and fundamental financial metrics. [S3]

On 28 September, SPK stated that the funds had been closed to TEFAS buy/sell transactions as of 17 September and described further liquidation mechanics. [S4] On 1 October, SPK introduced an interim-payment mechanism for certain investors in funds undergoing liquidation, with payments capped at TRY 1 million per investor per fund under the stated mechanism. [S5]

Project 50K must not imply that these outcomes could necessarily have been predicted. The opportunity is narrower and defensible:

> **Retail investors need better visibility into unusual fund behavior, fund-market relationships, regulatory events and changes that deserve investigation.**

---

## 9. Problem Category G — Market/Fund Relationship Blind Spots

A strong long-term differentiator is cross-entity intelligence.

Traditional asset pages are organized around one instrument at a time. However, some financially important questions are relational:

- Which funds have meaningful exposure to this BIST stock?
- Has a fund's allocation to a small-float stock increased materially?
- Are several funds changing exposure in the same direction?
- Did unusual fund behavior precede or coincide with unusual equity behavior?
- Are fund flows and portfolio composition telling a different story from NAV performance?

This suggests a future graph model:

```text
Fund ──holds──> Security
Fund ──managed_by──> Portfolio Management Company
Security ──belongs_to──> Sector
Security ──disclosed──> KAP Event
Entity ──subject_to──> Regulatory Event
Event ──reported_by──> Source
```

A graph-oriented data model is not mandatory for the hackathon, but the conceptual relationship should shape future architecture.

---

## 10. Problem Category H — Crypto Fragmentation

Crypto adds a second data dimension beyond traditional market data: the blockchain itself.

A user may need to combine:

- price;
- volume;
- liquidity;
- holder distribution;
- major-wallet activity;
- exchange inflows/outflows;
- contract properties;
- token unlocks;
- trusted news.

Individual tools solve pieces of this problem, but the user still has to decide whether signals are connected.

### Product opportunity

Use a shared cross-asset event model while allowing asset-class-specific detectors.

For example:

```text
Market anomaly
+ abnormal exchange inflow
+ major-holder transfer
= Multi-signal crypto event
```

The product does not need to call the asset a scam. It needs to show the unusual evidence and its confidence.

---

## 11. Problem Category I — U.S. Market Information Overload

U.S. equities have abundant data. That abundance creates a similar monitoring problem:

- earnings;
- SEC filings;
- insider activity;
- analyst revisions;
- company news;
- macro events;
- sector rotation;
- price/volume behavior.

The strategic reason to include U.S. equities is not to compete immediately with the deepest global research terminals. It is to give Turkish investors one monitoring model across the major asset classes they already follow.

For the MVP, U.S. coverage should be intentionally narrow.

---

## 12. User Jobs To Be Done

### Job 1 — Detect

> “Tell me when something genuinely unusual happens in an asset I follow.”

### Job 2 — Prioritize

> “Tell me which of today's developments deserve attention first.”

### Job 3 — Explain

> “Explain why the event was flagged in language I can understand.”

### Job 4 — Verify

> “Show me the evidence and the original sources.”

### Job 5 — Investigate

> “Let me ask follow-up questions without manually searching five websites.”

### Job 6 — Discover

> “Tell me about truly critical market events even when the asset is not already on my watchlist.”

### Job 7 — Reduce routine monitoring

> “Do the repetitive checking for me so I can spend time deciding rather than searching.”

---

## 13. Why Existing Tool Categories Do Not Fully Solve This

This is a preliminary product-discovery conclusion, not a final competitor study.

Strong products already exist in each adjacent category:

- charting and screening;
- Turkish equity/fund research;
- brokerage and multi-asset access;
- global market terminals;
- crypto on-chain intelligence;
- unusual-options/market-activity tools;
- news aggregation.

The opportunity is not that these capabilities do not exist.

The opportunity is that the workflow remains fragmented and usually **user-driven**:

> search → inspect → compare → interpret → decide whether it matters.

Project 50K proposes a **system-driven monitoring workflow**:

> detect → correlate → investigate → notify → explain.

A dedicated competitor-analysis document must test whether this difference is meaningful and defensible in Türkiye.

---

## 14. Why Now

Several factors make the opportunity timely:

### Data availability

Public/accessible sources exist for Turkish fund, regulatory, disclosure, market and financial information. SPK explicitly provides or links to daily consolidated fund data and a portfolio-value web service. [S1]

### Recent fund-market attention

The 2026 SPK actions and explanations show that fund structure, transparency, investor protection, low-free-float shares and unusual price behavior are active current issues rather than theoretical concerns. [S2][S3][S4][S5]

### LLM capability

Modern language models can now add semantic reasoning over disclosures, news and cross-source evidence, enabling an intelligence layer that was difficult to build with keyword rules alone.

### Consumer expectations

Users increasingly expect software to monitor, summarize, prioritize and explain proactively rather than merely provide raw tools.

### Cross-asset behavior

Turkish retail investors often follow more than one asset class. A unified intelligence model can provide more value than separate monitoring apps if the product remains focused and avoids becoming another generic super-app.

---

## 15. Opportunity Statement

> **Create the default “attention layer” between Turkish retail investors and the financial markets they follow.**

The product does not need to replace every data terminal. It needs to become the first place users check to answer:

> “Is there anything I need to know?”

That is a narrower and potentially stronger position than trying to become the best charting platform, broker, news site, or screener simultaneously.

---

## 16. Initial Differentiation Hypotheses

These are hypotheses to validate, not established competitive advantages.

### H1 — Turkey-first cross-source intelligence

BIST + KAP + SPK + TEFAS + fund relationships can create a locally differentiated dataset and event model.

### H2 — Fund anomaly intelligence

Fund behavior is under-served relative to equity charting and can be a meaningful local wedge.

### H3 — Proactive anomaly detection

Automatically identifying unusual behavior can reduce the setup burden of conventional alerts.

### H4 — Evidence-first AI

Visible sources, explicit uncertainty and deterministic evidence can generate greater trust than a generic financial chatbot.

### H5 — Cross-asset consistency

One mental model for BIST, funds, crypto and U.S. equities may be valuable to Turkish investors with diversified interests.

### H6 — Mobile retention

If alerts are sufficiently relevant and low-noise, the future mobile application may have strong recurring engagement characteristics.

---

## 17. Core Risks to Product-Market Fit

### False-positive fatigue

If too many events are flagged, users will stop trusting alerts.

### Weak differentiation

If the product becomes “charts + news + AI summary”, incumbents can replicate the experience easily.

### Insufficient evidence

If public data cannot support the desired event classification, explanations may be shallow.

### Overly broad scope

Serving beginners, active traders, four asset classes, chat, research and alerts could dilute the initial experience.

### Data licensing/cost

BIST production use is a material business constraint. Borsa İstanbul states that non-display use, including surveillance, risk-management and investment-analysis services, requires a direct data agreement. [S6]

### Legal/product language

Statements such as “this stock is manipulated” or personalized investment recommendations would create materially different risk. The product should remain an evidence-backed intelligence layer.

### LLM trust

A fluent but unsupported answer could damage user trust. Source citation and explicit uncertainty are mandatory product behaviors.

---

## 18. Open Research Questions

The next analysis phases should answer:

1. Which anomaly classes have strong empirical support in financial literature?
2. Which models perform reliably under non-stationary financial time series?
3. How should anomaly severity be calibrated across different assets?
4. How should confidence be calibrated and evaluated?
5. Which signals produce unacceptable false-positive rates?
6. How can news/disclosure materiality be objectively benchmarked?
7. Which Turkish fund behaviors can be computed reliably with available data?
8. How complete and timely are fund allocation and investor-count histories?
9. Which BIST market-data license path is commercially viable post-MVP?
10. Which trusted-news sources can be legally integrated and summarized?
11. Which on-chain data provider mix offers sufficient EVM/Solana coverage?
12. What alert frequency will users tolerate before disengaging?
13. Does the product create more value for beginners, intermediates or active investors first?
14. Will users trust a confidence score, and what explanation must accompany it?

---

## 19. Validation Plan

Before treating any hypothesis as validated, the team should collect evidence through:

- user interviews during/after Startup Weekend;
- clickable/prototype tests;
- historical event replay;
- anomaly-model precision/recall evaluation on curated event datasets;
- alert usefulness feedback (`Faydalıydı` / `Alakasızdı`);
- observation of search/watchlist behavior;
- event-open and source-open rates;
- later retention and notification metrics.

The hackathon's goal is not to prove full product-market fit. It is to demonstrate that the core loop is technically credible and intuitively valuable.

---

## 20. Sources & Evidence

- **[S1] SPK — Portföy Değerleri:** https://www.spk.gov.tr/kurumlar/fonlar/yatirim-fonlari/menkul-kiymet-yatirim-fonlari/portfoy-degerleri
- **[S2] SPK — Tasfiye Konusu Fonlardaki Yatırımcı Sayısına İlişkin Açıklama, 23 Sep 2026:** https://www.spk.gov.tr/duyurular/basin-duyurulari/2026/tasfiye-konusu-fonlardaki-yatirimci-sayisina-iliskin-aciklama
- **[S3] SPK — Yatırım Fonlarına İlişkin Rehber Düzenleme Süreci Açıklaması, 18 Sep 2026:** https://spk.gov.tr/duyurular/basin-duyurulari/2026/yatirim-fonlarina-iliskin-rehber-duzenleme-surecine-iliskin-aciklama
- **[S4] SPK — Tasfiye Süresine İlişkin Basın Duyurusu, 28 Sep 2026:** https://spk.gov.tr/duyurular/basin-duyurulari/2026/tasfiye-suresine-iliskin-basin-duyurusu
- **[S5] SPK — Tasfiyedeki Fonlara İlişkin Ara Ödeme Duyurusu, 1 Oct 2026:** https://spk.gov.tr/duyurular/basin-duyurulari/2026/tasfiyedeki-fonlara-iliskin-ara-odeme-duyurusu
- **[S6] Borsa İstanbul — Veri Dağıtım ve Endeks Lisanslama:** https://www.borsaistanbul.com/sss/veri-dagitim-ve-endeks-lisanslama
