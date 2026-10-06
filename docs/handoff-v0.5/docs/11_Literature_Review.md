# Project 50K — Scientific Literature Review & Method Selection

**Version:** 0.4 audit revision · **Prepared:** 2026-10-02
**Status:** implementation specification / not a claim of deployed functionality.

## Review protocol and limits
This is a targeted engineering literature review, not a systematic review or an empirical replication. Inclusion: primary research relevant to market time series, funds, manipulation-pattern screening, uncertainty, retrieval and tool use. Search date: 2026-10-02. Publisher/proceedings pages and author abstracts were consulted; the table states depth. Papers have not all been read in full. No reported accuracy is transferred to Project 50K.

Queries covered robust financial anomalies, intraday seasonality, online/offline change points, fund flows, cryptocurrency pump-and-dump, calibration, multiple testing, RAG and citation faithfulness. Prioritize foundational methods over recency alone; a later systematic search and full-paper implementation review remain release tasks.

## Evidence map

### R01 — Empirical properties of asset returns: stylized facts and statistical issues
**Authors/year:** Rama Cont, 2001. **Venue:** Quantitative Finance.

**Primary source:** https://www.tandfonline.com/doi/abs/10.1080/713665670

**Review depth:** publisher abstract/search excerpt.

**Contribution:** Return distributions and volatility behavior motivate robust, regime-aware baselines.

**Limitations:** Broad financial-market evidence, not a calibrated BIST fraud classifier.

**Project decision (our design, not a paper result):** Use robust scores and validate tails locally; never map a sigma value directly to a fraud probability.

### R02 — Intraday periodicity and volatility persistence in financial markets
**Authors/year:** Torben G. Andersen; Tim Bollerslev, 1997. **Venue:** Journal of Empirical Finance.

**Primary source:** https://www.sciencedirect.com/science/article/pii/S0927539897000042

**Review depth:** publisher abstract.

**Contribution:** Intraday periodicity materially affects volatility dynamics.

**Limitations:** Different markets and historical periods; proposed local thresholds are not supplied by the paper.

**Project decision (our design, not a paper result):** Compare the same session slot; separate auctions, overnight gaps and continuous trading.

### R03 — Isolation Forest
**Authors/year:** Fei Tony Liu; Kai Ming Ting; Zhi-Hua Zhou, 2008. **Venue:** IEEE ICDM.

**Primary source:** https://ieeexplore.ieee.org/document/4781136

**Review depth:** publisher abstract.

**Contribution:** Random isolation offers a multivariate anomaly approach.

**Limitations:** An anomaly score is not a supervised probability; contamination and features change results.

**Project decision (our design, not a paper result):** Challenger only after baselines; train on past data, record seed, features and training cutoff.

### R04 — Bayesian Online Changepoint Detection
**Authors/year:** Ryan Prescott Adams; David J. C. MacKay, 2007. **Venue:** arXiv preprint.

**Primary source:** https://arxiv.org/abs/0710.3742

**Review depth:** author abstract.

**Contribution:** Online inference tracks the run length since a possible distribution change.

**Limitations:** Hazard and likelihood assumptions matter; not an out-of-box market-abuse detector.

**Project decision (our design, not a paper result):** Later regime-change detector; test detection delay and likelihood misspecification.

### R05 — Selective review of offline change point detection methods
**Authors/year:** Charles Truong; Laurent Oudre; Nicolas Vayatis, 2020. **Venue:** Signal Processing.

**Primary source:** https://arxiv.org/abs/1801.00718

**Review depth:** author abstract and publication metadata.

**Contribution:** Organizes offline change-point algorithms by cost, search and change-count constraints.

**Limitations:** Offline segmentation can see future observations.

**Project decision (our design, not a paper result):** Use ruptures-style offline analysis only for research/labels, not claim-time live detection.

### R06 — Current Time Series Anomaly Detection Benchmarks are Flawed and are Creating the Illusion of Progress
**Authors / year / venue:** Renjie Wu; Eamonn J. Keogh · 2023 final issue · IEEE TKDE 35(3):2421–2429; early access 2021; arXiv 2009.13807v5 revised2022-09-03. DOI 10.1109/TKDE.2021.3112126.

**Primary source:** https://arxiv.org/abs/2009.13807

**Review depth:** author abstract and publication metadata.

**Contribution:** Documents flaws that can distort anomaly benchmark comparisons.

**Limitations:** General benchmark critique; it does not label Project 50K events.

