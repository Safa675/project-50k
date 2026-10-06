# Project 50K — Problem Analysis & Opportunity

**Version:** 0.3 · **Date:** 2026-10-02
**Status:** specification; not implemented product functionality.

## 1. Problem hypotheses
Investors face fragmented sources, information overload, inconsistent financial context, delayed discovery and opaque automated signals. These are working hypotheses derived from the product conversation, not a statistically verified survey of Turkish investors. Interview separate beginner, fund-focused and active cohorts before claiming prevalence.

The research question is not “can we show a graph?” It is “can we reliably direct attention to a meaningful event and expose its evidence with less work and less false certainty than the user's existing workflow?”

## 2. Türkiye-specific opportunity
BIST corporate disclosures, fund facts and regulatory announcements can be linked by canonical security/fund/issuer identity and publication time. Fund asset-class allocation, unit value, investor/AUM trends where truly available, and last-disclosed holdings provide different evidence layers. They must not be merged into an imaginary real-time portfolio.

SPK's official statement in the relevant September 2026 liquidation context identifies 131 funds, seven portfolio-management companies and 455,758 unique investors according to MKK [S02]. It does not quantify investor losses or prove every investor/asset experienced fraud. The regulator's separate explanation describes its observations concerning certain funds and low-free-float share behavior [S03]; attribute those observations exactly. This supports investigating transparency needs, not claiming the proposed detector would have predicted or prevented the events.

## 3. Data feasibility limits
Publicly visible does not mean licensed for commercial analytics or redistribution. BIST specifically addresses non-display use, including investment analysis/surveillance [S01]. Provider access, code licensing and rights to distribute alerts are separate.

The inspected borsapy TEFAS history implementation supplies price history while filling historic FundSize/Investors columns with compatibility placeholders [S06]. Latest fund detail is not historical reconstruction. Fundamental reporting dates, public availability dates and ingestion dates differ. US IEX volume is not consolidated market volume [S08]. Raw chain transactions do not establish owners or sales [S11,S12].

Therefore feasibility is field-, time-, rights- and detector-specific. An honest unavailable state is part of the product, not a flaw to hide.

## 4. Competitive alternatives
TradingView already offers watchlist alerts; Koyfin advertises price, technical, valuation, news and filing alerts [S30,S31]. Local/specialist alternatives require direct verification. A claim of no competitors or first all-market alert app is unsupported. Candidate differentiation is fund/BIST-specific context, careful timing, cited Turkish explanations and measured low-noise monitoring.

## 5. Risks and experiments
| Risk | Experiment / decision |
|---|---|
| Alerts add noise | Compare understood/actionable events per week, not raw alert counts |
| Fund data insufficient | Field-level provider spike; disable unavailable flow/history detectors |
| Users prefer incumbents | Same five tasks across alternatives with observed behavior |
| AI invents causality | Claim-evidence evaluation, numeric checks, source conflict handling and abstention |
| Data costs overwhelm revenue | Obtain actual scoped quotes; test paid value before pricing |
| Scope overwhelms one developer | Two reliable anchor vertical slices, then conditional expansion |
| Trust confused with probability | Turkish comprehension test for evidence-strength wording |

## 6. Validation boundaries
Unusual price/volume may have ordinary reasons. A published regulatory event is not automatically a crime finding. Historical replay is a demonstration method, not proof of predictive generalization. The literature review is targeted and review depth is disclosed. No empirical backtest or calibrated confidence results have yet been established.

Sources are resolved in `research/SOURCE_REGISTER.md`. Detailed interview and demo protocol is document 23.

## Problem solution and market research continuation 3 October 2026

Current evidence supports observed revision/conflict mechanisms and existing information seeking, not representative Turkish pain prevalence. KAP already supplies following and notifications; the proposed value is correct, lower-effort source/time/context verification. A platform publication count is not a personal anomaly rate. See `reports/PROBLEM_MARKET_RESEARCH.md` and the linked source-depth appendices.
