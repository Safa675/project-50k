# Project 50K v0.5 — Research synthesis

**Date:** 2026-10-02. **Delivery:** engine-method research, reproducible offline experiments and proposed brand/design directions. This package does not deliver an application, trained predictor, calibrated detector, live on-chain integration or production interface.

The research supports a product that explains an observed unusual development with dated evidence and explicit limits. It supplies concrete reasons to separate statistical rarity, financial importance, source support, user relevance and notification eligibility. It also rejects several tempting interpretations: fund investor counts are not money, transfers are not sales, many citations are not truth, and impressive retrospective scores are not timely detection.

Confirmed owner decisions and audited specifications/contracts remain authoritative; v0.5 is the current continuation package and adds clearly labeled research proposals. The completed v0.4 audit and owner-decision amendment remain inherited foundations; received originals and archived drafts remain historical evidence. This work extends that handoff without rewriting its history or repeating the audit. All **284 requirement IDs** and **28 anomaly definitions** are preserved; product implementation statuses remain **NOT_IMPLEMENTED**.

## What was tested

| Lab | Executed scope | Evidence type |
|---|---|---|
| [Market statistics](../research/engine_lab/MARKET_STATISTICS.md) | 12 fixed seeds; 322,560 unique synthetic volume evaluation bars; 24,000 multiplicity batches | Matched seeded simulations and constructed counterexamples |
| [Fund accounting](../research/engine_lab/FUND_ENGINE.md) | 49 named scenarios; 768 finite accounting combinations; 48 uncertainty corners | Exact-ledger arithmetic, accounting identities and nonidentifiability examples |
| [Temporal/on-chain](../research/engine_lab/TEMPORAL_CHAIN_ENGINE.md) | 29 checks; 100 seeded input permutations | Local revision, snapshot, finality and dependency-policy fixtures |
| [Evidence investigation](../research/engine_lab/EVIDENCE_INVESTIGATION.md) | 32 authored policy cases; five simulated budget assertions | Structured claim-policy conformance and adversarial examples |
| [Evaluation metrics](../research/engine_lab/EVALUATION_METRICS.md) | 32 random streams; 96 paired stream/interval-length scores | Retrospective scoring counterexample |
| [Color/design](../research/brand_lab/DESIGN_EXPLORATION.md) | 138 applicable listed color pairs across three palettes; 12 conditional exemptions | Opaque-sRGB contrast calculations |

Scripts are in `experiments/`; raw results and source-review depth are retained beside the corresponding reports. These counts describe different units and must not be pooled into a scientific sample size. No real market dataset, model evaluation, RPC experiment, customer study or rendered product test was performed.

## Main findings

**Market context helps only under its assumptions.** On the constructed equity seasonality, matching the prior session slot reduced false flags from 135.28 to 12.47 **per 100 asset-days**. That is a count, potentially greater than 100 because days contain multiple bars, not a probability. The flat control showed no clear benefit from season matching. A prior OLS market relation helped under stable beta and failed under beta drift. Preserve raw movement beside contextual residuals; a market-wide shock can still matter.

Valid tail probabilities are prerequisites for multiple-testing claims. Applying Gaussian probabilities to unit-variance heavy-tailed noise produced about 81.13% BH and 69.88% BY simulated batch FDR. Correction cannot repair a wrong null model. These are toy batch quantities, not real financial false-discovery guarantees. Median/MAD and session matching remain inspectable starting hypotheses; current thresholds are unvalidated. Known-event oracle grouping is not an implemented episode detector, and blind cooldown can suppress a separate material event.

**Fund endpoint residuals do not generally identify cash.** For compatible net assets and raw NAV, `A1 − A0 × P1/P0` equals end-period NAV times the change in units. Identical endpoints nevertheless admit cash 100 or 120; zero residual can coexist with cash −20. Reinvested distributions, splits, mergers, transaction timing and scope mismatch change the interpretation. The same investor-count decrease permits negative, zero or positive cash, while allocation changes can arise without trades and unchanged allocations can conceal round trips. Keep dated count/composition facts separate from outflow or selling narratives. Propagated input bounds are sensitivity intervals, not statistical confidence intervals.

**Historical knowledge needs immutable eligible versions.** The guarded synthetic snapshot was invariant in 100/100 permutations; naive last-arrival processing restored an older revision in 65/100. Actually-ingested replay and source-available reconstruction answer different questions. Later corrections, archives and finalization cannot silently enter an earlier decision. Frozen config now drives scoring, and exact binding plus admitted-state checks reject invalidated evidence. These checks demonstrate local policy behavior, not consensus verification, archive authenticity, database concurrency or a durable outbox. A token account is not a person; confirmed is not finalized; a transfer alone does not establish a sale.

**Evidence support and world truth remain separate.** The strongest typed policy matches 32/32 authored cases and emits no fixture-labelled unsupported structured claim. It still emits the deliberately false E06 assertion supported by two agreeing origins, even when its heuristic evidence score is 100. Its seven emitted claims and 24 insufficient outcomes expose the coverage tradeoff. Correct arithmetic must bind operand meaning, units, scope and contradictions. Per-premise lineage, dependencies and closed rendering prevent specific constructed failures. They do not extract or validate arbitrary Turkish prose, authenticate documents or identify causation. The five budget checks use invented reservations, not measured latency, tokens, provider bills or affordability.