**Project decision (our design, not a paper result):** Keep normal controls, point-in-time datasets and explicit event matching; no showcase-only accuracy.

### R07 — On Calibration of Modern Neural Networks
**Authors/year:** Chuan Guo; Geoff Pleiss; Yu Sun; Kilian Q. Weinberger, 2017. **Venue:** ICML / PMLR 70.

**Primary source:** https://proceedings.mlr.press/v70/guo17a.html

**Review depth:** proceedings abstract.

**Contribution:** Confidence calibration requires predicted probabilities to match observed correctness.

**Limitations:** Image/text classification experiments; temperature scaling does not calibrate an arbitrary weighted score automatically.

**Project decision (our design, not a paper result):** Separate evidence strength from probability; assess Brier score and reliability only with labels.

### R08 — Conformal prediction beyond exchangeability
**Authors/year:** Rina Foygel Barber; Emmanuel J. Candes; Aaditya Ramdas; Ryan J. Tibshirani, 2023. **Venue:** Annals of Statistics; author preprint 2022.

**Primary source:** https://arxiv.org/abs/2202.13415

**Review depth:** author abstract.

**Contribution:** Studies predictive inference when exchangeability is weakened.

**Limitations:** Coverage assumptions and drift still matter; a prediction set is not a fraud probability.

**Project decision (our design, not a paper result):** Research option, not a weekend guarantee of 95% coverage on financial time series.

### R09 — Controlling the False Discovery Rate: A Practical and Powerful Approach to Multiple Testing
**Authors/year:** Yoav Benjamini; Yosef Hochberg, 1995. **Venue:** JRSS Series B.

**Primary source:** https://academic.oup.com/jrsssb/article/57/1/289/7035855

**Review depth:** publisher abstract.

**Contribution:** Controls a multiple-testing error criterion under stated assumptions.

**Limitations:** Overlapping assets/times are dependent; heuristics are not automatically valid p-values.

**Project decision (our design, not a paper result):** Measure alert burden across the universe; do not promise FDR control without justified tests.

### R10 — Costly Search and Mutual Fund Flows
**Authors/year:** Erik R. Sirri; Peter Tufano, 1998. **Venue:** Journal of Finance.

**Primary source:** https://onlinelibrary.wiley.com/doi/10.1111/0022-1082.00066

**Review depth:** publisher abstract.

**Contribution:** Fund flows relate asymmetrically to past performance and search costs.

**Limitations:** Historical equity mutual funds outside Türkiye; flow changes are not misconduct evidence.

**Project decision (our design, not a paper result):** Contextualize subscriptions/redemptions and category behavior; do not equate outflow with fraud.

### R11 — To the moon: defining and detecting cryptocurrency pump-and-dumps
**Authors/year:** Josh Kamps; Bennett Kleinberg, 2018. **Venue:** Crime Science 7,18.

**Primary source:** https://link.springer.com/article/10.1186/s40163-018-0093-5

**Review depth:** publisher abstract and accessible article.

**Contribution:** Combines pump-and-dump definitions with anomalous trading-pattern screening.

**Limitations:** Historical exchanges and selected events; labels and thresholds are not portable to BIST or major coins without testing.

**Project decision (our design, not a paper result):** Use price/volume patterns as research candidates and report suspicious behavior, not legal verdicts.

### R12 — The Anatomy of a Cryptocurrency Pump-and-Dump Scheme
**Authors/year:** Jiahua Xu; Benjamin Livshits, 2019. **Venue:** 28th USENIX Security Symposium.

**Primary source:** https://www.usenix.org/conference/usenixsecurity19/presentation/xu-jiahua

**Review depth:** conference abstract.

**Contribution:** Examines organized cryptocurrency pump-and-dump activity.

**Limitations:** Coordination evidence depends on data excluded from our social-media-free MVP.

**Project decision (our design, not a paper result):** Record the information gap; price plus a transfer cannot prove coordinated control.

### R13 — Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks
**Authors/year:** Patrick Lewis et al., 2020. **Venue:** NeurIPS.

**Primary source:** https://arxiv.org/abs/2005.11401

**Review depth:** author abstract.

**Contribution:** Retrieval adds external knowledge to generation.

**Limitations:** Retrieval does not establish source truth or eliminate unsupported synthesis.

**Project decision (our design, not a paper result):** Use dated evidence packets and verify claim-level references.

