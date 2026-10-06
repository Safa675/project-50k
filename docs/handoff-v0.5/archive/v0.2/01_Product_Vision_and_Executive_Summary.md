# Project 50K — Product Vision & Executive Summary

**Document status:** Draft v0.1  
**Date:** 2026-10-02  
**Working codename:** Project 50K  
**Primary market:** Türkiye  
**Primary product language:** Turkish (`tr-TR`)  
**Internal documentation, code, prompts, API contracts:** English  

---

## 1. Executive Summary

Project 50K is an AI-native investment intelligence and anomaly-monitoring product for retail investors in Türkiye. It is designed to continuously monitor financial markets on the user's behalf, identify unusual or materially important developments, correlate evidence across multiple sources, and explain what is happening in clear, natural Turkish.

The product is not intended to be another charting terminal, broker, portfolio accounting tool, news reader, or generic investment chatbot. Its core job is to answer a more valuable question:

> **What is happening in the assets I care about — and what deserves my attention right now?**

Project 50K will initially focus on four asset classes, in this priority order:

1. **Borsa İstanbul (BIST) equities**
2. **Turkish investment funds**
3. **Crypto assets**
4. **U.S. equities**

The Turkey-first product advantage is expected to come from combining BIST market behavior with KAP disclosures, SPK/regulatory information, TEFAS/fund data, financial statements, reliable news, and — where relevant — relationships between investment funds and the equities they hold.

For crypto assets, the system will extend the same intelligence model with market data and on-chain signals. For U.S. equities, it will combine market/fundamental data with disclosures, earnings, regulatory filings, and trusted news.

The long-term consumer product is **mobile-first**, because the strongest user value is proactive, time-sensitive awareness. However, the Techstars Startup Weekend MVP will be a **responsive web application** because it offers the fastest path to a polished, deployable prototype, rich financial visualization, reliable demo execution, and later reuse as the product's research-oriented web experience.

---

## 2. Vision

### Vision statement

> **Build the market intelligence layer that continuously watches investments for the user, detects what is unusual or important, and explains it with evidence before the user has to search for it.**

### Consumer-facing promise

A natural Turkish expression of the product promise should be closer to:

> **Piyasayı sürekli takip etmek zorunda değilsin. Önemli bir şey olduğunda sana söyleriz.**

This is stronger than positioning the product as an "AI investment app". AI is a core capability, but the customer value is **continuous monitoring, prioritization, evidence, context, and explanation**.

---

## 3. Mission

Project 50K aims to reduce the cognitive burden of retail investing by converting fragmented financial information into timely, evidence-backed events.

The product should help a user move from:

- checking multiple financial websites,
- manually watching charts,
- reading every KAP filing,
- comparing fund pages,
- following news feeds,
- monitoring crypto activity,
- and deciding whether a movement matters,

into a simpler loop:

1. Follow an asset.
2. Receive only meaningful developments.
3. Understand why the development was detected.
4. Inspect the supporting evidence and sources.
5. Ask follow-up questions if desired.
6. Make the investment decision independently.

Project 50K informs the investor. It does not make the investment decision for them.

---

## 4. Core Product Thesis

Modern retail investors do not primarily suffer from a lack of information. They suffer from **information fragmentation, excessive noise, limited time, and weak contextualization**.

Most financial tools are optimized around one of the following models:

- **Data terminal:** "Here are the charts and metrics."
- **News feed:** "Here are the latest stories."
- **Rule-based alerting:** "Tell us the threshold you want monitored."
- **Screening:** "Build filters and search for opportunities yourself."
- **Brokerage:** "Buy and sell instruments."
- **Chatbot:** "Ask a question and we will answer it."

Project 50K is based on a different interaction model:

> **The system continuously observes first, detects second, investigates third, and only then asks for the user's attention.**

The product pipeline is therefore:

```text
Observe → Detect → Correlate → Investigate → Explain → Alert → Explore
```

---

## 5. What Project 50K Is

Project 50K is:

- a cross-asset market monitoring platform;
- a financial anomaly-detection system;
- a contextual intelligence layer over market, fundamental, regulatory, fund, news, and on-chain data;
- a personalized watchlist and alert product;
- an evidence-first AI research assistant for individual assets;
- a Turkey-first consumer fintech product with global expansion potential;
- a web research experience in its first implementation and a mobile-first notification product in its long-term form.

---

## 6. What Project 50K Is Not

Project 50K is not intended to be:

- a brokerage;
- a portfolio accounting or tax application;
- a signal-selling service;
- a copy-trading product;
- an automated trading bot;
- a product that outputs Buy / Hold / Sell recommendations;
- a system that declares a security or person to be "manipulating the market" without competent evidence and authority;
- a generic LLM wrapper that summarizes articles;
- a clone of TradingView, Midas, Fintables, Investing.com, or another existing terminal.

