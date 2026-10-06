# Project 50K — Product Vision & Executive Summary

**Version:** 0.3 · **Date:** 2026-10-02
**Status:** specification; not implemented product functionality.

## Product definition
Project 50K is a Türkiye-first, AI-native retail investment intelligence and anomaly-monitoring product. It identifies unusual observations, investigates their context and explains source-backed developments in natural Turkish. BIST is mandatory; Turkish investment funds are the main differentiating research focus, followed by crypto and selected US equities.

It is not a brokerage, portfolio-accounting tool, trading recommender, loss-prevention guarantee or authority that determines fraud/manipulation. A user can research an asset before owning it. The account model uses a watchlist, not assumed holdings.

## Customer problem and value
Users can access many prices, graphs and news stories but must decide what deserves attention, reconcile sources and judge uncertainty. The proposed value is fewer meaningful, explainable events with visible source coverage—not more raw signals or an undifferentiated AI chat window. Existing alerting competitors are recognized in document 24; uniqueness remains a hypothesis to validate.

Turkish user promise: **“Takip ettiğiniz varlıklardaki önemli gelişmeleri, kaynakları ve nedenleriyle görün.”** Avoid promising that the platform will always detect developments before the user or prevent losses.

## Core experience
An anonymous visitor discovers a security/fund/coin, opens an asset page and inspects permitted charts and published events. Google sign-in unlocks a persistent watchlist, personal feed, preferences, notifications, feedback and bounded asset chat. Official documents, financial context and credible news support the investigation. Users may explicitly opt into exceptional critical events outside their watchlist.

The event explains what changed, the relevant time window, source/venue and latency, why it was flagged and what the system cannot conclude. Users can ask follow-up questions without being forced to construct screening rules. The assistant may research current sources within bounded read-only tools; it can and must abstain when evidence is insufficient.

## AI-native operating model
Numerical evidence is computed through reviewed deterministic/statistical methods. LLM investigation actively extracts disclosure events, resolves context, asks read tools for missing information, synthesizes evidence and supports conversational research. A deterministic policy layer validates claims, timestamps, rights, severity, eligibility and score semantics before publication/delivery. The LLM does not set arbitrary confidence, manipulate records or broadcast notifications.

Confidence v1 is **heuristic evidence strength**, shown with a disclosed method; calibrated probability remains null until supported by separate evaluation. Severity, source health, unusualness and user relevance remain distinct.

## Surface and architecture
The weekend prototype is a polished responsive web application with a mobile-first long-term consumer vision. Google-only accounts, a small protected admin operations panel, readable Turkish, source drawers, asset-event timelines and low-noise email/in-app notifications are confirmed product decisions. Browser push, actual mobile binaries, cost basis, social-media ingestion and buy/hold/sell output are excluded from the initial release.

The architecture uses a typed Next.js web front end, Python/FastAPI analytics/API, Supabase PostgreSQL/Google Auth and one durable PostgreSQL worker/outbox. Further infrastructure requires a demonstrated need. Versions, vendors, budgets and data entitlements are resolved at implementation; no environment is provisioned by this specification.

## What must be proved
Validate whether investors understand and trust events, whether alerts reduce monitoring burden, whether fund/BIST context is a reason to switch or pay, and whether data rights permit viable unit economics. Scientific references justify candidate methods, not product accuracy. No revenue, retention, predictive accuracy or user-study results are claimed.

## Delivery boundaries
The full product vision is larger than a one-developer weekend. Build BIST/fund vertical slices first and treat broad catalog size separately from active monitoring. EVM, Solana and US integrations remain desired but provider/capacity-gated. A reduced demo is labeled as reduced, not misrepresented as complete. Organizer pre-work clarification and real-data publication rights are blocking gates (document 25).

## Problem solution and market research continuation 3 October 2026

Real information seeking and events support research into verification effort. Recurring unmet need, willingness to switch/pay and our task advantage remain hypotheses. Positioning must not imply demonstrated fraud prediction, loss prevention or paid traction. See `reports/PROBLEM_MARKET_RESEARCH.md` and the linked source-depth appendices.