### R14 — ReAct: Synergizing Reasoning and Acting in Language Models
**Authors/year:** Shunyu Yao et al., 2023. **Venue:** ICLR; author preprint 2022.

**Primary source:** https://arxiv.org/abs/2210.03629

**Review depth:** author abstract.

**Contribution:** Interleaves language-model reasoning and tool interaction.

**Limitations:** Benchmark results are not financial accuracy evidence; unrestricted tool autonomy adds risk.

**Project decision (our design, not a paper result):** Bounded read-only asset investigation with budgets and logged tool actions, not hidden chain-of-thought storage.

### R15 — Enabling Large Language Models to Generate Text with Citations
**Authors/year:** Tianyu Gao; Howard Yen; Jiatong Yu; Danqi Chen, 2023. **Venue:** EMNLP.

**Primary source:** https://aclanthology.org/2023.emnlp-main.398/

**Review depth:** proceedings abstract.

**Contribution:** Studies citation generation and evaluation of attributed answers.

**Limitations:** A displayed citation may still fail to support the attached claim.

**Project decision (our design, not a paper result):** Test citation completeness and entailment separately from prose fluency.

## Method selection
**Weekend baseline:** completed-bar log returns with robust, same-session-slot historical references; relative volume; simple benchmark residual; return-adjusted fund-flow estimate only with aligned valid inputs; asset-type allocation distance; structured official-event extraction. These favor transparency and testability, not a claim that simple models are universally superior.

**Challengers after baseline validation:** Isolation Forest on quality-gated features; online change-point detection for shifts; retrieval-aware semantic classifiers with held-out labeled disclosures. Reject a challenger unless it improves event-level usefulness at a comparable alert burden and latency.

**Deferred:** offline segmentation used as live evidence; deep sequence models trained on a few selected cases; conformal coverage claims without dependence/drift analysis; hidden-owner manipulation classification without account-level evidence.

## Scientific-to-requirement bridge
| Research concern | Requirement / implementation consequence | Falsification test |
|---|---|---|
| Intraday periodicity [R02] | FR-049/050, DR-003: match market/session slot | Opening-auction volume should not dominate continuous-session false alarms. |
| Benchmark/evaluation flaws [R06] | NFR-038/080: sequential cutoff, negative controls | Adding future documents must not change an earlier run. |
| Calibration [R07,R08] | FR-067 amendment: evidence score vs calibrated probability | All MVP probability fields remain null. |
| Multiple comparisons [R09] | FR-085: notification budget distinct from detection | Alert burden measured per 100 asset-days, not just per selected event. |
| Fund flow context [R10] | FR-033/034/037: date alignment and return adjustment | AUM decline entirely due to NAV decline produces zero estimated net flow. |
| Attribution [R13,R15] | FR-058/096, NFR-081: claim-evidence mapping | Plausible unrelated citation must be rejected. |
| Tool reasoning [R14] | FR-060/097: bounded read-only investigation | Tool-injected instructions cannot access admin actions or secrets. |

## Replication program
EXP-01 compares naive percent-change alerts with robust session baselines. EXP-02 tests adding benchmark residuals. EXP-03 adds contextual retrieval but tests whether it reduces misleading causal wording, not whether it predicts price. EXP-04 evaluates fund-specific signals with independent category controls. EXP-05 assesses citation grounding in Turkish.

All experiments require frozen configurations, chronological train/validation/test splits, immutable input manifests, known source availability, normal periods and disclosed limitations. See documents 13 and 20 for concrete measurements. Full texts, proprietary datasets and empirical market backtests are not bundled.

## v0.4 audit review depth
All fifteen references are identifiable as real works. This audit checked primary metadata and selected content at the per-reference depth recorded in `research/scientific_sources_verification.json`; R01 body retrieval failed and R09 PDF text extraction was empty. Selected sections of R03/R11/R12/R15 were inspected; no exhaustive full-paper review or empirical replication is claimed. Complete structured bibliography metadata and version distinctions are in `research/bibliography_audit.json`.

## Problem solution and market research continuation 3 October 2026

Original historical US/crypto papers provide method-specific counts, not our thresholds or current harmful-event prevalence. CF-S01 is a multiplier of mean absolute returns, not standard deviations; window orientation and stock-count inconsistency remain unresolved. CF-S02 Table 4 counts jumps per eligible test days; distinct jump-day probability was not independently reconciled. Behavioral attention evidence does not establish Turkish unmet need. See `reports/PROBLEM_MARKET_RESEARCH.md` and the linked source-depth appendices.
