# Independent methodological peer review

**Reviewed:** 2026-10-02. **Scope:** read-only review of the offline research extension, with this report as the sole peer-authored file. This is a review of constructed experiments and their interpretation, not certification of source truth, a live financial backtest, production readiness or competition eligibility.

The reviewed work supports retaining several inspectable accounting, time, evidence and evaluation controls. It does not establish real-market detector accuracy, calibrated probabilities, meaningful live on-chain delivery, affordable operation or a completed product. The reports preserve this distinction. No unresolved methodological blocker was found in the six final frozen lab artifacts. The evidence lane's final result/narrative consistency was verified after its last case was frozen.

## Review coverage and verification depth

Paths below are relative to `Project_50K_v0.5_research`.

| Lane | Files inspected | Independent peer checks |
|---|---|---|
| Market | `experiments/market_statistics.py`; `research/engine_lab/MARKET_STATISTICS.md`, `market_results.json`, `market_results_reproduction.json`, `market_run.log`, `market_sources.json` | Read implementation and final interpretation; checked current script/result provenance and exact equality of the two saved result files. The peer did not independently execute the full market simulation. |
| Fund | `experiments/fund_accounting.py`; `research/engine_lab/FUND_ENGINE.md`, `fund_results.json`, `fund_sources.json` | Regenerated every saved case group and bounded formula group in memory under precision 50/ROUND_HALF_EVEN; all equal the saved groups. Current experiment checksum matches the result. |
| Temporal/on-chain | `experiments/temporal_chain.py`; `research/engine_lab/TEMPORAL_CHAIN_ENGINE.md`, `temporal_chain_results.json`, `temporal_chain_sources.json` | Independently reproduced the original two defects before correction. Read corrected gates and counterexamples, then reran `run()` in memory; full saved JSON equals regenerated output. |
| Evidence | `experiments/evidence_reasoning.py`; `research/engine_lab/EVIDENCE_INVESTIGATION.md`, `evidence_results.json`, `evidence_sources.json` | Read typed policies, fixtures and final report; independently reran all 32 policy cases and five budget assertions. JSON-normalized results equal the saved output except generation time and local wall time; current script checksum matches. |
| Evaluation metrics | `experiments/evaluation_bias.py`; `research/engine_lab/EVALUATION_METRICS.md`, `evaluation_results.json`, `evaluation_sources.json` | Read generator and scoring separation; independently reran in memory, exactly matching saved JSON. Verified paired false-positive counts and early-hit denominators. |
| Color/design | `experiments/color_contrast.py`; `research/brand_lab/color_candidates.json`, `color_contrast_results.json`, `DESIGN_EXPLORATION.md` | Read opaque-sRGB arithmetic and threshold decisions, scenario classifications and report limits; candidate input checksum matches the saved result. No browser/rendered-interface test was performed by this peer. |
| Integration/authority | `research/engine_lab/ENGINE_SYSTEM_DESIGN.md`; `research/USER_DECISIONS_2026-10-02.md`, `USER_RESEARCH_REQUEST_2026-10-02.md`; `requirements_registry.json`, `contracts/traceability.json`, `config/anomaly_catalog.json` | Reviewed scope and research authority. Compared the three product registries with v0.4: contents unchanged, 284 requirements remain NOT_IMPLEMENTED in both requirement/traceability files, and all 28 anomaly entries are unchanged. |

Source manifests were inspected for provenance and declared reading depth; this peer review does not repeat a full literature or provider-rights audit. No external call, account provision, paid runtime request or remote action was executed by the peer's verification scripts. The in-memory checks deliberately did not overwrite agent-owned results.

## Methodological assessment

### Market statistics

The main comparisons use the same generated observations for competing methods. Volume profiles include both constructed seasonality and a flat negative control. History uses previous completed sessions; evaluation injections are not removed from later eligible history by consulting the oracle. Prior OLS uses a separate earlier training window, and the beta-shift case demonstrates where that residual method fails. These are useful conditional controls, not evidence that real feeds have the specified process or that the provisional thresholds generalize.

The headline volume burden is **false flags per 100 asset-days**, a count that can exceed 100 because each asset-day contains multiple bars. It is not a probability or percentage of days with any alert. Null-bar flag rates and injected-event recall have different denominators and are separately labeled. The 322,560 unique synthetic volume evaluation bars are not independent real-market observations.

The Gaussian null produces valid toy tail probabilities; the heavy-tail case deliberately applies invalid Gaussian probabilities to unit-variance Student-t3 noise. The normalization in the generator is correct. BH and BY are implemented as step-up procedures with the appropriate harmonic correction for BY. Batch FDR is the mean of `V/max(R,1)` across simulated batches. Under the all-null case it equals the chance of any rejection in a batch; it is neither a pooled false-count fraction nor a financial monitoring guarantee. The 24,000 multiplicity batches are explicitly synthetic.