**Evaluation can manufacture impressive scores.** Uninformative random flags scored about 0.956 retrospective point-adjusted F1 on long labelled intervals, while raw F1 was about 0.00497. Only one of 128 interval starts received a flag within ten points. Adjustment deliberately uses completed future-labelled intervals; longer intervals also change prevalence. Report actual first alerts, misses, false-alert burden and the intended point/event target. Do not backdate detection from later event stories.

## Proposed engine structure

[ENGINE_SYSTEM_DESIGN.md](../research/engine_lab/ENGINE_SYSTEM_DESIGN.md) proposes six conceptual modules within **one Python codebase/API and worker**, with shared records and PostgreSQL jobs/outbox. It does not propose six deployed services.

| Module | Responsibility |
|---|---|
| Capability and knowledge time | Admit correctly scoped, licensed, dated observations and revisions |
| Market unusualness | Preserve raw movement, comparable volume and prior market context |
| Fund accounting/disclosure | Produce explicitly named residual estimates and dated official facts |
| On-chain observation | Preserve network/event identity, raw units, canonicality and finality limits |
| Evidence investigation | Bind atomic claims, calculations, lineage, contradictions and limitations |
| Publication/attention/cost | Apply exact revisions, relevance, consent, notification and reservation policy |

[HYPOTHESES.json](../research/engine_lab/HYPOTHESES.json) records **23 dispositions: 10 KEEP variants, 10 REJECT and three DEFER**. KEEP remains conditional or proposed where stated; REJECT targets disproven interpretations; DEFER postpones unsupported methods or claims. None changes the owner's required experience or marks a requirement implemented.

## Proposed identity and design

[Naming and logo exploration](../research/brand_lab/NAMING_AND_LOGO.md) recommends **İzvanta / Izvanta** as a creative lead. Project 50K remains the codename until selection. Public screening retrieved no clear exact commercial match within its scope; trademark, similar-name, domain and handle availability remain uncleared. The generated inspection-frame logo is a raster concept needing designer refinement, vector masters and similarity review.

The recommended **Mineral / Ink** direction separates action color, market direction, importance, heuristic evidence strength and source freshness. All 138 listed applicable opaque color pairs meet their selected thresholds. This does not establish rendered contrast, Turkish glyph behavior, focus geometry, chart distinction, full WCAG conformance, Impeccable review or designer acceptance. Name, logo, palette and copy remain proposals.

## Binding boundaries and next evidence

The selected demonstration still covers **BIST, Turkish funds, crypto and US equities with meaningful on-chain experience**. BIST/fund first is a sequence, not an approved reduced final target. Exact networks/providers require capability evidence. No existing service accounts are available. **TRY 5,000 is the cumulative project ceiling**, excluding only development Claude/Codex subscriptions; runtime calls, data, hosting, domain and email remain inside it. No operating lifetime, affordability or spending permission is established.

Owner-authorized preparation does not supply organizer clearance. **G01 remains open for competition use of prepared materials**; the original no-prior-work condition remains preserved. This uncertainty does not halt authorized research.

[PEER_REVIEW.md](../research/engine_lab/PEER_REVIEW.md) records resolved defects, final artifact consistency and verification depth. All six frozen labs reproduced successfully in the aggregate execution recorded at 20:59:48 UTC in [RESEARCH_EXECUTION.json](RESEARCH_EXECUTION.json): five outputs were byte-identical; evidence matched after excluding only generation time and local wall time. This verifies fixture reproducibility, not product accuracy. A separate v0.5 package rerun passed 43 package checks, 88 reference methods and 31 contract scenarios. These remain offline specification/reference checks, not product acceptance.

Next evidence should establish provider rights and point-in-time coverage, independent labels, prior-only selection and untouched evaluation periods, real source/chain behavior, Turkish claim comprehension, durable concurrent revisions/delivery and measured cumulative costs. Synthetic findings guide those tasks; they do not replace them or authorize deployment, spending, contact or real-data publication.

## Additional weakness/risk review — 3 October 2026

The current v0.5 handoff now includes [RISK_REVIEW.md](RISK_REVIEW.md), five specialist reviews, 24 consolidated ordinal risk entries, an independently reviewed arithmetic scenario extension and retained pre-update history. Research priority is usable/entitled data and bounded cost, observed user advantage and actual required paths/failure behavior. No existing lab result, owner scope, production contract/configuration or product implementation status changes. This extension is risk research, not measured vulnerability, customer demand, actual prices or empirical financial performance.

## Additional problem solution and market research 3 October 2026

[PROBLEM_MARKET_RESEARCH.md](PROBLEM_MARKET_RESEARCH.md) separates real events/information seeking from unvalidated recurring user pain and paid demand. Five specialist evidence reports retain official investor cohorts, the full 2025 KAP publication table, historical US/crypto measurements, existing alternatives and three selected official episodes. All28 catalog frequencies remain unknown. The follow-up protocol seeks correct task advantage, ordinary-use recurrence and later payment evidence; none was executed. Current agent entry points/specification addenda use this evidence without changing requirements, scientific/risk results, owner scope or budget. See MARKET_EXECUTION.json/MARKET_DIFF.json for actual artifact checks and preserved history.