The system may detect patterns associated with unusual or potentially concerning market activity, but product language must distinguish **observed anomalies** from **legal conclusions**.

---

## 7. Target Users

The product is intended for retail investors across a range of experience levels:

### Beginner investor

Needs simple explanations, clear prioritization, and protection from information overload.

### Intermediate investor

Understands common market concepts but cannot continuously monitor every asset, disclosure, fund metric, and news source.

### Active retail investor

Needs intraday awareness, faster anomaly detection, source-level evidence, and the ability to investigate an event in depth.

The product should serve all three through **progressive disclosure**, not through three separate products. The initial event summary must remain simple; detailed evidence, metrics, methodology, and source material should be available one level deeper.

---

## 8. Asset-Class Strategy

### 8.1 BIST — Primary market

BIST is the core market for the initial product. The system should support intraday analysis, not only end-of-day monitoring.

Core intelligence domains include:

- price anomalies;
- abnormal volume;
- volatility shifts;
- sector/index divergence;
- liquidity-related signals where data permits;
- KAP disclosure interpretation;
- financial-statement anomalies;
- SPK/BIST regulatory events;
- trusted-news correlation;
- unexplained market-movement events.

### 8.2 Turkish investment funds — Strategic differentiator

Investment funds are not a secondary feature. They are a potential core differentiator in the Turkish market.

The product should eventually monitor:

- NAV/unit price;
- fund size/AUM;
- investor count;
- fund inflow/outflow proxies;
- asset allocation changes;
- peer/category divergence;
- risk profile;
- regulatory events;
- concentration and underlying-market exposure where sufficient data exists;
- relationships between fund behavior and BIST securities.

SPK states that fund amount, number of shares, investor count, portfolio value, portfolio allocation and unit-price information can be viewed on a daily and consolidated basis, and it links to TEFAS and a portfolio-value web service. [S1]

Recent events strengthen the relevance of this domain. SPK stated on 23 September 2026 that decisions dated 17 September covered the liquidation of 131 funds belonging to seven portfolio management companies, with 455,758 unique investors in those funds according to MKK records. [S2] SPK also stated on 18 September 2026 that, particularly through certain free investment funds and money-market funds, price movements had been observed in low-free-float shares that could not be explained by economic reality and fundamental financial metrics. [S3]

These events do not prove that a consumer anomaly product can identify every such case in advance. They do demonstrate that **fund-market relationships, investor protection, unusual behavior, transparency, and timely interpretation are meaningful current problems in Türkiye**.

### 8.3 Crypto

Crypto should combine market and on-chain intelligence.

MVP coverage should focus on a meaningful set of the most popular and liquid assets rather than an attempt to support every token. On-chain coverage should initially concentrate on **EVM-compatible chains and Solana**.

Potential signals include:

- abnormal price/volume;
- liquidity changes;
- holder concentration;
- whale transfers;
- exchange inflow/outflow;
- connected-wallet behavior;
- token-unlock events;
- deployer/creator activity where relevant.

### 8.4 U.S. equities

The U.S. market is an expansion layer that reuses the equity-intelligence architecture. MVP coverage should use a deliberately narrow, highly liquid universe.

Potential signals include:

- price/volume anomalies;
- sector divergence;
- financial-statement changes;
- earnings events;
- SEC filings;
- insider transactions where data is available;
- trusted-news context.

---

## 9. AI-Native Product Philosophy

Project 50K must be **AI-native, not AI-decorated**.

The role of AI is not limited to rewriting a deterministic alert in friendly language. AI should be used where semantic understanding and cross-source reasoning create genuine value.

### Deterministic/statistical layer

Responsible for measurable facts and repeatable calculations such as:

- returns;
- relative volume;
- volatility;
- robust z-scores;
- rolling baselines;
- peer divergence;
- fund allocation deltas;
- on-chain transaction metrics;
- event timestamps.

### ML/anomaly layer

Responsible for learning or estimating whether observed behavior differs materially from normal behavior. Method selection will be grounded in a later scientific-literature review covering financial time-series anomaly detection, manipulation/pump-and-dump research, multivariate detection, graph anomalies, change-point detection, and calibrated uncertainty.

### LLM intelligence layer

Responsible for tasks such as:

- understanding KAP/SPK/SEC/company disclosures;
- interpreting trusted news;
- classifying financial events;
- investigating possible explanations for a market anomaly;
- relating an event to company/fund scale;
- synthesizing evidence across sources;
- answering asset-specific follow-up questions;
- communicating uncertainty in natural Turkish.

### Decision/event layer

