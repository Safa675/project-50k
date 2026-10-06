# Source register — declared review depth and dated audit verification

Access date: 2026-10-02. Public documentation checks are not live API tests, legal approvals or service guarantees. No third-party paper full text is redistributed.

## S01 — Borsa İstanbul — data distribution and non-display licensing

Source: https://www.borsaistanbul.com/sss/veri-dagitim-ve-endeks-lisanslama

Review: read. A public page or delayed feed is not a redistribution or non-display license.

## S02 — SPK — investors in funds subject to liquidation, 23 September 2026

Source: https://spk.gov.tr/duyurular/basin-duyurulari/2026/tasfiye-konusu-fonlardaki-yatirimci-sayisina-iliskin-aciklama

Review: read. 131 funds, seven portfolio managers, 455,758 unique investors according to MKK; not a loss estimate.

## S03 — SPK — fund guideline preparation explanation, 18 September 2026

Source: https://spk.gov.tr/duyurular/basin-duyurulari/2026/yatirim-fonlarina-iliskin-rehber-duzenleme-surecine-iliskin-aciklama

Review: read. Attribute observations about fund/share activity to SPK; no predictive validation of this product.

## S04 — SPK — investment-fund portfolio values

Source: https://spk.gov.tr/kurumlar/fonlar/yatirim-fonlari/menkul-kiymet-yatirim-fonlari/portfoy-degerleri

Review: read. Discovery entry point; available fields and time-series coverage require endpoint testing.

## S05 — borsapy repository README

Source: https://github.com/saidsurucu/borsapy

Review: read. Unofficial wrapper; personal/educational-use warning; code license does not grant data rights.

## S06 — borsapy TEFAS provider implementation

Source: https://github.com/saidsurucu/borsapy/blob/master/borsapy/_providers/tefas.py

Review: code inspected. GitHub blob SHA 7b5974ab0eee3a07808a5a8b8439d4d693caa26c; history inserts FundSize=NaN, Investors=0; endpoints are not independently live-tested.

## S07 — SPK web-service help

Source: https://ws.spk.gov.tr/help/index.html

Review: page located; schema not recovered. Do not invent paths or promise coverage. A schema/sample-response spike remains open.

## S08 — Alpaca Market Data overview

Source: https://docs.alpaca.markets/us/docs/about-market-data-api

Review: read. IEX versus consolidated coverage; subscription and redistribution rights require separate review.

## S09 — SEC EDGAR APIs

Source: https://www.sec.gov/search-filings/edgar-application-programming-interfaces

Review: read. Submission/XBRL APIs, no authentication; server-side retrieval and access-policy compliance.

## S10 — Binance spot WebSocket streams

Source: https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams

Review: read. Venue-specific public market streams; access/terms must be checked for deployment region.

## S11 — Ethereum JSON-RPC

Source: https://ethereum.org/en/developers/docs/apis/json-rpc/

Review: read. Raw logs/transactions are not wallet-identity or beneficial-owner labels.

## S12 — Solana getTokenLargestAccounts

Source: https://solana.com/docs/rpc/http/gettokenlargestaccounts

Review: read. Returns 20 token accounts, not 20 independent persons.

## S13 — DEX Screener API

Source: https://docs.dexscreener.com/api/reference

Review: read. Pair-level data; snapshot and historical support must be distinguished.

## S14 — CoinGecko coins markets

Source: https://docs.coingecko.com/reference/coins-markets

Review: read. Candidate universe metadata and rankings; use provider IDs and dated snapshots.

## S15 — Next.js installation

Source: https://nextjs.org/docs/app/getting-started/installation

Review: read. 16.3.8 displayed at review; resolve and lock supported versions at implementation, not floating latest in CI.

## S16 — Supabase Google authentication

Source: https://supabase.com/docs/guides/auth/social-login/auth-google

Review: read. Provider configuration required; no infrastructure was provisioned here.

## S17 — Supabase SSR client guidance

Source: https://supabase.com/docs/guides/auth/server-side/nextjs

Review: read. Follow current server-side session validation and cookie guidance.

## S18 — Supabase row-level security

Source: https://supabase.com/docs/guides/database/postgres/row-level-security

Review: read. Service-role credentials bypass RLS; browser use is forbidden.

## S19 — OpenAI web search tool

Source: https://developers.openai.com/api/docs/guides/tools-web-search

Review: read. Responses web-search tool and clickable citation annotations; availability must be verified for selected model/account.

