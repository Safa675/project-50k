# Scientific risks and misleading certainty

Review date: 2026-10-02. Scope: final market, fund, evidence and evaluation laboratories. This review changes no code, results, thresholds, market scope or release decision. BIST, funds, crypto and US remain in scope; the existing TRY 5,000 cumulative ceiling and spending authorization rules remain unchanged.

The laboratories demonstrate arithmetic, policy conformance and constructed failure mechanisms. They do not establish deployment accuracy, market base rates, useful-warning performance, source truth, causality, calibration or losses avoided. Their explicit caveats are appropriate; the risk arises if later product language or release decisions drop those caveats. Severity below concerns the consequence of doing so. Evidence confidence concerns the stated limitation, not the probability or frequency of a future failure. These are not product alert severities or calibrated probabilities.

Read the four complete narratives and selected machine-readable results. File snapshots and primary-source retrieval/depth records are in `scientific_risk_sources.json`. No new experiment was run and no lab artifact was changed.

## Seven key risks

### SR-01 — Passing authored synthetic cases becomes a deployment validation claim

**Severity: HIGH. Evidence confidence: HIGH for the scope limitation; deployment error rate UNKNOWN.**

**Observed:** `EVIDENCE_INVESTIGATION.md:33` and `:35` describe 32 hand-authored packets and the same author's validator/oracle. `:61` records 32/32 policy matches. `FUND_ENGINE.md:18` reports 49 named cases, 768 bounded combinations and 48 corner checks. `MARKET_STATISTICS.md:3` uses zero real observations and `:17` describes fixed generators/seeds. `EVALUATION_METRICS.md:11` fixes a random flag process. Many generated values or seeds do not create independent real-world evidence; a perfect count can concern a deliberately narrow rule.

**Inferred future failure:** production prose, omitted premises, unreliable metadata, market regimes and source conventions differ from the authored world. Repeatedly adding a fixture after discovering a bug improves regression coverage while also adapting the suite to the implementation. That suite cannot become an untouched performance holdout.

**Cheap falsification:** preserve the current labs as development/regression evidence. Before viewing system outputs, a separate reviewer should freeze a legally usable offline set of unfamiliar Turkish documents and dated market/fund records, with independently defined claims, relevant-event labels and ambiguous/unknown labels. Blind the reviewer to scores and gates. One counterexample can falsify an asserted universal gate guarantee; it cannot estimate deployment frequency. Keep a separate final set unavailable to prompt/threshold authors. If rights or labels are missing, report an evaluation gap rather than assigning accuracy.

### SR-02 — Fixed thresholds appear reliable despite base rates, drift and dependence

**Severity: HIGH. Evidence confidence: HIGH for observed constructed counterexamples and probability accounting; real-market magnitude UNKNOWN.**

**Observed:** `MARKET_STATISTICS.md:44`–`:57` gives substantial uninjected-bar burden even after seasonal matching; the flat control shows no clear matching advantage. `:63`–`:69` shows fitted OLS losing its constructed advantage under beta drift. `:82` shows invalid Gaussian tails defeating both BH and BY. `:86` distinguishes a per-batch result from repeated-monitoring burden. `:108` uses three exactly dependent price-family representations; their flag count is not three independent confirmations.

**Inferred future failure:** rare actionable positives can make a tolerable-looking per-test false-positive rate produce mostly unhelpful alerts. Serial overlap, shared market shocks, news syndication and data-provider dependence inflate the effective alert family. A quality score or multiplicity correction cannot repair invalid null probabilities or drift. There is no established operational prevalence here. For a defined binary target, precision depends on prevalence π through `TPR·π / (TPR·π + FPR·(1−π))`; the labs do not identify these deployment quantities. Primary imbalanced-classifier discussion is SR-S01; its application here is an inference, not a financial performance result.

**Cheap falsification:** freeze thresholds and collect contiguous eligible periods, ordinary periods and known regime/source breaks, retaining all unflagged observations. Compare burden and event recall by market, liquidity, session/feed, market-wide episode and time block. Group uncertainty by asset/episode/source origin rather than counting overlapping bars as independent. Evaluate threshold sensitivity on development data only, and preserve subsequent untouched periods. If low burden fails or drift reverses the benefit, retain the contextual statistic with explicit limits instead of asserting reliability or calibrated FDR.

### SR-03 — Concordance, citations and calculation correctness become truth or causality

**Severity: HIGH. Evidence confidence: HIGH for non-implication; frequency of false concordance UNKNOWN.**