Responsible for producing a normalized event object such as:

```text
event_type = "unexplained_market_movement"
severity = "HIGH"
confidence = 0.91
evidence = [...]
sources = [...]
```

The LLM may contribute evidence and interpretation, but it must not be the sole authority for objective numerical facts or the final confidence value.

---

## 10. Severity and Confidence Are Different

A foundational product decision is to separate **severity** from **confidence**.

### Severity

Answers:

> How important could this event be for a user?

Possible MVP levels:

- Medium
- High
- Critical

### Confidence

Answers:

> How strongly does the available evidence support this event classification?

Confidence must not be generated by simply asking an LLM how confident it feels. It should eventually be calibrated using factors such as:

- evidence coverage;
- data freshness;
- source reliability;
- agreement among independent signals;
- missing-data penalties;
- magnitude of anomaly;
- historical precision/recall or calibration of relevant models.

Exact methodology is deferred until the scientific and empirical model-design phase.

---

## 11. Core User Experience

### Public experience

An anonymous visitor can:

- search supported assets;
- open public asset pages;
- inspect charts and selected metrics;
- view public intelligence events;
- understand what the product does through a polished landing page.

### Authenticated experience

Google-authenticated users can:

- create a watchlist;
- receive personalized event feeds;
- receive e-mail and in-app alerts;
- access asset-specific AI conversations;
- retain chat history;
- submit alert feedback;
- control notification preferences.

For MVP, **watchlist and “my assets” are the same concept**. Cost basis, lot count, P&L and tax accounting are intentionally excluded.

### Market-wide critical intelligence

Users may also receive alerts for assets outside their watchlist when an event meets a deliberately high **Critical** threshold. This feature must be rate-limited and user-controllable to prevent notification fatigue.

---

## 12. Asset Intelligence Page

Each asset page should eventually combine:

- price chart;
- anomaly/event timeline;
- key market metrics;
- relevant fundamentals;
- recent official disclosures;
- trusted news;
- asset-specific intelligence summaries;
- evidence and sources;
- an AI assistant that already knows the current asset context.

The conversational assistant is not the primary product interface. The system should proactively surface important events; chat exists for deeper investigation.

Example questions:

- “Bugün neden yükseldi?”
- “Bu KAP açıklaması şirketin ölçeğine göre ne kadar önemli?”
- “Benzer bir hareket daha önce olmuş mu?”
- “Bu fonun portföy dağılımında son dönemde ne değişti?”
- “Bu kripto varlıkta son 24 saatte dikkat çeken on-chain hareket ne?”

All material factual answers should be source-backed. If evidence is insufficient, the assistant must be able to say that it cannot establish an explanation.

---

## 13. Notification Philosophy

Project 50K must minimize noise.

### In-app

Eligible intelligence events according to user settings.

### Immediate e-mail

- High/Critical watchlist events, based on user preference;
- Critical market-wide events even when outside the watchlist, subject to user controls.

### Digest

Lower-priority events can be grouped into a digest rather than producing individual e-mails.

### Not in MVP

- browser push;
- native mobile push.

Native push becomes a core capability in the future mobile product.

---

## 14. Web MVP, Mobile Product Vision

### MVP

Responsive, deployable web application.

Reasons:

- fastest development path in a 54-hour startup weekend;
- strongest environment for financial charts and evidence-rich asset pages;
- easier jury demonstration;
- no App Store/Play Store delivery overhead;
- reusable as a long-term desktop research product.

### Long-term

Mobile-first consumer experience.

The eventual product split can be thought of as:

```text
Web:    research, discovery, detailed analysis
Mobile: alerts, watchlist, portfolio awareness, quick investigation
```

Both should share the same intelligence backend.

---

## 15. Design Vision

Design quality is a first-class product requirement.

Project 50K must avoid generic AI-generated fintech aesthetics. Specifically, it should not default to:

- excessive glassmorphism;
- neon gradient dashboards;
- decorative “AI sparkles”;
- nested card-on-card layouts;
- dense chip/status-label clutter;
- uniform card grids with no hierarchy;
- arbitrary animations;
- crypto-casino visual language.

The desired direction is closer to:

> **premium financial intelligence terminal × editorial clarity × modern consumer product**

Dense information is acceptable when it is genuinely useful. The design response to complexity should be **hierarchy and progressive disclosure**, not hiding all information behind generic cards.

The team intends to use Impeccable as part of the agentic-development workflow. Impeccable explicitly provides design context files and automated checks intended to catch recurring AI-generated design defaults. [S4]

A dedicated `PRODUCT.md` and `DESIGN.md` should later be maintained for coding agents.

---

## 16. Technical Direction

The current recommended implementation stack is:

- **Frontend:** Next.js 16.x, React, TypeScript
- **Styling:** Tailwind CSS 4.x with custom design tokens
- **UI primitives:** unstyled/headless accessible primitives; no off-the-shelf theme
- **Financial charting:** TradingView Lightweight Charts
- **Analytical charting:** Apache ECharts where needed
- **Backend/API:** Python + FastAPI
- **Data/ML:** Polars, NumPy, SciPy, scikit-learn, statsmodels; additional methods selected after literature review
- **Database:** Supabase PostgreSQL
- **Vector retrieval:** pgvector
- **Authentication:** Supabase Auth, Google OAuth only
- **Caching/jobs:** Redis plus a dedicated Python worker; MVP scheduler kept deliberately simple
- **E-mail:** transactional provider such as Resend
- **LLM layer:** provider abstraction, with OpenAI as the initial implementation
- **Web deployment:** Vercel
- **API/worker deployment:** Railway
- **Primary timezone:** Europe/Istanbul

Supabase provides official Next.js App Router authentication guidance and Google social-login support, which fits the MVP's Google-only account model. [S5][S6]

---

## 17. Data and Licensing Principle

The hackathon may use pragmatic providers and historical/demo data to validate product value. Production commercialization must treat data licensing as an architectural concern rather than an afterthought.

Borsa İstanbul states that market data is distributed through licensed data distributors. It also defines accessing and using data without displaying it — including surveillance systems, risk-management systems and investment-analysis services — as “non-display use”, for which a direct data-distribution agreement is required. [S7][S8]

Therefore the application must use provider abstractions so that hackathon data sources can be replaced later without rewriting product logic.

Example:

```text
StockDataProvider
FundDataProvider
NewsProvider
DisclosureProvider
OnChainProvider
```

The anomaly engine consumes normalized internal contracts, not provider-specific response objects.

---

## 18. Core Product Principles

1. **Watch the market for the user.**
2. **Evidence before explanation.**
3. **AI-native, not AI-decorated.**
4. **Deterministic facts; probabilistic intelligence.**
5. **Severity is not confidence.**
6. **No Buy / Hold / Sell recommendations.**
7. **Do not present anomaly detection as a legal finding of manipulation.**
8. **Cite material claims.**
9. **Say “I cannot establish an explanation” when evidence is insufficient.**
10. **Turkey-first, not Turkey-only.**
11. **BIST and funds must be deeper than global add-ons.**
12. **Minimize alert fatigue.**
13. **Natural Turkish for users; English for engineering artifacts.**
14. **Web-first MVP; mobile-first long-term product.**
15. **Design quality is a requirement, not post-launch polish.**
16. **Provider independence and data provenance are architectural requirements.**
17. **Scientific literature and empirical validation should inform the anomaly/decision engine.**

---

## 19. Initial Success Hypothesis

Project 50K succeeds if users feel that it reliably answers three questions better and faster than their current workflow:

1. **What important thing happened?**
2. **Why did the system flag it?**
3. **What evidence should I inspect before making my own decision?**

For the hackathon, success is demonstrated by a working prototype that can detect and explain several meaningful historical events, ingest at least some current data, show evidence-backed asset pages, and deliver a polished user experience.

---

## 20. Sources & Evidence

- **[S1] SPK — Portföy Değerleri:** https://www.spk.gov.tr/kurumlar/fonlar/yatirim-fonlari/menkul-kiymet-yatirim-fonlari/portfoy-degerleri
- **[S2] SPK — Tasfiye Konusu Fonlardaki Yatırımcı Sayısına İlişkin Açıklama, 23 Sep 2026:** https://www.spk.gov.tr/duyurular/basin-duyurulari/2026/tasfiye-konusu-fonlardaki-yatirimci-sayisina-iliskin-aciklama
- **[S3] SPK — Yatırım Fonlarına İlişkin Rehber Düzenleme Süreci Açıklaması, 18 Sep 2026:** https://spk.gov.tr/duyurular/basin-duyurulari/2026/yatirim-fonlarina-iliskin-rehber-duzenleme-surecine-iliskin-aciklama
- **[S4] Impeccable:** https://impeccable.style/
- **[S5] Supabase — Auth with Next.js:** https://supabase.com/docs/guides/auth/quickstarts/nextjs
- **[S6] Supabase — Sign in with Google:** https://supabase.com/docs/guides/auth/social-login/auth-google
- **[S7] Borsa İstanbul — Veri Yayını:** https://www.borsaistanbul.com/veriler/veri-yayini
- **[S8] Borsa İstanbul — Veri Dağıtım ve Endeks Lisanslama:** https://www.borsaistanbul.com/sss/veri-dagitim-ve-endeks-lisanslama