## S20 — Codex AGENTS.md guidance

Source: https://developers.openai.com/codex/guides/agents-md

Review: read. Repository instructions for coding agents.

## S21 — Claude Code memory and project instructions

Source: https://code.claude.com/docs/en/memory

Review: read. CLAUDE.md project instructions; import AGENTS.md rather than duplicating rules.

## S22 — Impeccable

Source: https://impeccable.style/

Review: read. Design workflow, PRODUCT.md and DESIGN.md; check current installation/command syntax.

## S23 — TradingView Lightweight Charts

Source: https://tradingview.github.io/lightweight-charts/

Review: read. Chart library, not data feed; comply with notices and attribution.

## S24 — FastAPI tutorial

Source: https://fastapi.tiangolo.com/tutorial/

Review: read. Typed Python API foundation.

## S25 — Resend API

Source: https://resend.com/docs/api-reference/introduction

Review: read. Email integration candidate, sender/domain setup required.

## S26 — Resend idempotency keys

Source: https://resend.com/docs/dashboard/emails/idempotency-keys

Review: read. Provider idempotency supplements rather than replaces durable application deduplication.

## S27 — OWASP LLM application risks

Source: https://owasp.org/www-project-top-10-for-large-language-model-applications/

Review: read. Prompt injection and unsafe tool/data flows inform threat model.

## S28 — WCAG 2.2

Source: https://www.w3.org/TR/WCAG22/

Review: read. Accessibility reference; project targets are not an accessibility certification.

## S29 — KVKK standard contracts announcement

Source: https://www.kvkk.gov.tr/Icerik/7938/Standart-Sozlesmeler-ve-Baglayici-Sirket-Kurallarina-Iliskin-Dokumanlar-Hakkinda-Kamuoyu-Duyurusu

Review: read. Cross-border processing requires a legally reviewed transfer arrangement; consent is not a universal workaround.

## S30 — TradingView watchlist alerts

Source: https://www.tradingview.com/support/solutions/43000739708-watchlist-alerts/

Review: read. Proactive/watchlist alerting already exists; not a unique selling point by itself.

## S31 — Koyfin alerts

Source: https://www.koyfin.com/features/alerts/

Review: read. Alerts across price, technical, valuation, news and filing dimensions.

## S32 — ForInvest business products

Source: https://www.forinvest.com/business?lang=en

Review: read. Local data/analytics ecosystem; exact comparable consumer features need hands-on verification.

## S33 — Techstars Startup Weekend

Source: https://www.techstars.com/communities/startup-weekend

Review: read. General program only. Local schedule and pre-work rule are from user-provided materials.

## R01 — Empirical properties of asset returns: stylized facts and statistical issues

Source: https://www.tandfonline.com/doi/abs/10.1080/713665670

Review: publisher abstract/search excerpt. Broad financial-market evidence, not a calibrated BIST fraud classifier.

## R02 — Intraday periodicity and volatility persistence in financial markets

Source: https://www.sciencedirect.com/science/article/pii/S0927539897000042

Review: publisher abstract. Different markets and historical periods; proposed local thresholds are not supplied by the paper.

## R03 — Isolation Forest

Source: https://ieeexplore.ieee.org/document/4781136

Review: publisher abstract. An anomaly score is not a supervised probability; contamination and features change results.

## R04 — Bayesian Online Changepoint Detection

Source: https://arxiv.org/abs/0710.3742

Review: author abstract. Hazard and likelihood assumptions matter; not an out-of-box market-abuse detector.

## R05 — Selective review of offline change point detection methods

Source: https://arxiv.org/abs/1801.00718

Review: author abstract and publication metadata. Offline segmentation can see future observations.

## R06 — Current Time Series Anomaly Detection Benchmarks are Flawed and are Creating the Illusion of Progress

Source: https://arxiv.org/abs/2009.13807

Review: author abstract and publication metadata. General benchmark critique; it does not label Project 50K events.

## R07 — On Calibration of Modern Neural Networks

Source: https://proceedings.mlr.press/v70/guo17a.html

Review: proceedings abstract. Image/text classification experiments; temperature scaling does not calibrate an arbitrary weighted score automatically.

## R08 — Conformal prediction beyond exchangeability

Source: https://arxiv.org/abs/2202.13415

Review: author abstract. Coverage assumptions and drift still matter; a prediction set is not a fraud probability.