Episode grouping by known generator identity is an oracle comparison, not an implemented episode detector. The separate-event cooldown counterexample prevents interpreting reduced notification counts as uniformly better behavior. The deliberately leaky current/future-contaminated baseline is labeled as a forbidden comparison. Monte Carlo intervals describe seed variability conditional on the simulator; they do not establish real-market error rates and may extend outside natural rate bounds.

### Fund accounting

The exact Fraction transaction ledger is structurally separate from the Decimal endpoint residual calculation. The identity check remains an algebraic/accounting check; observing it on a finite grid does not validate provider fields. More informative are the nonidentifiability counterexamples: identical NAV/AUM endpoints admit cash 100 or 120, zero residual can coexist with cash −20, and reinvestment/splits/noncash transfers alter the raw residual without corresponding subscription cash.

The final result contains **49 named synthetic scenarios**, **768 finite ledger/formula combinations** and **48 bounded-input uncertainty corners**. These are different counts and must not be combined into an empirical sample size or represented as 49 independent accuracy trials. The largest recorded Decimal-versus-rational discrepancy is `3.33333E-48`, below the stated `1E-40` numerical tolerance.

Investor count and allocation examples correctly separate count from money and weight change from trading. Placeholder zero and observed zero now execute distinct guards. Source publication/receipt cutoff fixtures do not constitute a complete delivery gate. Endpoint metadata tests cover a narrow comparability subset; rights, real disclosure cadence, complete actions and source adapters remain unimplemented. Input-bound propagation assumes independently permissible positive bounds. Its interval is a sensitivity bound, not a statistical confidence interval or a measured source-error distribution.

### Temporal and on-chain records

All **29 synthetic checks** independently rerun and equal the saved result. Cutoff selection distinguishes what was actually ingested from source-available reconstruction. A late verified archive can enlarge a new reconstruction without proving live historical detection. The future-finalization case excludes the later FINALIZED revision from earlier knowledge.

Snapshot invariance in 100 permutations is conditional on the authored records, identities and monotonic revision assumption. A hash protects comparison of recorded content; it does not authenticate the source or prevent replacement of both payload and checksum. The bundle lacks a production executable/dependency manifest, rights context, consensus verification and historical universe membership.

The corrected local gate checks exact binding **and** a kind-specific admitted-state whitelist. RETRACTED, INVALIDATED, UNKNOWN and ORPHANED identical self-bindings are rejected even when the finality option is off. Frozen evidence with threshold 3 versus 7 now actually controls scoring: ratio 6 changes from CANDIDATE to NOT_FLAGGED. This is a meaningful config counterexample rather than merely a changed hash.

Chain states, source availability and token-account data are fixture inputs. They do not establish consensus, RPC coverage, transfer parsing, ownership, actual finalized observations or an atomic durable outbox. The report correctly keeps raw transfer, token account, authority and beneficial owner separate, and explicitly states that this lab alone cannot satisfy the owner's meaningful on-chain demonstration.

### Evidence investigation

Fixtures and golden policy outcomes are authored separately from the validator, which does not receive the oracle. They share an author and a finite typed assertion language, so this is policy conformance rather than blinded evaluation of extraction or reasoning on unseen documents. Positive controls retain valid raw facts, an official access fact without a price baseline, attributed causal statements and supported associations. Abstention is not the only passing behavior.

The frozen strongest policy matches **32/32 authored policy oracles**, emits seven structured claims and no fixture-labelled unsupported structured claim, but still emits the one source-supported/world-false E06 claim. Its 24 insufficient, one partial and one review-required outcome remain in the denominator. These counts do not measure a hallucination rate or unseen-answer precision.

The important E06 counterexample remains accepted: distinct source-supported origins can agree on a world-false assertion, even with heuristic score 100. The report does not call that score a probability. The closed renderer controls its own structured output; it does not prove that a Turkish LLM response has no omitted or extra material claim. Typed atoms, authentication, validity windows and lineage are supplied, not discovered.

New guards bind corroboration to each premise, reject an ancestor that did not assert the copied premise, bind calculation predicates and ordered operands, and reject current contradictions in calculation operands. They are worthwhile narrow counterexamples, not general natural-language entailment, authenticity or causal-identification solutions.

The five budget assertions are arithmetic reservations against invented calls/tokens/durations. They do not measure actual model usage, timeout enforcement, provider prices, transactional races or TRY affordability. Six combined stage calls are an additional lab proposal; the existing tool-call cap does not automatically cap model requests.

### Evaluation-metric counterexample

