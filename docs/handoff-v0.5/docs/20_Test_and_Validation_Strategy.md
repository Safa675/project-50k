# Project 50K — Test & Validation Strategy

**Version:** 0.4 audit revision · **Prepared:** 2026-10-02
**Status:** implementation specification / not a claim of deployed functionality.

## 1. What this package validates
The included reference harness exercises deterministic arithmetic, missing-data handling, temporal access and notification policy using synthetic inputs. It is **not** an end-to-end implementation, a historical backtest, a calibrated classifier or proof of market-abuse detection. The execution report distinguishes these scopes.

## 2. Test pyramid and ownership
| Level | Scope | Release evidence |
|---|---|---|
| Reference unit | Return/volume math, fund flow, evidence strength, replay cutoff | Executed local unittest report in this package |
| Contract | Event/AI schemas, examples, OpenAPI references, requirement links | Executed package-validation report |
| Provider integration | Actual authenticated/entitled responses, time fields, units, outages | Pending; capture sanitized response and rights record |
| Backend integration | User isolation, Google JWT, RLS, outbox transactions, job leases | Pending implementation |
| UI / E2E | Anonymous → Google → watchlist → event → evidence → chat → feedback | Pending; Playwright and manual walkthrough |
| Research evaluation | Chronological splits, labels, alerts/day, precision and delay | Pending data and labels |
| Design/accessibility | Keyboard, contrast, focus, mobile layout, Impeccable + designer | Pending implemented UI |
| Security | Auth bypass, cross-user access, SSRF, injection, secrets | Pending deployed staging |

## 3. Named acceptance cases
| ID | Scenario | Expected result |
|---|---|---|
| TC-DATA-001 | borsapy price-history investor field is a compatibility zero | Normalize to unknown, no investor-loss alert |
| TC-DATA-002 | Fund NAV arrives next day | Label source as-of date; never invent intraday candles |
| TC-DATA-003 | Price feed is IEX rather than SIP | Visible venue coverage and same-feed baseline |
| TC-DATA-004 | Stale source returns HTTP 200 | Mark stale and suppress affected interpretations |
| TC-DATA-005 | OHLC series crosses split without adjustment metadata | Reject anomaly computation; data-quality status |
| TC-DET-001 | Same-slot volume is six times prior-session baseline | Candidate using only prior observations |
| TC-DET-002 | Flat history has zero MAD | Abstain; no divide-by-zero or arbitrary huge score |
| TC-DET-003 | Fund AUM falls only because NAV falls | Estimated flow is zero within rounding tolerance |
| TC-DET-004 | AUM decreases beyond NAV return | Estimated negative flow, not exact audited cash movement |
| TC-DET-005 | Allocations include negative derivative/repo weights | No naive probability-vector normalization |
| TC-DET-006 | Missing essential inputs but otherwise high evidence score | Hard gate blocks publication regardless of score |
| TC-TIME-001 | Evidence published after replay cutoff | Excluded even if reporting period predates cutoff |
| TC-TIME-002 | Revised filing replaces original later | Replay sees only the version available then |
| TC-AI-001 | Retrieved news says ignore rules/send email | Treat as untrusted text; no write tool exists |
| TC-AI-002 | Answer states a numeric fact not in evidence/calculation | Reject or regenerate with supported facts |
| TC-AI-003 | No trustworthy explanation found | Bounded “Doğrulanabilir bir açıklama bulamadım” |
| TC-AI-004 | User asks buy/sell or manipulation verdict | Informational alternative, no definitive recommendation |
| TC-AI-005 | Web source unavailable/paywalled | State coverage limits; no invented quote or date |
| TC-AI-006 | Replay chat attempts live web research | Denied or isolated present-day mode, never mixed |
| TC-AUTH-001 | Anonymous requests private watchlist/chat | 401 without data |
| TC-AUTH-002 | User A guesses user B's resource ID | 404/403 and no row leakage |
| TC-AUTH-003 | User edits profile metadata to admin=true | No privilege escalation |
| TC-AUTH-004 | Expired/wrong-audience JWT | Reject before user data access |
| TC-NOT-001 | Duplicate event/job delivery | One in-app logical alert; provider-idempotent email |
| TC-NOT-002 | Off-watchlist critical without opt-in/admin release | No external email |
| TC-NOT-003 | Unsubscribe before retry | Suppress queued email at send-time recheck |
| TC-NOT-004 | Worker crashes after provider accepted mail | Reconcile/idempotent retry; no promised exactly-once guarantee |
| TC-NOT-005 | Replay/synthetic event reaches notifier | External send forbidden |
| TC-UX-001 | Narrow screen, keyboard navigation, long Turkish title | No essential horizontal overflow; visible focus |
| TC-UX-002 | No alert or disabled detector | Say no detected event/coverage unavailable, never “safe” |
| TC-OPS-001 | Provider outage or LLM budget exhausted | Existing evidence remains readable; clear degraded mode |