## R09 — Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing

Source: https://academic.oup.com/jrsssb/article/57/1/289/7035855

Review: publisher abstract. Overlapping assets/times are dependent; heuristics are not automatically valid p-values.

## R10 — Costly Search and Mutual Fund Flows

Source: https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00066

Review: publisher abstract. Historical equity mutual funds outside Türkiye; flow changes are not misconduct evidence.

## R11 — To the moon: defining and detecting cryptocurrency pump-and-dumps

Source: https://link.springer.com/article/10.1186/s40163-018-0093-5

Review: publisher abstract and accessible article. Historical exchanges and selected events; labels and thresholds are not portable to BIST or major coins without testing.

## R12 — The Anatomy of a Cryptocurrency Pump-and-Dump Scheme

Source: https://www.usenix.org/conference/usenixsecurity19/presentation/xu-jiahua

Review: conference abstract. Coordination evidence depends on data excluded from our social-media-free MVP.

## R13 — Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks

Source: https://arxiv.org/abs/2005.11401

Review: author abstract. Retrieval does not establish source truth or eliminate unsupported synthesis.

## R14 — ReAct: Synergizing Reasoning and Acting in Language Models

Source: https://arxiv.org/abs/2210.03629

Review: author abstract. Benchmark results are not financial accuracy evidence; unrestricted tool autonomy adds risk.

## R15 — Enabling Large Language Models to Generate Text with Citations

Source: https://aclanthology.org/2023.emnlp-main.398/

Review: proceedings abstract. A displayed citation may still fail to support the attached claim.


## v0.4 audit verification
Original review claims remain historical in the received release. Current verification depth and failures are recorded per reference in `scientific_sources_verification.json` and `data_sources_verification.json`. Metadata confirmation is separate from full-paper review, live service tests and data-use rights. S06 remains mutable-reference-only; its prior reported blob hash was not independently recovered.

| ID | Supplemental source | URL | Verified scope |
|---|---|---|---|
| S34 | KAP publication-service REST integration | https://kap.org.tr/tr/api/about/content-file/8a019492945fbe080194b26d8bed4873 | Subscriber route requires distribution contract and MKK IP/key authorization; selected issuer/fund scope; no entitlement obtained. |
| S35 | Fintables official product packages | https://fintables.com/uyelik-paketleri | Fund comparison/filtering, fund-stock positions, estimated fund price and Evo AI documented; hands-on quality not tested. |
| S36 | ForInvest / ForMind official product context | https://www.forinvest.com/business?lang=en | Official product/terms review documents financial-data and natural-language analysis overlap; consumer task quality not tested. |
| S37 | Supabase signout token lifetime | https://supabase.com/docs/guides/auth/signout | Already issued access tokens remain valid to expiry after session revocation; local signature validation does not imply immediate logout enforcement. |
| S38 | Supabase session state | https://supabase.com/docs/guides/auth/sessions | Sensitive actions can verify session_id against current trusted session state; no provisioned integration tested. |
| S39 | Supabase anonymous authentication roles | https://supabase.com/docs/guides/auth/auth-anonymous | Anonymous Auth sessions use authenticated database role; Google-only product policy needs additional identity/provider checks. |

R06: final TKDE journal issue is 2023, 35(3):2421–2429, DOI 10.1109/TKDE.2021.3112126; early access is 2021. Author arXiv 2009.13807v5 was revised on 2022-09-03; its ICDE extended abstract is a separate publication. The complete BibTeX author/type/field corrections and unresolved metadata are retained in `bibliography_audit.json`.

## v0.5 supplementary source records
The original 54-entry register and 15-paper bibliography retain their audited identities. Additional selected primary-source readings live in research/engine_lab/*_sources.json and research/brand_lab/color_candidates.json/DESIGN_EXPLORATION.md. They have independent lab IDs, URL/date/depth and explicit limits; they do not retrospectively validate anomaly thresholds or imply full-body/systematic review. Public name screening is separately recorded in NAMING_RETRIEVAL_LOG.json.

## Risk review source provenance — 2026-10-03 local

Separate lane manifests under research/risk_review record current primary pages, reading depth, failed attempts and pre-update document snapshots. They do not replace the audited 54-entry/15-paper register or validate catalog thresholds. Review UTC date 2026-10-02 and Europe/Istanbul date 2026-10-03 refer to the same session. Hash snapshots describe review inputs, not later appended files; pre-update history is preserved.
