# Project 50K — product brief for market research

## What the product is

Project 50K (working codename; "İzvanta" is a naming proposal) is a planned Turkish-language web app that monitors Turkish investment funds for retail investors. When something notable happens to a fund the user follows, it shows what changed, when it became known, which official sources support it and what is still uncertain. Its promise: *"Takip ettiğiniz varlıklarda önemli bir gelişme olduğunda, neden önemli olabileceğini kaynaklarıyla görün."* (When something important happens to an asset you follow, see why it might matter, with its sources.)

It is an information and research tool, not an advisor. It gives no buy/hold/sell calls or price targets, executes no trades, makes no price predictions and never labels anything as fraud. It doesn't ask for holdings or brokerage logins; users keep a watchlist.

Its theme is trust and calm: evidence before persuasion, honesty about stale or missing data, a few meaningful alerts instead of many raw signals, and native Turkish. Confidence is shown as "evidence strength", never as a probability.

**Target user:** an independent retail investor who understands the basics, follows several funds and uses several sources, but can't watch everything all the time. Beginners and very active investors are secondary users.

## Scope and stage

- **Current phase:** Turkish investment funds on TEFAS only (about 2,100 funds). BIST equities, crypto, US equities and on-chain data are part of the long-term vision but postponed.
- **Stage:** pre-product. Requirements, architecture and research are written, but there is no working app, no customer interviews, no pricing test and no users. Solo developer, with a total prototype budget of TRY 5,000. The first milestone is a Techstars Startup Weekend demo.

## What it detects in the funds phase

- A fund's return diverging sharply from its category peers
- Asset-allocation shifts, from KAP's monthly portfolio reports
- Regulatory or access events: access restrictions, liquidation notices, material prospectus changes (from official disclosures)
- Estimated net inflows/outflows and investor-count changes. These need the app's own daily snapshots, because TEFAS publishes only the current value.
- Corrections to earlier official disclosures
- Data problems: stale, missing or placeholder values

## User flow

Search a fund without an account → open its page (price chart, event timeline, source drawer) → sign in with Google → follow funds → get in-app alerts and optional email (immediate or digest) → ask the AI a bounded question about a specific event → open the cited sources → rate usefulness.

## Architecture

- **Front end:** Next.js + TypeScript responsive web app with a Turkish UI. Mobile apps later.
- **Back end:** a Python/FastAPI API and one background worker in a single codebase. Supabase provides PostgreSQL and Google sign-in, and a database job queue replaces extra infrastructure.
- **Data:** TEFAS (daily NAV with 5-year history; other fields only as a current snapshot), KAP (fund disclosures and monthly portfolio reports in PDF) and regulator announcements. Commercial redistribution rights for this data are still an open question.
- **Pipeline:** ingest → record what was knowable and when → deterministic statistical detectors (robust baselines, peer comparison) → AI investigation (an LLM reads disclosures, makes bounded read-only lookups and drafts typed claims with citations) → a rule-based gate that checks every claim, number, timestamp and data right before publishing → feed and notifications.
- **AI safety and cost:** the LLM cannot set scores, write records or send alerts. Each event explanation is generated once per event version and shared by all followers, which keeps AI costs low.

## Turkish market figures already collected (verify and update)

- **MKK VAP screen, dated 2 Oct 2026:** about 5.95 million fund investors, 5,729,060 of them individuals. A separate "monthly active" fund figure of about 2.20 million has an unknown methodology. There are also about 6.62 million equity investors and 3.72 million crypto investors. These cohorts overlap and must not be added together.
- **KAP 2025:** 161,759 notifications in total, 79,357 of them for funds. KAP reports about 5 million quick searches a year.
- **SPK statement, 23 Sep 2026:** 131 funds of seven portfolio management companies were in liquidation, affecting 455,758 unique investors; SPK issued it after conflicting public reports about the numbers. This illustrates the kind of event the product targets; it is not a demand estimate.
- **Known overlap:** KAP itself offers free fund following and instant mobile notifications. Fintables offers fund comparison, fund holdings, historical allocations, price alarms and an AI assistant (Evo). ForInvest/ForMind, TradingView, Koyfin, Investing.com and Midas offer alerts or AI research. Our earlier review only read marketing pages; nothing was tested hands-on.

---

## Prompt for ChatGPT

