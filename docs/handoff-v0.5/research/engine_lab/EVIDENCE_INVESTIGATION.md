# Evidence investigation: claim support and bounded review

Date: 2026-10-02. Status: **OFFLINE SYNTHETIC POLICY LAB — NOT A PRODUCT RUNTIME OR SCIENTIFIC VALIDATION**.

The strongest simulated policy emits none of the fixture claims labelled unsupported by the authored policy oracle, but it still emits a deliberately world-false claim supported by two agreeing sources. Source support, source truth, causal identification, answer coverage, and calibrated correctness probability must remain separate properties. Source IDs and correct arithmetic alone are insufficient even in this small, fully structured setting.

## Scope and authority

Read `AGENTS.md`, `START_HERE.md`, current decisions and release gates, `research/USER_DECISIONS_2026-10-02.md`, product/design documents, audit/correction/coverage/open-decision reports, `docs/13_Decision_Confidence_and_Validation.md`, `docs/17_AI_Tools_and_Runtime_Prompts.md`, and the existing AI-answer/evidence/calculation contracts. Requirement anchors are FR-055/057/058/061/067/068/096/097 and NFR-026/027/028/029/031/081.

Only `experiments/evidence_reasoning.py` and this lane's three research artifacts were created or changed. No shared documentation, configuration, schema, application runtime, paid model/provider call, deployment, account, or database was changed. The experiment uses Python's standard library, hand-authored synthetic assertions, integer time ticks, and a closed English diagnostic renderer. Product user text remains Turkish; this diagnostic renderer is not a proposed user interface.

The lab's internal claim roles (`FACT`, `DERIVED`, `ASSOCIATION`, `ANOMALY`, `CAUSAL`, `ABSENCE`) are a policy taxonomy, **not** replacements for the shipped contract's `DIRECT`/`DERIVED`/`INTERPRETATION` support kinds. Semantic role and support mechanism are different axes. The existing evidence score remains a heuristic and calibrated probability remains null.

## Primary-source review and its limits

All sources were retrieved on 2026-10-02. Exact URLs, source reference IDs, metadata, reviewed text locations, and retrieval failures are in `evidence_sources.json`. Selected sections were inspected; no entire-paper reading or research replication is claimed. The root agent must reopen a source before citing its web reference in a final answer.

