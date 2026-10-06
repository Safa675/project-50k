# Project 50K — Arithmetic risk scenarios

**Reviewed:** 2026-10-03, Europe/Istanbul. **Status:** authored sensitivity analysis, not measured detector performance, real provider pricing or a forecast. Code: `experiments/risk_scenarios.py`; exact results: `risk_scenario_results.json`.

## Rare targets can make apparently small error rates expensive

For an explicitly defined binary target, population positive predictive value is `p × sensitivity / (p × sensitivity + (1−p) × false_positive_rate)`, where `p` is target prevalence across eligible decision opportunities. This is Bayes arithmetic with supplied rates. It is a ratio of expected counts/population probability, not mean precision in a random finite sample. Whether a statistically unusual point is useful to a person is another target and needs its own labels.

With **assumed** prevalence 0.1% and sensitivity 80%:

| Assumed false-positive rate on target-negative decisions | Population positive predictive value |
|---|---|
| 1% | 7.41% |
| 0.1% | 44.47% |
| 0.01% | 88.90% |

At 100,000 decision opportunities, the first row gives expected true positives 80, false positives 999 and misses 20. Fractional expected counts elsewhere are legitimate expectations, not partial observed events. No actual prevalence, sensitivity or error rate has been measured for this product. The table therefore proves neither that the product will be noisy nor that a specific threshold will solve it. It demonstrates why a threshold, accuracy score or toy recall alone cannot establish alert quality.

The script contains 16 prevalence/FPR combinations. It checks conservation and monotonicity, not generalization or independent event quality. Correlation does not invalidate linearity of expected point counts given correct marginal rates, but it affects uncertainty, clusters and user-level burden.

## Point candidates are not notifications

An authored all-null universe of 1,000 assets, each with 78 eligible observations per day, creates 78,000 point decisions. An assumed 1% point FPR produces **780 expected false point candidates**, not 780 emails. At 0.1% it gives 78 candidates. The 78-slot cadence is illustrative, not a BIST/US/crypto/fund calendar claim. Eight scenarios vary asset count, cadence and FPR.

Eligibility, source gaps, joint features, episode grouping, severity, relevance and consent intervene before notifications. Notification precision cannot be inferred from this table. Conversely, a hard daily cap can make notification counts small while silently discarding useful events. Record eligible opportunities, candidate burden, event/episode outcomes, delivery and missed targets separately.

## A cumulative ceiling requires an operating horizon

The owner ceiling is TRY 5,000 total, excluding only development Claude/Codex subscriptions. Every number below **except that ceiling is invented for sensitivity analysis**. Suppose setup uses TRY 1,000 and reserve remains TRY 500: recurring services can consume TRY 3,500 in total.

| Invented all-in recurring cost/month | Modeled fractional months | Whole months fundable under this simple model |
|---|---|---|
| TRY 200 | 17.5 | 17 |
| TRY 1,000 | 3.5 | 3 |
| TRY 3,000 | 1.17 | 1 |

These are not quotations or an affordable operating plan. Monthly/annual prepayment, currency changes, taxes, minimum commitments, data rights, renewals and variable usage can change feasibility. The zero-recurring-term case has no finite limit from that term alone, but supplies no proof of free or perpetual operation. A monthly allowance must never reset the cumulative ceiling.

## Chat quota is an exposure, not an expected bill

The configured 10-turn daily user ceiling permits 100 active users to request **30,000 turns in 30 days**. At an assumed two turns/day the workload is 6,000. Neither is a measured demand forecast. With the invented TRY 3,500 remainder, allocating *all* of it to chat would leave maximum average costs about TRY 0.1167 and TRY 0.5833 per turn, respectively. Those upper bounds leave no room for additional hosting/data/email unless already represented; shared event investigations, retries and failed requests add workload.

No price/token/model latency was supplied to the experiment. Measure actual usage and current scoped quotes before forming an affordability conclusion. User limits, project reservation and shared event caching address different exposures; a tool-call cap alone does not bound model calls or daily total spend.

## Reproduction and limits

Run `python experiments/risk_scenarios.py --output <path>`. Output contains 16 precision, eight point-burden, four cumulative-budget and four quota scenarios; 15 authored arithmetic invariants pass. Their count measures only these checks. All observations/prices are assumptions, no market samples or paid calls are used. Undefined precision is retained as null instead of converted to perfect/zero performance. Source: owner ceiling and existing quota specification; remaining quantities are hand-authored. The result includes the script SHA-256.
