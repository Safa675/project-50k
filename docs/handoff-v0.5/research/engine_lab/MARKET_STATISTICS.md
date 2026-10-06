# Market statistics laboratory

**Date:** 2026-10-02 · **Version:** market-statistics-synthetic-v1 · **Mode:** SYNTHETIC ONLY.

This laboratory changes no production detector, threshold, contract or product acceptance. It studies failure mechanisms using constructed observations. It is not a BIST/US/crypto historical backtest, financial forecasting experiment, calibrated classifier or evidence that users avoid losses. All reported rates are conditional on explicitly chosen generators and labels. Real financial observations: **0**.

**Trace:** FR-048–054, FR-065–070, FR-085–090, FR-108–110; NFR-004, NFR-022–026, NFR-035–040, NFR-068–069, NFR-079–080. No requirement is marked implemented or empirically validated by these simulations.

## Reproduce

From the package root:

```sh
PYTHONDONTWRITEBYTECODE=1 python experiments/market_statistics.py
PYTHONDONTWRITEBYTECODE=1 python experiments/market_statistics.py --output research/engine_lab/market_results_reproduction.json
```

Dependencies: Python standard library and the package's offline `reference.engine`. No installations, API credentials, paid calls, downloads of market datasets or external actions. Defaults: 12 fixed independent seeds; 500 multiple-testing batches per seed/scenario; 200 assets per batch. Exact seeds, parameters, script/reference hashes, Python version, denominators, per-seed outputs and Monte Carlo intervals are in `market_results.json`. Actual CLI output is in `market_run.log`.

Both commands completed successfully. Parsed results from the two runs were **exactly equal**, including metadata and every numerical field; the recorded script hash matched the executed source. No scenario, threshold or seed was optimized after inspecting results. OLS parameters alone are estimated from an earlier disjoint 120-observation prefix. There is no threshold-development search, learned anomaly model or hidden choice of best seeds.

Uncertainty: arithmetic means across independent seeds; standard error across seeds; approximate two-sided t interval with df 11 for the default 12 seeds. These quantify Monte Carlo variability of this simulator, not uncertainty about real-market performance. Some unbounded approximate t intervals for rates can extend outside [0,1]; they are not probability bounds. Zero seed variability in an easy constructed case is not proof of perfect reliability.

## Primary-source review and inference boundary

Six dated records, URLs, retrieval identifiers, failed routes and actual review depth are in `market_sources.json`. These are primary works/official documentation, not a claim of a complete paper corpus or systematic review.