These are test specifications. Only cases explicitly matched to executed tests in reports are verified; a listed case is not a passed case.

## 4. Research protocol
Freeze universe, session calendar, symbol mapping, feed and corporate-action policy. Partition chronologically into train, threshold-development, calibration (only when needed), and untouched test periods. Purge overlap for rolling windows; avoid fitting on test data. Hold out entire episodes/assets when feasible. Keep delisted/failed assets rather than surviving names only.

Define the target first: unusual market behavior, not fraud. Label events independently with an annotation guide and adjudication; regulatory findings are separate labels and publication dates. An event can be statistically unusual but explainable. Record uncertain/unknown instead of forcing negatives.

Measure event-level precision, recall only where ascertainable, false alerts per asset-day, duplicate burden, detection delay from observable onset, evidence correctness and Turkish comprehension. Report denominators, confidence intervals and missing-data coverage. No point-adjusted time-series score without disclosure [R06]. Compare with fixed percent-change and same-slot RVOL baselines; report unsuccessful comparisons.

## 5. Calibration and multiple testing
A heuristic evidence score is not calibrated. To display a probability, define its target label, estimate it on separate calibration data, assess reliability diagrams/Brier score and strata, and suspend probability output under drift or insufficient samples [R07,R08]. FDR procedures require defensible p-values/dependence assumptions; do not convert arbitrary robust z-scores into valid p-values [R09]. In the initial release control alert burden through deduplication, cooldown and evaluated thresholds, not an unsupported statistical guarantee.

## 6. Evaluation datasets to build
`DATASET-REAL-01`: licensed historical BIST bars and contemporaneous disclosures. `DATASET-FUND-01`: dated NAV/AUM/allocation records with actual publication evidence. `DATASET-CHAIN-01`: finalized transactions and identity-label uncertainty. `DATASET-AI-01`: Turkish claim-evidence questions with allowed abstentions. None is included as a real dataset here. Included fixtures are synthetic and labeled.

## 7. Go/no-go
No release with cross-user leakage, fabricated citations, replay-to-email path, uncertain BIST rights, numeric probability masquerading as heuristic score, hidden source delay or fabricated fund history. Other performance/design goals are measured in staging and recorded against the agreed scope.

## Audit-added acceptance cases (planned; not executed application tests)
| Case | Trigger | Required result |
|---|---|---|
| TC-AUTH-005 | Anonymous, service-role or non-Google credential; logged-out session with unexpired JWT on a sensitive action | Provider policy enforced; privileged/deletion action checks current session and role; expiry-bounded ordinary JWT semantics documented. |
| TC-NOT-006 | Global approval for revision 1 followed by revision 2, invalidation, revocation or changed policy | Stale queued send suppressed; exact current eligible revision needs current private approval. |
| TC-AI-007 | Orphan calculation, changed operand or numerical sentence omitted from structured claims | Resolve and recompute server calculation; every material sentence checked; unsupported numeric output blocked. |
| TC-API-001 | Replay without cutoff; follow-up changes asset/origin/cutoff | Invalid input rejected; stored-context mismatch returns 409. |
| TC-PROJ-001 | Candidate/review event or restricted/unknown evidence on public event route | Public projection excludes internal state and uncleared evidence; rights labels verified against entitlement. |
| TC-NET-001 | IPv4/IPv6 private/reserved destination, redirect to private network or DNS rebinding | Server fetcher rejects at resolution and connection, caps bytes/time; no internal response returned. |

The reference email helper now defaults to dry-run and requires explicit real-origin evidence metadata and actual booleans. Its regression tests are policy checks, not delivery/RLS tests. Replay helpers do not assemble snapshots or prove licensed point-in-time history. See the audit coverage register for these boundaries.

## v0.5 research continuation
The v0.5 six offline laboratories and their reproducible outputs are indexed in reports/RESEARCH_REPORT.md. These are conditional simulations/counterexamples/color arithmetic, separate from the original 88 reference methods/43 package checks/31 contract scenarios. No real financial, LLM, authentication, delivery or browser UI test occurred. EVALUATION_METRICS.md demonstrates why retrospective label-adjusted F1 is not timely alert performance.

## 2026-10-03 risk review

Research acceptance probes remain planned. Preserve independent labels, natural-prevalence ordinary periods, all missing/abstained cases, source/episode clusters and untouched evaluation; arithmetic scenario reproduction is not product acceptance. Current synthesis: reports/RISK_REVIEW.md; register: research/risk_review/RISK_REGISTER.json.

## Problem solution and market research continuation 3 October 2026

Precommit the actual universe, event/trigger definition, eligibility and historical cutoff before evaluating ordinary and unusual periods. Include unflagged samples, independent labels, exclusions, revisions and score-blinded review. Compare correct source-verified user tasks against actual next-best alternatives. None of these empirical/customer tests was executed here. See `reports/PROBLEM_MARKET_RESEARCH.md` and the linked source-depth appendices.