The 32 random prediction streams are independent of labels and shared within each seed across the three interval lengths. The **96 seed/length scores are paired**, not 96 independent streams. Retrospective point adjustment deliberately uses future completed interval labels; raw prediction generation does not. False-positive counts are identical within each raw/adjusted pair.

Longer intervals change both the chance of any hit and positive prevalence, and both are disclosed. The long-interval adjusted F1 of about 0.956 is therefore a counterexample to the interpretation of that score as timely detection, not a trained detector's result. One early hit among 128 interval starts is preserved for every duration. Misses remain in recall; reported conditional delay applies only to hit intervals. The analytical Bernoulli probabilities are independent checks on the generator design, not fitted targets. Normal Monte Carlo intervals are acknowledged as rough simulator summaries, including their poor boundary behavior with rare hits.

### Color and design

The opaque sRGB formula uses the 0.04045 conversion breakpoint and correct luminance weights; threshold decisions use unrounded ratios. The results cover **138 listed applicable pairings** plus **12 conditional exemptions**, with five arithmetic and five invalid-input checks. Exemptions depend on the documented decorative/inactive usage being true in a later interface.

This verifies listed colors under opaque solid backgrounds. Actual font rendering, compositing, dark mode, adjacent charts, focus geometry, keyboard behavior, full WCAG compliance, Impeccable review and designer acceptance remain outside the test. Proposed palette/name/logo directions do not become owner-approved product branding through this review.

## Concrete issue and resolution register

| ID | Finding | Resolution/evidence | Status |
|---|---|---|---|
| PR-01 | Local delivery originally admitted some identical RETRACTED/INVALIDATED/UNKNOWN evidence when finality was disabled. Binding equality alone is insufficient. | Kind-specific admitted-state whitelist; independent self-binding cases C24–C27 plus kind mismatch C29. Peer rerun confirms rejection. | RESOLVED in lab; durable production enforcement remains untested. |
| PR-02 | Frozen threshold was stored and hashed but toy scoring originally read the global default. A different frozen policy could produce the old outcome. | Scoring now reads verified bundle config; C23 ratio 6 at thresholds 3/7 gives different outcomes. Peer rerun matches saved result. | RESOLVED in lab; executable/environment binding remains deferred. |
| PR-03 | Investor placeholder/true-zero outcomes were initially illustrative result dictionaries rather than executed distinctions; some allocation examples needed arithmetic assertions. | Executable investor helper and assertions added; narrow metadata and allocation/cash-path guards added. All fund case groups independently regenerate identically. | RESOLVED; no broad source adapter claim. |
| PR-04 | Evidence guards and fixtures changed during peer review while saved outputs/narrative briefly lagged at 27/31 cases. | Final 32-case freeze verified: script checksum matches; JSON-normalized independent rerun matches saved output excluding only generation time/local wall time; final narrative counts agree. | RESOLVED before packaging. |

## Scope, open boundaries and packaging interpretation

The owner-selected target remains BIST, Turkish funds, crypto and US equities with meaningful on-chain experience. A BIST/fund implementation sequence, small active universe or deferred statistical technique is not approval to remove a required market. Exact initial networks/providers remain decisions requiring capability evidence. All 284 requirements and 28 anomaly definitions remain unchanged and unimplemented.

The TRY 5,000 ceiling is cumulative and excludes only development Claude/Codex subscriptions. No account availability, vendor allocation, operating lifetime or affordability is proven here. The research authorization permits these offline preparations; it does not authorize spending, provider provisioning, deployment, real-data publication or contact. The no-prior-work organizer condition and G01 ruling remain unresolved for competition use. That uncertainty does not halt authorized preparation or turn this report into organizer clearance.

Before stronger empirical claims, require rights-cleared point-in-time data and independent labels, frozen prior-only training/selection and untouched later evaluation, ordinary periods and missingness, alert-level coverage and user comprehension, prospective timing, dependency-aware uncertainty and measured costs. Before runtime claims, require real source/chain capability checks, semantic extraction evaluation, durable database/outbox integration and concurrency tests. These are explicit next boundaries, not hidden failures of the current offline task.

## Final evidence freeze verification

Final evidence result generation time is `2026-10-02T20:51:40.907849+00:00`; experiment SHA-256 is `90540d4ab2c2f2cedd91948eb0e3ff5fc0a298a6c6f3d8aae924b728e482974e`. The independent peer rerun JSON-normalized tuples/lists and excluded only `generated_at_utc` and `wall_seconds_local`. All remaining fields equal the saved JSON: 32 policy-oracle matches, all five budget assertions passing, zero external calls and zero paid runtime cost. Current report counts and its E32 contradiction case agree with this frozen result. Earlier 27/31-case snapshots were in-progress artifacts, not the delivered claim.