| Source | Reviewed depth | Relevant finding and transfer limit |
|---|---|---|
| EV-S01, [Lewis et al., RAG](https://arxiv.org/abs/2005.11401) | Metadata/abstract; selected discussion and Broader Impact in the PDF | Retrieval can expose external evidence, but the paper explicitly recognizes that external sources can be wrong or biased. Its NLP comparisons supply no project correctness guarantee. |
| EV-S02, [Gao et al., ALCE](https://aclanthology.org/2023.emnlp-main.398/) | Metadata/abstract; citation-quality definitions, shortcut cases, partial-support limitation | Joint citation support, irrelevant citations, factual correctness, and useful coverage need separate measures. Its NLI-based evaluation and partial-support caveat motivate adjudication; benchmark rates do not transfer. |
| EV-S03, [Manakul et al., SelfCheckGPT](https://aclanthology.org/2023.emnlp-main.557/) | Metadata/abstract; sample-count discussion and Limitations | The evaluated material was generated biography text. Mixed factual/nonfactual sentences and computational cost limit direct transfer to Turkish market explanations. |
| EV-S04, [Zhang et al., SAC3](https://aclanthology.org/2023.findings-emnlp.1032/) | Metadata and abstract only | The abstract identifies self-consistency blind spots and motivates cross-checking. It does not establish project performance, affordable call counts, or independent model errors. |
| EV-S05, [Guo et al., calibration](https://proceedings.mlr.press/v70/guo17a.html) | Metadata and abstract only | Probability calibration is empirical correspondence with correctness. Classification calibration methods do not validate the project's weighted evidence rubric. |
| EV-S06, [El-Yaniv and Wiener, selective classification](https://jmlr.org/papers/v11/el-yaniv10a.html) | Metadata and abstract only | Rejection trades coverage for accuracy. Its noise-free theory supplies no bound for this noisy evidence workflow. |
| EV-S07, [Pearl, causal inference](https://ftp.cs.ucla.edu/pub/stat_ser/r350.pdf) | Author-hosted header/abstract and selected introduction/association distinction | Causal queries require explicit assumptions beyond observed association. No identification design or market causal effect was evaluated here. Publisher retrieval exposed an iframe; the UCLA PDF supplied the inspected text. |

The architecture decisions below are project engineering inferences informed by these readings and the counterexamples. They are not methods empirically validated for Project 50K by those papers.

## Experiment design

The program compares three deliberately incomplete policies on the same 32 packets. Each packet contains typed assertions, citations, source lineage, availability/validity, calculations, material claim dependencies, and optionally extra answer prose. These are supplied by the fixture author; no extraction, source authentication, entity resolution, lineage discovery, NLI, or real document analysis was performed.

The golden answer status, accepted IDs, unsupported IDs, and the hidden E06 world-truth label are authored separately from `validate()`. The validator receives only the packet and profile, never the oracle. The same author wrote fixtures and validator; this is not an independent or blinded scientific evaluation. Matching the golden oracle establishes conformance to these declared cases, not accuracy on unseen prose or markets.

| Policy | Gates actually simulated |
|---|---|
| `EXISTENCE_ARITHMETIC` | Referenced source IDs exist; referenced operands resolve; Decimal RATIO arithmetic recomputes. This is an illustrative weak policy, not a measurement of the shipped product. |
| `TYPED_SCOPE` | Above plus current eligibility/authentication flags; exact typed premise support; asset, unit, and time scope; approved fact predicates and calculation metric/ordered operands; known current contradictions; no unsupported causal/global-absence promotion; a baseline-count gate for anomaly claims. |
| `GRAPH_RENDER` | Above plus acyclic source ancestry with same-assertion support, eligible ancestors, per-premise distinct origin counts, acyclic claim dependencies and rejection propagation, and a closed renderer. Extra prose that differs from validated output quarantines the answer. |

The baseline threshold of 20 is a **fixture policy parameter**, not a scientifically justified minimum for any anomaly method. Exact typed equality is an intentionally narrow entailment surrogate. The lab has no natural-language paraphrase judgment. Origin keys represent asserted provenance components; they do not prove statistical independence, causal independence, or truthful reporting. Source ancestry checks availability/authentication and assertion support; current claim truth uses the current eligible record. Actual revision chains and historical source authenticity remain outside the lab.

## Results and reproduction

From the project root:

```bash
python experiments/evidence_reasoning.py --output research/engine_lab/evidence_results.json
```

The actual command exited 0 on Python 3.12.14 and generated the saved result at `2026-10-02T20:51:40.907849+00:00`. Script SHA-256: `90540d4ab2c2f2cedd91948eb0e3ff5fc0a298a6c6f3d8aae924b728e482974e`. Local experiment wall time was 0.005597 seconds; this is not model latency. The JSON records all packets/oracles/outcomes, budget reservations, and explicit limitations. Fixtures are deterministic and use no random seed. The script's actual external calls, paid runtime cost, and model invocations are zero; model latency and actual model token usage are null. Research browsing is separate from the script. Future reruns may change generation time and local wall time.

| Policy | Answered | Partial | Insufficient | Review required | Emitted claims | Unsupported fixture claims emitted | World-false but source-supported claims emitted |
|---|---:|---:|---:|---:|---:|---:|---:|
| `EXISTENCE_ARITHMETIC` | 29 | 0 | 3 | 0 | 32 | 24 | 1 |
| `TYPED_SCOPE` | 14 | 2 | 16 | 0 | 17 | 9 | 1 |
| `GRAPH_RENDER` | 6 | 1 | 24 | 1 | 7 | 0 | 1 |

The strongest policy matches **32/32 authored policy oracles**. These counts are not LLM hallucination rates, precision estimates, market validation, or confidence intervals. The 24 insufficient and one review-required outcomes reduce output coverage; they are not correct full answers. The unsupported count is restricted to the explicit typed claims labelled in these fixtures. E14's extra sentence is measured separately because it was deliberately omitted from the structured claim list.

Key observations:

- E03 recomputes the correct ratio and omits the unsupported causal explanation, producing `PARTIAL`. Correct numbers do not support their causal interpretation.
- E05 rejects two syndicated copies of one origin. E28 rejects an unrelated citation used to pad corroboration; E31 rejects an ancestor that never asserted the copied premise. Corroboration must bind to each premise.
- E06 deliberately assigns two distinct origin keys and agreeing assertions while the hidden world oracle marks the assertion false. All policies emit it. Assigning every heuristic component to 1 yields score 100 under the current weighted rubric; calibrated probability remains null. This is a logical counterexample, not an empirical score calibration test.
- E09 permits an authenticated, correctly scoped official access fact without price history. E23 rejects the promotion of a raw observation into an anomaly without an approved baseline. Different claim roles need different gates.
- E11 allows the current fact despite an expired old contradiction; E12 abstains on an unresolved current conflict. The lab assumes supplied validity windows are correct.
- E14 accepts the ratio internally but emits no answer when an extra causal sentence appears outside the validated renderer. This is `REVIEW_REQUIRED`, not a complete correct response.
- E17 permits the attributed fact that an issuer reports a cause; it does not establish that cause. E25 and E29 reject causal semantics laundered through a fact label or derived predicate.
- E18 and E30 demonstrate that arithmetic must bind units and operand meaning/order, not just numeric values. E20 demonstrates that a rejected material premise invalidates claims depending on it. E32 rejects a correct calculation whose input premise has an unresolved current contradiction.

## Architecture hypotheses

| Decision | Hypothesis | Basis and next implementable step |
|---|---|---|
| **KEEP, priority 1** | Server-owned claim-role and metric registries | Require a canonical subject, approved predicate, value/unit, effective interval, and explicit support bindings. A model's `FACT` label or an existing source ID cannot supply semantic authorization. |
| **KEEP, priority 1** | Calculation gates bind meaning as well as arithmetic | Recompute with the approved method version, ordered operand roles, input source versions/locators, units, time/asset scope, and declared rounding. Bind rendered values to that record. E18/E29/E30 are concrete blockers. |
| **KEEP, priority 1** | Validate every material output claim | Prefer a closed renderer for approved factual/calculated claims. If free prose is retained, all sentences need independent claim decomposition and review; the lab does not prove that review works. Extra unreviewed material must quarantine publication. |
| **KEEP, priority 1** | Per-premise provenance and dependency graphs | Collapse known syndicated origins, reject circular/unknown lineage when asserting corroboration, reject unsupported ancestry, and propagate rejected material dependencies. A URL count is insufficient. |
| **KEEP, priority 1** | Explicit temporal and contradiction policy | Use canonical identity and publication/availability/effective/revision times. Quarantine unresolved current contradictions; do not blindly compare an old superseded state with a current one. |
| **KEEP** | Bounded retrieval, extraction, and focused review | Search only for a specific missing premise or contradiction after an internal evidence packet exists. Reserve limits before work and retain budget exhaustion as an auditable abstention reason. |
| **KEEP** | Partial answers and abstention preserve the coverage denominator | Return supported observations with omitted claim/reason records when useful. Abstention describes an evidence or coverage limit; it does not mean no risk, no cause, or safety. Missing score remains absent, never 0. |
| **REJECT** | Existing IDs, correct arithmetic, many URLs, or reviewer agreement prove the answer | E02/E03/E05/E14/E28/E29/E30 and E06 give distinct counterexamples. These properties answer narrower questions. |
| **REJECT** | High evidence score overrides a failed gate or represents a probability | Invalid evidence stays invalid. The maximum-score E06 counterexample still passes a source-supported falsehood; the heuristic is descriptive. |
| **REJECT** | Temporal coincidence establishes cause, or a bounded search establishes global absence | E03/E15/E19 separate supported observations from unsupported explanations and unbounded negative assertions. |
| **REJECT as default** | Many sampling/review passes provide inexpensive validation | Repeated calls have no evaluated project benefit. The combined-call budget scenario blocks the second extra self-check. This does not reject all future sampling research. |
| **DEFER** | Learned extraction, NLI, or an LLM semantic reviewer can accept free prose | Needs Turkish claim-level human adjudication, mixed-fact/partial-support examples, contradiction and numeric-role attacks, reviewer false acceptance/rejection counts, and measured cost. Schema conformance alone cannot test it. |
| **DEFER** | Score-to-probability mapping or accepted-output risk guarantee | Needs a precisely defined correctness target, representative independent labels, held-out asset/time/source clusters, reliability evaluation, and coverage/risk reporting after the selection gates. No calibration fitting was run. |
| **DEFER** | Real provenance, authenticity, revision replay, and atomic budget enforcement work | Requires real immutable source snapshots, source-specific lineage checks, replay cases, transactional reservations and concurrency tests. The standalone lab is sequential local arithmetic only. |
| **DEFER** | Cross-model checking or broader retrieval improves this product within its budget | Requires actual approved-model experiments and latency/token/provider-price accounting. Different model names are not evidence of independent errors. |

For sources with unknown lineage, the conservative fixture policy abstains on a corroboration claim. A future narrower attributed observation could remain publishable with provenance uncertainty explicitly shown; this alternative is not implemented or evaluated here. Treat absence of discovered contradiction as “none in the bounded inspected packet,” not proof that no contradiction exists.

## Proposed records and enforcement boundary

Before adding product runtime, define a claim-support record with role, canonical asset/entity, approved predicate, value/unit/interval, source version/hash and exact locator/span, source-origin component, material dependencies, calculation-method version and operand bindings, verdict and exclusion reasons. Use separate states for source-supported, unsupported, contradicted, and unknown. “Source-supported” must not be named “world-verified.” Proposed records are research recommendations; shared contracts were not edited.

For text extraction, a reviewer should return the precise claim, cited span(s), whether each premise is fully/partially/unsupported, scope mismatch or contradiction, and the extraction/reviewer/model/prompt version. Deterministic code can verify identifiers, locators, source hashes, value bindings, operation/rounding, graph cycles, reservation arithmetic, and closed output templates. It cannot establish that extracted atoms faithfully represent a document, the document is authentic and true, two origin labels imply independent errors, an omitted natural-language premise was found, or a causal effect is identified. A model-generated verdict remains a measured, fallible inference.

No reviewer should manufacture probability from verbal confidence. A future causal claim would additionally require a declared target effect, an identification design and assumptions, confounder/alternative-event treatment, valid timing, uncertainty and sensitivity analysis. An official causal statement can instead be shown as attribution. The current lab supplies none of that causal evidence.

## Bounded-cost experiment

The lab reserves fictional work against 2 searches, 8 sources, 45,000 simulated milliseconds, 8,000 reserved tokens, and **6 combined stage calls**. Search/source/time numbers align with the current proposed envelope; token and combined-stage caps are additional lab proposals. In particular, the existing 6-tool-call limit does **not** automatically cap model requests. The simulation conservatively counts retrieval, draft, calculation, and review stages together; product accounting needs separate tool and model request caps. These reservations are not observed latency, tokenizer output, bills, or approved new limits.

| Scenario | Observed simulated reservation outcome |
|---|---|
| Internal retrieve → extract/draft → targeted search → calculate → material-claim review | Fits: 5 stages, 1 search, 6 sources, 3,400 reserved tokens, 13,120 simulated ms. |
| Same plan followed by up to 20 self-checks | First extra check is stage 6; the second is rejected before execution for exceeding the combined-call cap. |
| Three searches | Third search is rejected before execution. |
| Nine requested sources | First reservation is rejected before execution. |
| A 45,001 ms reserved operation | Rejected before execution. |

All five reservation assertions pass. The experiment tests no database transaction, race, cancellation, retry, actual wall-clock timeout, caching, idempotency, real provider rate limit, TRY/USD cost, or budget reconciliation. Actual deployment must reserve a conservative call/token/cost allowance atomically before external work, use an overall deadline, and reconcile measured usage without permitting an overrun. The existing TRY 5,000 cumulative ceiling remains authoritative; this research incurred no paid runtime expenditure and does not authorize it.

## Evaluation required before runtime claims

Build a frozen, legally usable Turkish evidence set with independently adjudicated atomic claims, source truth uncertainty, citations and revision times, mixed facts/causes, syndication, circular quotation, and negative-search traps. Separate extraction quality, premise support, calculation correctness, source truth, causal overclaim, contradiction handling, and answer coverage. Split by asset, time, and origin cluster to limit leakage from reused stories; reserve a final set before tuning thresholds or prompts. Reviewer outputs and source-score labels must not serve as their own ground truth.

Measure emitted supported/unsupported/unknown claims, citation relevance and partial/joint support, required facts omitted, accepted-answer error, abstention/review/partial/full-answer coverage, and the cost/deadline distribution. Keep the original requested-answer denominator: a system can reduce emitted errors by omitting everything while answering nothing. Report source-supported but world-false cases separately. Include both unavailable and absent heuristic scores; neither maps to zero.

Any calibration target must specify what “correct” means and where it applies. Fitting on all drafted claims cannot justify probabilities for the selected published subset without evaluating that subset's conditional behavior and coverage. A changed source pool, gate, time regime, or reviewer version can change the selection distribution. These are proposed validation procedures, not completed experiments or guaranteed bounds.

## Complete strongest-policy case ledger

Accepted IDs are internal gate decisions; E14 accepts a ratio but emits none. Full inputs and rejection reasons are in `evidence_results.json`.

| Case | Adversarial/positive fixture | Answer status | Accepted IDs |
|---|---|---|---|
| E01 | Supported raw price fact | ANSWERED | price |
| E02 | Existing source ID, unsupported numeric premise | INSUFFICIENT_EVIDENCE | none |
| E03 | Correct ratio, unsupported cause | PARTIAL | ratio |
| E04 | Incorrect computed ratio | INSUFFICIENT_EVIDENCE | none |
| E05 | Two syndication copies, one origin | INSUFFICIENT_EVIDENCE | none |
| E06 | Independent agreeing sources, hidden world-false assertion | ANSWERED | corroborated |
| E07 | Circular source citations | INSUFFICIENT_EVIDENCE | none |
| E08 | Claim dependency cycle | INSUFFICIENT_EVIDENCE | none |
| E09 | Official access fact, no market baseline | ANSWERED | official |
| E10 | Official citation for the wrong fund | INSUFFICIENT_EVIDENCE | none |
| E11 | Expired old contradiction | ANSWERED | official |
| E12 | Unresolved current contradiction | INSUFFICIENT_EVIDENCE | none |
| E13 | Publication unavailable at cutoff | INSUFFICIENT_EVIDENCE | none |
| E14 | Omitted causal sentence in extra prose | REVIEW_REQUIRED | ratio |
| E15 | Bounded search promoted to global absence | INSUFFICIENT_EVIDENCE | none |
| E16 | No usable evidence | INSUFFICIENT_EVIDENCE | none |
| E17 | Attributed causal statement as a factual report | ANSWERED | attribution |
| E18 | Correct arithmetic, mixed currencies | INSUFFICIENT_EVIDENCE | none |
| E19 | Aligned observations without causal promotion | ANSWERED | association |
| E20 | Supported child depends on rejected premise | INSUFFICIENT_EVIDENCE | none |
| E21 | Unknown source origin | INSUFFICIENT_EVIDENCE | none |
| E22 | Zero denominator | INSUFFICIENT_EVIDENCE | none |
| E23 | Anomaly label with no baseline | INSUFFICIENT_EVIDENCE | none |
| E24 | Unauthenticated official evidence | INSUFFICIENT_EVIDENCE | none |
| E25 | Causal proposition laundered as FACT | INSUFFICIENT_EVIDENCE | none |
| E26 | Eligible copy, unavailable original | INSUFFICIENT_EVIDENCE | none |
| E27 | Misaligned temporal association | INSUFFICIENT_EVIDENCE | none |
| E28 | Unrelated citation pads origin count | INSUFFICIENT_EVIDENCE | none |
| E29 | Correct ratio, causal result predicate | INSUFFICIENT_EVIDENCE | none |
| E30 | Correct arithmetic, reversed metric operands | INSUFFICIENT_EVIDENCE | none |
| E31 | Ancestor does not assert copied premise | INSUFFICIENT_EVIDENCE | none |
| E32 | Correct calculation, currently contradicted input | INSUFFICIENT_EVIDENCE | none |
