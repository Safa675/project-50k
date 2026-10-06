# US and crypto: real problems and measured frequencies

Retrieved 2026-10-03. This is a limited review of original empirical papers and original incident reports, not a new market backtest. It supplies historical measurements with their definitions, periods and denominators. It does not establish current Project 50K detector frequency, fraud prevalence, causal explanation accuracy or paid demand.

Large market deviations, unreliable reported volume and damaging market/chain incidents are real observed problems. The defensible product hypothesis is that users may benefit from a bounded investigation that separates a measured deviation, verified context and an unsupported explanation. Whether those investigations save enough attention or money to justify this product remains unmeasured. The observations below support studying that hypothesis; they do not establish it.

## What has actually been measured

| Original evidence | Observed quantity and unit | Period and denominator | Interpretation limit |
|---|---|---|---|
| **CF-S01 — US minute-return threshold crossings**, Joulin et al. | Authors report **177,674 crossings**, approximately **7–8 per stock-day**, at `abs(one-minute return) > 4 × 120-minute mean absolute return`. Raising the multiplier to 8 reduced the count about tenfold. | Complete-data window **28 Nov 2005–30 Jun 2006**, stated **149 trading days**. Text describes **163 stocks**, then **166** in the counting paragraph. | Preserve that denominator inconsistency; no exact independently replicated rate. The inspected text does not establish a one-sided window. The multiplier is neither four standard deviations nor this project's robust-return threshold. Repeated minute crossings are not distinct actionable incidents. |
| **CF-S02 — Crypto econometric jump detections**, Saef et al. | **1,392 detected jumps** across six currencies. Exact per-asset counts and eligible test-day denominators appear below. | **12 Apr 2019–27 Sep 2021**, tick trades on seven exchanges against Tether; incomplete or insufficiently liquid asset-days are excluded. | Historical, method-dependent detections, with sampling and microstructure limits; neither daily unprocessed large returns nor harmful incidents. Unique jump-day probabilities are not verified here. |
| **CF-S03 — Crypto reported-volume integrity**, Cong et al., July 2021 draft | Estimated wash volume is **71.43–77.50% of reported trade value**, volume weighted, across two Table 7 specifications for the selected unregulated group. | **9 Jul–3 Nov 2019**; 29 selected exchanges, four coins; the estimate concerns **26 exchanges classified unregulated in that study**. | This is a model estimate of trade-value share, not the percentage of fraudulent transactions or the frequency of episodes. It is not a current all-crypto census or an individual legal finding. |
| **CF-S04 — Crypto hacking harm**, Chainalysis original analysis | **303 hacking incidents** reported for 2024, versus 282 for 2023. | Article published **19 Dec 2024**, before year-end; denominator is the vendor's identified incident records. | A preliminary incident count, with no total exposed-platform/wallet denominator or independently audited complete case universe. It cannot give a per-token risk, a finalized annual rate, or the frequency of large transfers. |
| **CF-S05 — US severe execution/liquidity episode**, joint CFTC/SEC staff report | Over **20,000 executions**, across over **300 securities**, at prices at least **60% away from the 14:40 price**; those trades were later cancelled. | **6 May 2010, 14:40–15:00 ET**: one selected investigated episode. | Executions are not independent incidents; a major case demonstrates that disruption occurs but supplies no recurring population rate. Cancellations do not measure investor loss. |

CF-S02's Table 4, inspected in the publisher PDF, labels the numerator **“N jumps”** and reports the following ratios. The introduction describes BTC/ETH as jumping on roughly 58%/32% of days. Because distinct jump-date counts were not reconciled with the table's event counts, this review retains the table unit: **detected jumps per 100 eligible test days**, not a verified probability that a day contains at least one jump.

| Currency | Detected jumps | Eligible test days | Table ratio: jumps per 100 test days |
|---|---:|---:|---:|
| BTC | 499 | 865 | 57.69 |
| ETH | 277 | 865 | 32.02 |
| BCH | 194 | 858 | 22.61 |
| XRP | 169 | 865 | 19.54 |
| ETC | 145 | 793 | 18.28 |
| LTC | 108 | 861 | 12.54 |

These numbers cannot be pooled into a cross-market “anomaly percentage.” A minute threshold crossing, econometric jump, estimated wash-volume dollar, hacking incident and execution inside a crash have different counting units. Joint moves across assets and repeated flags within one episode also create dependence. Neither missed public-news matches nor multiple agreeing articles prove absence of a cause, a verified causal explanation, manipulation or fraud. The liquidity explanation in CF-S01 is explicitly a conjecture; the paper does not measure liquidity-crisis incidence.

## What this means for all 28 catalog entries

The current catalog itself states that every validation-source list is empty, and that the v0.5 labs test selected interpretation and quality failures rather than all 28 detectors. No external rate below validates this project's selected thresholds, inputs, market coverage or suppression rules.

