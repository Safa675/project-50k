# BIST frequency: what the retrieved evidence can establish

**Reviewed:** 2026-10-03. **Status:** primary-source desk research and arithmetic on published aggregates; no market-data backtest, complete circuit-breaker export or product-detector evaluation.

There is a substantial official information stream, but this review cannot defensibly state how many Project 50K anomalies occur per day in BIST. Its 28 catalog entries span statistical movements, disclosures, funds, on-chain observations and data-quality states. They are not one homogeneous event population. Their project-authored thresholds remain unvalidated [P01]. Circuit-breaker activations are a narrower exchange-rule event, not fraud findings or labels for the entire catalog.

## Complete-year published information counts

[MKK's 2025 report](https://www.mkk.com.tr/sites/default/files/2026-04/MKK_2025.pdf), PDF page index 31 / printed page 31, reports these KAP notification counts [F01]. The [other official report layout](https://www.mkk.com.tr/sites/default/files/2026-06/MKK-2025.pdf), PDF index 31 / printed page 30, gives the same five category values and total [F02].

| Published category | 2025 notifications | 2024 comparator |
|---|---:|---:|
| Fund notifications | 79,357 | 60,742 |
| Special disclosures | 35,944 | 32,902 |
| Regulatory notifications | 16,920 | 17,716 |
| Other | 15,426 | 15,385 |
| Financial reports | 14,112 | 13,058 |
| Total | 161,759 | 139,803 |

**Defined rates:** numerator = the reported notification count; denominator = **365 calendar days**, 1 January–31 December 2025; population = the KAP publication categories above. Local arithmetic gives **443.18 total notifications/calendar day** and **98.48 special disclosures/calendar day**. These are annual average publication throughput, not counts observed on each day, distinct material developments, BIST-stock-only rates or anomaly prevalence. No sampling confidence interval is appropriate for simply restating a published full-year aggregate. The total reconciles exactly with the five rows.

Do not divide these counts by BIST's year-end company count: the populations differ, membership changes, and the aggregate does not resolve notification revisions, translations or multiple notices into unique underlying events. The data supports a source-monitoring workload premise, not a claim that hundreds of user-relevant anomalies happen every day. It also does not measure user demand.

## Circuit breakers are a measurable candidate series, but no complete numerator was collected

[Borsa İstanbul's market rules](https://www.borsaistanbul.com/piyasalar/pay-piyasasi/piyasa-isleyisi), retrieved 3 October 2026, describe downward-only 5% share-level breakers using an auction/base reference, and a market-wide BIST100 rule at a 6% fall versus the previous close [F03]. A share-level reference is not simply the prior daily close. An activation therefore cannot be reconstructed reliably by counting daily close-to-close declines alone.

The [29 August 2025 notice](https://www.borsaistanbul.com/files/duyuru-38860-TR.pdf) changes market-wide EBDKS from 5%/7% stages to one 6% stage, effective **1 September 2025** [F04]. A 2025 analysis must record this regime change. Two stage activations on one date are not two distinct affected market days. Share-level activations, unique share-days and market-wide affected dates require separate numerators and denominators.

The [official KAP guide](https://kap.org.tr/tr/api/about/content-file/402832a195b3017d0195bd17e2e07e9a) documents detailed issuer/topic/date queries, a maximum one-year range and bulk Word/Excel export [F05]. However, the circuit-breaker sender listing failed retrieval and no complete date-bounded export was obtained [F06]. Indexed incident snippets establish neither archive completeness nor annual totals. No `observed_events.json` was created because this review has no genuine complete auditable event sample.

The [BIST 2025 annual report](https://www.borsaistanbul.com/files/faaliyet-raporu-2025.pdf) was opened, but later targeted retrieval failed; the inspected excerpts did not provide an activation numerator [F07]. This is a retrieval limitation, **not** a claim that no official aggregate exists. Neither unknown count is treated as zero.

## The next frequency measurement must freeze its meaning first

1. **Official-rule series:** obtain a complete bounded KAP export; preserve notification IDs, full timestamps, instruments, breaker subtype, revisions and query/export boundaries. Reconcile all pages/rows and original-versus-correction semantics. Count activation records, unique asset-dates and unique market-wide dates separately. Join the actual eligible trading calendar and historical rule regimes; validate exceptional closures and half-days before publishing a trading-day rate.
2. **Product numerical candidates:** use an entitled point-in-time BIST cohort with completed, same-feed bars, adjustments and prior-only baselines. Freeze bar interval, session exclusions, universe, thresholds and missing-data policy before evaluation. Report tested eligible bars and eligible asset-days, abstention coverage, raw flags, distinct streaming episodes and recipient alert burden separately. A circuit breaker is an external reference event, not universal ground truth for price/volume or issuer-disclosure detectors.
3. **Useful verified events:** independently adjudicate relevance, supported factual claims and explanation quality. A true unusual move can have an ordinary explanation; a disclosure can be useful without a price outlier. Precision, usefulness and detection delay need their own definitions and measured denominators.

Project thresholds such as RVOL3, robust |z|4 and 20 prior comparable samples specify a proposed trigger, not its real frequency [P01]. Synthetic lab alert rates are conditional on invented distributions and must not be substituted for BIST estimates [P02]. No forecasting, fraud prevalence, market sizing or financially meaningful detection performance is established here.

Source URLs, dates, retrieval depth, refs, raw numeric table cells and calculations are retained in `bist_frequency_sources.json`. Only the two assigned research files were written; no account, contact, paid service, code change or live experiment occurred.
