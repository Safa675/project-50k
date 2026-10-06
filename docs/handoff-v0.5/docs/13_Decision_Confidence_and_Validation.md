# Project 50K — Decision Engine, Evidence Strength & Calibration

**Version:** 0.4 audit revision · **Prepared:** 2026-10-02
**Status:** implementation specification / not a claim of deployed functionality.

## 1. Separate five dimensions
1. Observation unusualness: baseline deviation, not harm.
2. Event severity: potential operational/informational significance, not predicted loss.
3. Evidence strength: support for the displayed classification.
4. Source/coverage health: what was and was not observed.
5. User relevance: followed asset or exceptional global event.

The user asked for confidence. We meet the underlying need with a visible, inspectable score; we do not manufacture a probability. `Kanıt gücü: 80/100` has tooltip `Kaynakların güncelliği ve doğrulanabilirliğini gösterir; olayın doğru olma veya fiyatın yön değiştirme olasılığı değildir.` Calibration research motivates this distinction [R07,R08].

## 2. Pipeline and publication gates
Normalize and validate → compute structured signals → open investigation candidate → bounded LLM extraction/retrieval → validate claims and numeric derivations → deterministic policy publication → notification eligibility.

The LLM can uncover context that reclassifies an unexplained movement as a disclosed corporate event. It cannot fabricate prices, upgrade a statistical outlier to a legal finding, invent citations, set its own numeric confidence, edit thresholds or directly email users.

Hard gates before public event publication: supported identity; authorized processing/display; adequate timestamps; complete bar or actually published NAV; minimum baseline for numerical claims; no known adjustment conflict; no unresolved source contradiction that invalidates the title. A verified official notice can publish without a market-price baseline because its event type is different.

## 3. Proposed evidence-strength calculation
For a publishable event, four components in [0,1]:
- completeness Q: validated required evidence fields present / required fields;
- freshness F: schedule-aware, evidence-level validity, aggregated conservatively;
- source integrity I: traceable original source, entity match, successful extraction and revision tracking;
- corroboration C: independent supporting evidence families, not copied article count.

`score = ROUND_HALF_UP(100 * (0.35*Q + 0.25*F + 0.25*I + 0.15*C))` at the integer display boundary, using Decimal values constructed from decimal strings. Thus 0.5 becomes 1, consistently in the reference helper and package validator. Reject nonfinite or out-of-range components and nonboolean policy gates.

These weights are product heuristics, version `evidence-strength-v1`, not science-derived probabilities. Fatal data failure prevents publication even if an arithmetic score looks high. Magnitude is excluded from confidence; it affects severity. For a verified original official notice, corroboration is not a requirement for truth: the component may be 1 for direct primary evidence with verified identity. That special case must be encoded by event type, not selected by the LLM.

Initial display bands: <50 limited, 50–74 moderate, >=75 strong. Quantized score can be omitted when the data is too incomplete to grade. Store components, scoring version and reasons. `calibrated_probability` stays null until there is a separately reviewed calibration artifact.

## 4. Severity policy
**MEDIUM:** one meaningful supported change or contextual update.
**HIGH:** a qualified multi-signal numerical event, or material official/issuer development affecting the asset.
**CRITICAL:** a supported material access, custody or exceptional market-wide disruption event, with exact scope and admin approval for global circulation. In MVP, price + volume alone is never CRITICAL. This is a conservative product policy, not a financial loss model.

Regulatory records retain: authority, subject entity, decision/publication/effective dates, exact action, source and subsequent status. A trading measure is not proof of a manipulation conviction. A fund liquidation decision must not be paraphrased as all invested money being lost.

## 5. Event state machine
`CANDIDATE → INVESTIGATING → REVIEW_REQUIRED or PUBLISHED`.
`PUBLISHED → UPDATED / EXPIRED / INVALIDATED`.
Store immutable revisions and the current pointer. An LLM timeout permits a deterministic metric-only event if all other gates pass. A contradictory source cannot be hidden to preserve the original title. Reorg/source correction invalidates dependent observations; pending notifications are canceled and already-delivered material errors receive a correction record.

Dedup uses asset, event family, observation window and origin namespace. Market price/volume signals within the same completed bar merge. A new source may update context, not create five alerts. Material-change notifications are separately typed `UPDATE` or `CORRECTION`, never a reset dedup key on every summary rewrite.

## 6. Replay and labeling
A server-registered immutable replay_bundle_id binds the evidence/revision manifest, cutoff, rights record and config hash. A frozen replay snapshot has eligible evidence `available_at <= cutoff`, source-publication cutoff, known historical revision, and config hash. It cannot fetch current web pages. Backfilled historical bars require recorded knowledge assumptions; unknown availability cannot be relabeled known at the event time.

Human labels: `actionable_attention`, `not_actionable`, `uncertain`, plus event-type correctness and citation support. No manipulation ground truth unless established by appropriate authoritative material with its own date. Later official findings can label outcomes but cannot enter earlier features.

## 7. Evaluation plan and proposed gates
Chronological fit/validation/holdout; purge overlapping event windows. Include sector-wide moves, macro days, no-event days, small/illiquid assets, data outages, corporate actions and delayed NAV. No random shuffled split.

Report event-level precision/recall with a stated matching window, false alerts per 100 asset-days, median/p95 delay after **available** data, fraction abstained, review disagreement and citation completeness. Normal point-wise accuracy is not useful in a sparse-event setting. No point-adjusted scoring that marks an entire episode correct from one late hit [R06].

Calibration later needs an explicitly defined binary target, adequately sized held-out labels across time/asset class, reliability diagrams, Brier score and uncertainty intervals. Success on a tiny synthetic set supports arithmetic correctness only. Do not publish a precision or calibration percentage before completing this study.

## 8. MVP truthfulness
Offline reference tests in this package test arithmetic, temporal filters and policy guards. They do not prove a real market anomaly was predicted, that a user would avoid losses, or that the scoring formula is calibrated. The demo must state this limitation.

## 9. Reference arithmetic and policy boundary
Fund-flow arithmetic uses a local Decimal context with precision 50 and ROUND_HALF_EVEN for intermediate operations; no implicit currency quantization is applied. Evidence-score integer display uses ROUND_HALF_UP as above. Derived float metrics must be finite, and thresholds must be finite with valid sign/range. Invalid inputs fail closed or abstain rather than imply normality.

Replay filtering is only a row-level timestamp/origin eligibility helper. It does not assemble immutable revision snapshots, validate corporate-action history, select historical universe membership or verify config hashes. These remain implementation and dataset acceptance gates. External-email eligibility requires actual booleans and eligible, published real-origin evidence; this helper does not implement consent persistence, provider delivery or durable outbox concurrency.

## v0.5 research continuation
Read research/engine_lab/ENGINE_SYSTEM_DESIGN.md and the four engine labs plus EVALUATION_METRICS.md. Source-supported facts can still be world-false; metadata strength is not truth probability. Separate source-available reconstruction from actual-ingested replay, and bind scoring to frozen config. Synthetic simulations do not calibrate financial p-values or validate the heuristic score. Current contracts/reference code are unchanged.

## 2026-10-03 risk review

Evaluate prevalence, emitted and unflagged opportunities, coverage/abstention, source truth and usefulness separately; see scientific risks and arithmetic sensitivity. The authored negative-fixture ratio is not actual coverage. Current synthesis: reports/RISK_REVIEW.md; register: research/risk_review/RISK_REGISTER.json.