**Observed:** `EVIDENCE_INVESTIGATION.md:67` records E06: agreeing distinct origins support a hidden world-false assertion, while manually assigned maximum rubric components produce score 100. E03 permits a ratio but rejects its cause; E17 permits attribution, not the attributed cause. E05/E28/E31 expose syndication, irrelevant citation padding and unsupported ancestry. The lab supplies atomic assertions, authenticity and lineage; it does not discover them from documents (`:33`, `:100`). RAG's source-truth caveat and Pearl's association/causation distinction were inspected directly (SR-S05/SR-S06).

**Inferred future failure:** two outlets can repeat a common mistaken premise despite different URLs or apparent origin keys. An authentic official statement can correctly record what its issuer said without establishing the issuer's explanation. A causal narrative may conceal an unsupported premise between correctly calculated numbers. Same-model or cross-model agreement remains a fallible diagnostic. No causal identification design or independently measured semantic reviewer exists here.

**Cheap falsification:** assemble offline pairs of original/copy, circular quotations, corrections, partial support, attributed explanations and equally plausible alternative events. Label each atomic premise and its source support independently; keep world truth unknown where it cannot be resolved. Compare plain observations, attribution and causal wording separately. Require exact source-version/span/calculation bindings and measured omission/false-acceptance counts. Any universal “verified truth” or “cause identified” claim fails upon a supported-false or unsupported-cause example. Keep score descriptive and calibrated probability null.

### SR-04 — Safety gates hide false negatives and lost coverage

**Severity: HIGH. Evidence confidence: HIGH for observed omission mechanisms; deployment recall and subgroup disparities UNKNOWN.**

**Observed:** `EVIDENCE_INVESTIGATION.md:61` records 24 insufficient answers, one partial and one review-required answer. These are not full answers; the abstentions matched the authored policy oracles and may be policy-correct. The deliberately authored fixture distribution does not estimate production coverage or accuracy. E14 internally accepts a ratio but publishes none. `MARKET_STATISTICS.md:110` gives two distinct events within cooldown and loses one. `:101`–`:104` describes zero-MAD abstention and future-contaminated history hiding a constructed event. Fictional evidence-budget reservations constrain work, not the adequacy of what was retrieved. The reject-option literature describes a risk/coverage tradeoff, under conditions that do not certify this product (SR-S02).

**Inferred future failure:** sparse assets, delayed official records, rare languages/entities, metadata gaps or exhausted search budgets can receive fewer useful results. Looking only at emitted claims or accepted answers can conceal missing events, missing explanations and excessive “review required” states. A silent or absent result is not a safe state or a causal negative.

**Cheap falsification:** independently label a sample of *both* emitted and unflagged/abstained opportunities from frozen contiguous data. Include incomplete sources and budget-exhausted packets. Audit every required claim/event as emitted, omitted, rejected, unavailable or unknown. Report end-to-end recall, required-information coverage, full/partial/abstained/review coverage and false alerts using the original opportunity denominator. Measure actual first alert and preserve misses. If suppression removes a distinct supported event or eliminates most useful coverage, revise the policy on development data and recheck untouched data; do not count suppression as correctness.

### SR-05 — Selection, revision leakage and survivor-only data inflate results

**Severity: HIGH. Evidence confidence: HIGH for observed deliberate leakage; survivor bias is an unmeasured future risk.**

**Observed:** `MARKET_STATISTICS.md:104` contrasts causal past history with deliberately forbidden current/future values. `EVALUATION_METRICS.md:13` uses completed labeled intervals to adjust predictions retrospectively. `FUND_ENGINE.md:77` excludes asynchronously published/revised fields at earlier cutoffs. No current lab demonstrates a licensed historical universe containing delisted/merged/closed funds and failed or missing providers. No survivor-bias magnitude was measured. A failed external RFS retrieval supports no bibliographic or scientific claim in this review.

**Inferred future failure:** selecting today's surviving/liquid assets, repaired price histories, current fund share classes or already-public incident stories can exclude the difficult cases. Current classifications, revised statements and threshold/prompt tuning on the same holdout introduce later knowledge. Filtering to assets with enough history can create a second selection layer. Source-score labels, model-generated judgments and jury examples cannot be their own independent ground truth.

**Cheap falsification:** freeze the contemporaneous universe and membership rules before scoring; retain inactive, merged, halted, missing and ineligible records with explicit reasons. Replay immutable available-at snapshots, revisions and class/action chronology. Split by time and source/episode cluster, and document exclusions and every tuning attempt. Compare eligible and excluded groups; do not silently drop failed records. A replay decision changed solely by unavailable future information falsifies point-in-time integrity. If historical membership is unavailable, state that survivor bias cannot be assessed. Reserve an untouched final holdout before adapting settings.