- **MS-01:** Andersen/Bollerslev (1997) motivates respecting intraday periodicity. The author-hosted paper's indexed introduction and an institutional abstract were readable; direct scanned-PDF extraction was empty. Its evidence does not validate this project's volume multiplier, threshold 3, sample size 20 or current BIST/crypto applicability. [Author copy](https://public.econ.duke.edu/~boller/Published_Papers/joef_97.pdf).
- **MS-02/03:** BH's original publisher summary and the original BY paper uploaded by Yoav Benjamini were checked. BY sections1.2–1.4 give the BH step-up rule, FDR definition, dependence restriction and harmonic modification. Theorem1.3 does not repair invalid null p-values. Euclid's direct page was iframe-only; the separate author draft extracted as garbled text. Selected readable original-paper sections were used, without independently verifying the proof. [BH](https://rss.onlinelibrary.wiley.com/doi/10.1111/j.2517-6161.1995.tb02031.x), [BY author-uploaded original](https://www.researchgate.net/publication/38348313_The_control_of_the_false_discovery_rate_in_multiple_testing_under_dependency).
- **MS-04:** Barber et al., arXiv2202.13415v5, explains exchangeability/symmetry and calibration splitting; selected drift/weight remarks were read. This motivates caution about financial rank calibration. Its specialized methods were not implemented or replicated. [Manuscript](https://arxiv.org/html/2202.13415v5).
- **MS-05:** MacKinlay's original-paper indexed page15 motivates a stable linear market relation and an estimation window preceding the event. This is a methodological motivation, not an assertion that beta-one or OLS is valid under regime change. [Academic-hosted paper copy](https://www.bu.edu/econ/files/2011/01/MacKinlay-1996-Event-Studies-in-Economics-and-Finance.pdf).
- **MS-06:** Official Alpaca bars documentation distinguishes IEX/SIP/other feeds and raw/split/dividend/spin-off adjustments; symbol `asof` defaults to the current date. This supports explicit feed/adjustment/entity mapping. It supplies no entitlement or genuine point-in-time dataset here. [Official reference](https://docs.alpaca.markets/us/reference/stockbars).

Everything below is our inference/experiment design, not a numerical result attributed to those papers.

## Experiment A — seasonal volume and an honest flat control

Constructed volume is `1000 * profile(slot) * exp(N(0,0.5²))`. Each scenario has six assets, an 80-session prefix and 80 evaluation sessions. Equity uses eight constructed slots with profile `[6,2,1.2,1,1,1.2,2,6]`; crypto uses24 UTC slots with either `1+0.7*cos(2π*slot/24)` or a flat profile. These are stress profiles, not exchange calendars or estimated seasonality.

Each asset receives six predeclared single-bar fourfold injections, independent of random noise and scorer:36 positives per seed/scenario, 432 across 12 seeds. Controls count every uninjected bar, including naturally large noise realizations. Each method sees exactly the same data and injected labels. Pooled20 and same-slot20 both use20 previous sessions; pooled picks one rotating eligible slot per session, controlling sample count/horizon. Same-slot60 changes both sample size and adaptation horizon. Evaluation injections can subsequently enter causal rolling history; no injected observation is removed using future labels.

| Constructed scenario | Pooled20: false flags/100 asset-days | Same-slot20 | Same-slot60 | Injection recall pooled20 → same-slot20 |
|---|---:|---:|---:|---:|
| Equity U shape | 135.28 | 12.47 | 11.44 | 60.88% → 68.75% |
| Crypto UTC cycle | 211.11 | 38.35 | 34.03 | 53.01% → 68.29% |
| Crypto flat control | 39.48 | 39.46 | 34.98 | 71.06% → 72.45% |

Matched-seed reduction pooled20 minus same-slot20: equity **122.81** [121.15,124.47] false flags/100 asset-days; crypto cycle **172.76** [167.94,177.58]; flat control **0.017** [-1.41,1.44]. Brackets are simulator-conditional95% Monte Carlo intervals.

Matching removes the deliberately constructed periodicity error; the flat control shows no clear matching advantage. It does **not** make threshold 3 sufficient for low notification burden. Same-slot20 still produces about12.5 or38.4 false flags/100 asset-days here. These counts exceed100 when there are multiple flags per asset-day. Crypto has 24 opportunities/day versus eight in the equity construction, so cross-scenario counts must not be interpreted as intrinsic crypto risk; null-bar rates and denominators are separately retained.

A flagged uninjected bar is a statistical null-control error under this generator, not a false criminal allegation or a financial-loss label. Auctions, holidays, half-days, day-of-week effects, persistence, sparse/zero trade volumes, regime shifts and market microstructure are absent from this experiment. Increasing 20 to 60 is a modest gain here and can slow adaptation elsewhere; it is not a recommendation to silently change the package's minimum of 20.

## Experiment B — shared shocks and the failure of a universal beta

Constructed market returns are N(0,.002²), asset residuals N(0,.003²), with twelve asset betas spread from 0.4 to 1.8. Fit prefix 120; evaluation 90. Six market shocks add ±.04 log return to the market; six asset-specific additions of+.03 are spread across assets, three coinciding with market shocks. Labels distinguish ordinary noise, market-only and asset-specific—including mixed events. Raw, beta-one and prior OLS comparisons share every observation.

All methods retain the reference z4 and1% absolute simple-return floor. Residual computations are approximate contextual statistics; none gets a normal-tail probability.

| Constructed regime / statistic | Raw return | Beta-one residual | Prior OLS residual |
|---|---:|---:|---:|
| Stable beta: market-only asset flag rate | 99.03% | 58.82% | 5.56% |
| Stable beta: injected asset-event recall | 95.83% | 97.22% | 100.00% |
| Beta increases0.8 after training: market-only flag rate | 100.00% | 88.04% | 100.00% |
| Beta increases0.8: injected asset-event recall | 98.61% | 100.00% | 83.33% |

A market-only raw flag is often a correct unusual market observation. The error would be interpreting every such flag as an independent asset-specific problem. Fitted OLS removes much of the stable common component, but estimation error still matters: stable-regime market-only rate5.56% has MC interval[2.37%,8.74%]. Under beta drift, OLS breaks and a mixed event can cancel against model error. Discarding the raw/common context in favor of a residual-only stream loses information.

**Implication:** keep raw movement and benchmark context separate. Beta-one is an inspectable MVP approximation, not a complete explanation. Defer production fitted-beta publication until benchmark mappings, sufficient licensed aligned history, coefficient uncertainty and drift diagnostics exist. No cross-sectional subtraction can establish the cause of an event.

## Experiment C — multiplicity, wrong tails and the time axis

Each seed generates 500 independent batches of 200 assets in four scenarios. Methods use identical p-values within each batch: uncorrected per-test q=.05, BH q=.05 and BY q=.05 with harmonic factor `H_200`. There are 24,000 batches and 4.8 million constructed marginal values across the default run.

The Gaussian scenarios have **known oracle null means/variances**, providing legitimate two-sided Gaussian p-values. One scenario has within-batch correlation0.3; the reported BH observation is not a proof that arbitrary two-sided dependence meets PRDS. The mixed case shifts 20 alternative means by 3.5. The adversarial all-null t3 case has variance1 but computes **wrong Gaussian p-values**; its violation is deliberate and labeled in every per-seed record. No robust MAD score is converted into a production p-value.

| Constructed case | Per-test observed batch FDR | BH | BY | BH → BY power, when alternatives exist |
|---|---:|---:|---:|---:|
| Independent Gaussian all null | 100.00% | 4.73% | 0.97% | n/a |
| Correlated Gaussian all null | 99.65% | 4.12% | 0.75% | n/a |
| Independent Gaussian,10% shifted | 31.80% | 4.47% | 0.79% | 72.71% → 49.11% |
| t3 all null, wrongly Gaussian tails | 99.98% | 81.13% | 69.88% | n/a |

FDR is the **mean over batches of V/max(R,1)**, not false counts divided by pooled counts. In all-null scenarios, FDR equals probability of any false rejection. Uncorrected independent Gaussian testing averages10.018 false rejections per batch; BH averages0.0527; BY0.0097. Wrong-tail BH FDR MC interval[80.19%,82.08%], BY[68.73%,71.03%]: multiplicity correction cannot compensate for invalid p-values.

Time also matters. In the independent all-null Gaussian scenario, the observed probability of at least one false rejection across90 consecutive independent batches was98.33% for BH and61.67% for BY. Only five nonoverlapping90-batch blocks per seed are available; this time-axis result is deliberately coarse. A per-batch guarantee is not a per-day/user guarantee. No online or anytime-valid procedure is implemented.

Nonrandomized calibration-rank resolution provides another constraint: `p_min=1/(n+1)`. For n=20 it is0.04762 and n=60 is0.01639. With m=200/q=.05, the first BH cutoff is0.00025 and BY0.00004253. One isolated most-extreme rejection would need at least3,999 or 23,512 calibration observations, respectively. This is resolution arithmetic, not sample size sufficiency or a finance calibration guarantee; many simultaneous low ranks can pass a later BH rank. Ordinary rank validity also requires appropriate exchangeability/score construction. Keep FDR/conformal deployment **deferred**, not cosmetically added to z4.

## Experiment D — robustness is conditional, leakage changes the question

For each seed,200 matched trials compare a current+.03 log-return event against40 prior N(0,.002²) values. Fractions of prior history are replaced by+.03 values. Mean/SD and median/MAD share each matched trial. This is adversarial contamination, not a measured frequency of historical market corruption.

| Contaminated fraction | Median/MAD detection | Mean/SD detection |
|---|---:|---:|
| 0% | 100.00% | 100.00% |
| 10% | 100.00% | 0.00% |
| 30% | 99.92% | 0.00% |
| 50% | 0.00% | 0.00% |
| 60% | 0.00% | 0.00% |

The median/MAD comparison resists the chosen minority contamination; it does not survive a majority shift. At 60% repeated values the MAD is zero and the reference correctly abstains. A sustained new regime may require a separate contextual change detector rather than perpetual outlier claims. Successful toy resistance is not a financial breakdown-point guarantee for serial, rounded or illiquid data.

A separate leakage counterexample uses twenty simulated prior values versus a forbidden window with only four past values and sixteen copies of the current/future shifted level. Across all 12 seeds, causal scoring yields CANDIDATE and the leaky calculation ABSTAINED. Contamination/future fitting can hide the very episode being evaluated; no later knowledge enters the valid detector comparisons. The intentionally leaky branch is marked as a counterexample, never a valid method.

## Experiment E — floods, shared context, and mechanical guardrails

A constructed shared episode has twenty assets, nine persistent bars and three **exactly dependent representations of one price family**. Counts:540 feature flags →180 same-bar asset merges →60 records under a four-bar cooldown. Oracle asset-episode identity would yield20 timeline records; oracle shared-market context yields one common record with linked assets. These last groupings use identities supplied by the generator, not a trained/implemented clustering algorithm. They do not erase the individual asset evidence.

Another counterexample has two distinct supported events for the same asset/family two bars apart. Naive cooldown delivers one of two. Cooldown is a burden guard, not the source of truth for whether a new event/material update exists. A60-minute policy still needs stable event identity, material-change classes and scope-aware aggregation; no external email is performed or authorized here.

Mechanical cases across 12 seeds:

| Counterexample | Unchecked assertion | Guarded/verified result |
|---|---|---|
| Raw2-for-1 split looks like a50% decline | CANDIDATE | Unknown adjustment ABSTAINED; correctly adjusted comparison NOT_FLAGGED |
| Feed volume jumps100→500 with feed identity changed | CANDIDATE | Mixed-feed guard ABSTAINED |

The5x feed change is constructed, not a measured IEX/SIP ratio. Flags are assertions supplied to the reference helper; these cases do not prove automatic corporate-action or provider-switch detection. A production provenance layer must validate entity, feed/venue, unit, session, adjustment and source revision, then reset incompatible baselines rather than guess transformations.

## Hypothesis register

| Hypothesis | Decision | Conditions / counterexample |
|---|---|---|
| Session/slot-aware causal references should be retained | KEEP | Comparable feed/unit/session and sufficiently valid prior observations; flat control shows no universal advantage. |
| Median/MAD is a useful small inspectable starting statistic | KEEP | Explicit scale/zero-MAD guards; minority-contamination result conditional; no tail/probability claim. |
| RVOL3 or z4 inherently gives low notification burden | REJECT | Synthetic same-slot baseline still flags many null bars; empirical per-market evaluation absent. Retain current settings as provisional, not validated. |
| Beta-one is a complete common-shock adjustment | REJECT | Heterogeneous betas leave58.82% market-only flags in this construction. Keep it only as disclosed contextual approximation. |
| A fitted beta automatically solves the market-context problem | DEFER | Stable-regime benefit; regime-change failure. Need history, identity, uncertainty and drift evidence before production use. |
| BH/BY can calibrate arbitrary robust anomaly scores | REJECT | Wrong Gaussian tails defeat both. Valid p-values/families are prerequisites, not outputs of correction. |
| Production FDR/rank/conformal layer is ready with 20 values | DEFER | Sparse-rank resolution, exchangeability, drift, overlapping/time families and operational labels unresolved. |
| Merge same-family/window events and preserve shared context | KEEP | Deterministic identities, visible linked asset evidence, revisions and separate material updates; oracle counts are design motivation only. |
| Cooldown alone solves deduplication | REJECT | Two distinct events inside cooldown lose one. Policy must distinguish retries from genuinely new material evidence. |
| Corporate-action/feed/session/provenance incompatibility must abstain/reset | KEEP | Verified metadata; no guessed adjustment, hidden feed substitution or relabeling unknown data as safe. |

## Recommended implementation/evaluation slice

Keep the lightweight hybrid. Validate one lawful point-in-time market adapter, comparable completed bars and session/corporate-action/feed metadata before calculating signals. Compute raw return, same-slot RVOL and disclosed benchmark context separately. Store every baseline/config/source dependency. Build deterministic asset/family/window identities and a separate shared context record; avoid counting return/momentum/volatility as independent corroboration.

Meaningful AI remains essential: investigate dated official disclosures/news, classify supported context, surface contradictions and alternatives and explain coverage limits. It should not fit numerical confidence, invent benchmark identity or infer a causal/legal verdict from co-movement. Release severity and external notification decisions remain deterministic and gated; price+volume alone never becomes global CRITICAL.

Before scientific performance claims, acquire rights-cleared contemporaneous BIST, US and crypto data with independently defined attention labels; freeze universe/calendars/feed/adjustment policy; develop settings chronologically and preserve an untouched final holdout. Report event-level matching, false alerts/100 asset-days, delay from availability, abstention/coverage and episode duplicate burden. Include no-event sessions, correlated market moves, beta/volatility drift, illiquid/zero-MAD assets, splits, outages, feed switches, lost material updates and failed AI entailment. Do not optimize on the jury example or treat usefulness feedback as correctness.

No source entitlement, organizer ruling, external integration, paid service, application build, migration, deployment or full four-market MVP delivery is provided by this lab.