| Catalog IDs | What the reviewed evidence can motivate | Project event frequency established? |
|---|---|---|
| AN-MKT-001 through AN-MKT-007 (7) | Price/volume/liquidity deviations and data integrity deserve investigation. CF-S01/02 concern different jump rules; CF-S03 concerns volume reliability; CF-S05 concerns one execution episode. | **No**, including cross-venue divergence and benchmark-relative rules. |
| AN-FND-001 through AN-FND-007 (7), AN-CMP-002 (1) | No reviewed US/crypto result identifies Turkish fund flow, cash, holdings changes or fund/share divergence. | **No**. |
| AN-EVT-001 through AN-EVT-004 (4) | News and official disclosures can provide context; price movement and a nearby article are different observations. | **No** frequency of useful or causally explanatory disclosures. |
| AN-ONC-001 through AN-ONC-005 (5), AN-CMP-001 (1) | CF-S04 establishes identified hacking harm; it does not count finalized large transfers, concentration changes, pool withdrawals, authority changes, unlocks or price/chain co-occurrences. | **No**. |
| AN-DQ-001 through AN-DQ-003 (3) | Incomplete observations and unreliable reported inputs matter. These studies do not supply the application's provider failure or adjustment-error rates. | **No**. |

The actionable-event rate, useful explanation rate, false-alert burden after clustering, harmful-event sensitivity, and current frequency for each of the 28 rules remain **unknown**. No complete point-in-time raw market universe was obtained or backtested in this review. No rate is inferred from a normal distribution, the project's synthetic fixtures, selected press examples, or the number of rules in its catalog.

## Cheap next measurement that could reject the product hypothesis

Before retrieving results, fix a market universe, historical interval, clock/session, adjustment policy, lookback and existing detector thresholds. Freeze them and obtain the complete eligible observation universe, including delistings where relevant. Publish excluded asset-days and reasons. Count raw threshold crossings **and** separately clustered episodes per eligible asset-day; retain shared market episodes so hundreds of securities do not become hundreds of independent stories. Do not tune thresholds on the evaluation interval.

Independently review a predeclared sample of both flagged and unflagged intervals, blinded to detector scores. Label factual deviation, independently evidenced context, unresolved cause, benign scheduled event and harm separately; preserve disagreement and unavailable evidence. Measure review minutes, bounded retrieval cost, duplicate stories, false positives, missed labeled events and abstention/omission coverage. Test whether users find the resulting investigation useful against the ordinary feed they already use. An untouched later period tests drift. The sample size should follow the intended precision and rare-event prevalence, not an invented fixed number of cases.

## Primary sources and reading depth

- **CF-S01:** Joulin, Lefevre, Grunberg and Bouchaud, *Stock price jumps: news and volume play a minor role*, [arXiv record](https://arxiv.org/abs/0803.1769), [original PDF](https://arxiv.org/pdf/0803.1769). Read selected pp. 2–3 and 8–10, not a full replication. The record is submitted 12 Mar 2008; the retrieved v1 PDF also prints “November 26, 2024,” an unresolved document-date discrepancy.
- **CF-S02:** Saef, Nagy, Sizov and Härdle, *Understanding temporal dynamics of jumps in cryptocurrency markets: evidence from tick-by-tick data*, Digital Finance 6 (2024), 605–638, [publisher article](https://link.springer.com/article/10.1007/s42521-024-00116-1), [publisher PDF](https://link.springer.com/content/pdf/10.1007/s42521-024-00116-1.pdf). Read selected introduction, data, jump-test description, §§5.1–5.2 and Table 4 (PDF p. 23). The [2025 correction](https://link.springer.com/article/10.1007/s42521-025-00131-w) adds an affiliation; its stated correction does not change these counts. Not a full-text methodological audit.
- **CF-S03:** Cong, Li, Tang and Yang, *Crypto Wash Trading*, [original July 2021 draft](https://arxiv.org/pdf/2108.10984). Read selected sample-selection/data text and Table 7 (PDF p. 46), not all 62 pages or a re-estimation.
- **CF-S04:** Chainalysis Team, [original 19 Dec 2024 analysis](https://www.chainalysis.com/blog/crypto-hacking-stolen-funds-2025/). Read the opening count and timing qualifications, not a gated annual report; commercial original analysis with methodology/completeness limitations.
- **CF-S05:** Staffs of the CFTC and SEC, [*Findings Regarding the Market Events of May 6, 2010*](https://www.sec.gov/files/marketevents-report.pdf), 30 Sep 2010. Read cover, executive-summary execution counts and selected episode timing, not the full 104-page causal investigation. It is a staff report.

The companion `cross_market_sources.json` preserves retrieval dates, tool source references, denominators, ambiguity and retrieval failures. No paid data access or LLM/provider calls were used.