You are a senior market analyst with deep knowledge of Turkish capital markets and fintech. Using the product brief above, write a market research report on how successful this product could be. Browse the web and use the most recent data available; today is 6 October 2026. Prefer primary sources: SPK, MKK/VAP, TEFAS, KAP, TSPB, Borsa İstanbul, TKYD, TÜİK, company websites, app stores and funding databases.

**Rules**

- Give a source URL and publication date for every figure. Label each number **Sourced**, **Derived** (show the arithmetic) or **Assumption**.
- Don't invent numbers. If you can't find something, say "not found" and give a clearly labeled assumption range instead.
- Keep units separate. Registered investors, investors with balances, active accounts, unique people and paying users are different things, and the equity, fund and crypto cohorts overlap, so they can't be added.
- State the TRY/USD rate and its date whenever you convert currency, and account for Turkish inflation in multi-year projections.
- The product doesn't exist yet. Evaluate the concept and don't assume any traction.

**Sections**

1. **Executive summary.** Your verdict (strong / moderate / weak / not viable as a standalone business), the three main reasons and the single biggest risk.
2. **Market context.** Turkish investment fund trends over the last 3–5 years: total fund assets, investor and fund counts, growth by fund type (money market, equity, hedge-type and others), and the role of inflation and interest rates. Who retail fund investors are (age, digital habits) and how they buy and track funds today (bank apps, brokers, TEFAS-connected platforms). The 2026 fund liquidations and how investors got information about them.
3. **TAM / SAM / SOM.** Work bottom-up first and cross-check top-down. Give low / base / high cases with every assumption visible.
   - TAM: Turkish retail investors who could use a paid fund-monitoring and research product.
   - SAM: self-directed, digitally active fund investors who follow specific funds and would use a Turkish web or mobile tool.
   - SOM: realistic paying users and revenue in years 1, 3 and 5 for a solo-founder, low-budget startup.
   - Size B2C subscriptions and B2B options (white-label or API for banks, brokers, portfolio management companies and financial media) separately.
   - Show, as separate upside, how the market grows if BIST, crypto and US equities are added later.
4. **Willingness to pay and pricing.** Current prices in TRY and USD of Turkish investor tools (Fintables, Matriks, ForInvest, Midas premium tiers, TradingView in Turkey, and others you find). Typical freemium-to-paid conversion and churn for retail investing apps. Turkish consumers' subscription spending habits. A recommended pricing model with price points.
5. **Competitor landscape.**
   - Direct: Turkish fund analytics and alert products. Include at least Fintables, KAP's own following and notifications, the TEFAS website, ForInvest/ForMind and Matriks, plus any fund-comparison sites and apps you find.
   - Indirect: bank and broker apps, Midas, Investing.com, TradingView, Koyfin, Morningstar.
   - Substitutes: ChatGPT, Gemini and Perplexity used directly; X, Telegram, YouTube and finfluencer communities; doing nothing.
   - A feature matrix covering Turkish fund coverage, event detection, dated source citations, AI chat, alerts, holdings/allocation history, price, platform, estimated users and funding. Mark each cell **Verified** (with source), **Vendor claim** or **Unknown**.
   - The closest international analogues and what happened to them: users, revenue, funding, shutdowns, acquisitions.
6. **Differentiation and defensibility.** Is "source-backed, time-stamped explanations of fund events, with honest uncertainty, in Turkish" a real wedge, or a feature an incumbent could copy in a few months? What could become a moat (own data history, event taxonomy, trust, distribution partnerships)?
7. **Regulatory and data constraints** that affect market size:
   - SPK rules on investment advisory (yatırım danışmanlığı) versus general information, and where an AI that explains fund events falls.
   - Licences and costs for commercially redistributing TEFAS, KAP and Borsa İstanbul data.
   - KVKK and commercial email rules (İYS).
8. **Go-to-market.** Realistic acquisition channels in Turkey (SEO on fund codes, X, YouTube, Telegram, finfluencer or broker partnerships), estimated CAC ranges and the best first segment.
9. **Scenarios and risks.** Bear / base / bull scenarios with what must be true for each, the top five risks with mitigations, and kill criteria: signals that should make the founder stop or pivot.
10. **Validation plan.** The five cheapest experiments to run in the next 4–6 weeks (for example a landing-page price test or problem interviews), plus ten non-leading interview questions for Turkish fund investors.

**Output:** a structured report with tables, then a source list with URLs and access dates. Write in English, but keep Turkish product, regulator and legal names in Turkish.