### SR-06 — Fund residuals and counts are presented as identified cash or asset sales

**Severity: HIGH. Evidence confidence: HIGH for algebraic non-identification; prevalence and size of real errors UNKNOWN.**

**Observed:** `FUND_ENGINE.md:49`–`:55` distinguishes the endpoint residual from transaction cash. Identical AUM/NAV/units endpoints permit cash 100 or 120 (`:64`); residual zero permits net cash −20 (`:65`). Count 2→1 permits cash −100/0/+150 (`:73`). Allocation distance can arise with no trades, while round trips leave endpoints unchanged (`:74`–`:76`). Distribution, split, merger, share-class and settlement alternatives are explicit. Deterministic uncertainty bounds (`:94`) are not empirical confidence intervals or a solution to missing timing. Morningstar's historical methodology describes estimates and action/reinvestment conventions; it supplies no Turkish defaults (SR-S04).

**Inferred future failure:** a precise number can be displayed as redemptions, capital flight, selling, or current exposure despite unresolved action/price/timing conventions. More endpoint samples do not by themselves recover unobserved within-period transaction cash. The residual's sign need not identify cash's sign. Reported cash and settlement cash also require distinct target definitions.

**Cheap falsification:** retain the paired synthetic ledgers as a permanent identifiability challenge. Where lawful offline records actually disclose transactions, select a fund/share-class period with unit changes, transaction NAVs, distributions/actions and recognition/settlement dates. Reconcile a separately authored ledger against the endpoint estimate, carrying unknown fields as unknown. If the ledger cannot be obtained, exact-cash validation is unavailable: publish only a conditional endpoint estimate, count change or dated allocation observation, with no cash/asset-sale identification claim. Validate provider precision bounds independently before arithmetic intervals are presented.

### SR-07 — Statistical rarity or retrospective event hits become useful timely warnings

**Severity: HIGH for loss-prevention/detection claims; MEDIUM for an explicitly exploratory timeline. Evidence confidence: HIGH for target mismatch; actual usefulness UNKNOWN.**

**Observed:** `EVALUATION_METRICS.md:29` gives random flags adjusted F1 0.956449 for long intervals while first-ten-point recall is 0.007812. The target changes with duration and positive prevalence. `MARKET_STATISTICS.md:67` recognizes that a market-only flag can be a correct unusual observation; calling it an asset-specific problem changes the assertion. Shared-context grouping counts use generator-supplied identities, not validated event clustering. An authenticated official access fact can matter without any market anomaly baseline (evidence E09).

**Inferred future failure:** unusual activity may be irrelevant; ordinary-looking official access changes may be useful. “Ever touched an interval,” localized detection, timely notice, supported explanation, user attention and prevented losses are different outcomes. A helpful-looking retrospective story or high adjusted score cannot establish the last four. Kim et al.'s point-adjustment warning supports the metric concern, not a product-effectiveness estimate (SR-S03).

**Cheap falsification:** predefine event-level relevance and permissible matching/delay windows before outputs are viewed. Score actual immutable decisions and first notice; retain no-hit events and false/duplicate notices. Ask a separate blinded reviewer to assess whether the available-at packet justified attention, and assess usefulness separately from factual/causal correctness. Compare with a simple official-notice/context baseline and a no-anomaly stream. Review disagreement and unknowns explicitly. This is an offline evaluation proposal, not authorization to contact users or publish claims of avoided losses.

## Low-cost evaluation order and stopping rule

Start with local rights-cleared exports, official documents and paired falsification packets. Freeze target definitions, temporal admission, exclusions, baselines, metric denominators and label guidance before running. Preserve distinct development and untouched final sets; a newly discovered attack joins development, not the final holdout. Labels require independent judgment and uncertainty states, not agreement with the engine. Use natural-prevalence contiguous data to estimate burden; enrich rare adversarial mechanisms only as a separately reported stress set.

No fixed sample count here is asserted to guarantee adequacy. Plan collection from the target prevalence, intended operational tolerance, independent cluster count, label uncertainty and the available budget. Report the collected counts and uncertainty; if too little evidence exists, leave the performance claim unresolved. A counterexample can cheaply reject an overly strong assumption. Absence of one in a small set cannot establish a deployment guarantee. No new paid data, model calls, accounts or infrastructure are authorized by this review.

The defensible next claim is that specific deterministic safeguards and identifiability limits have been explored offline. Broad four-market performance, calibrated confidence, reliable causal explanation and user benefit remain separate evaluation tasks.
