# Delivery and operations risks

**Reviewed:** 2026-10-02. **Scope:** the selected BIST, Turkish investment funds, crypto and US equity demonstration, including meaningful on-chain experience. Eight project-specific risks; no delivery-time estimate or reduced-scope acceptance is inferred.

The principal delivery risk is an unprovisioned dependency tree around a demanding target, rather than a missing statistical technique. The package contains specifications, contracts, reference helpers and offline research. It contains no delivered application, entitled provider connection, authenticated deployment, production worker or actual email delivery [D02, D03, D05]. A passing local harness cannot close those gaps. The failure modes below are engineering inferences to test, not failures observed in a deployed application.

Keep the existing one-Python-codebase/PostgreSQL-worker design. These findings do not justify Redis, additional microservices or changing the owner's four-market target. G01 requires an organizer ruling before **competition use** of prepared materials; it does not stop the currently authorized preparation [D05, D06]. Other rights, account, privacy and real-send gates apply at their relevant external action or release stage.

## Eight risks and concrete acceptance probes

### DR01 — Four-market and network delivery depends on several unresolved prerequisites

**Known gap.** No service accounts exist. Data entitlements, real dated fund fields, US feed scope and exact initial chain networks remain open. EVM plus Solana is a proposal, not a committed capability. All required paths share identity, auth, source/evidence and UI work, while their cadence and finality differ [D01–D06, D08].

**Inferred failure.** Success on one price feed can conceal an unusable fund or chain path. A generic polling/window abstraction can mislabel dated NAV as intraday data, treat closed sessions as outages, or publish chain evidence before its chosen finality rule. Integration dependencies can compound even if each module looks small.

**Acceptance probe (planned).** Run one four-path fixture walkthrough through the actual ingestion-to-event-to-chat UI: an equity session closure and calendar transition, next-day fund NAV, continuous crypto bars and a chain observation that is later reorganized. Inject a missing provider capability into each path in turn. Assert preserved effective/available times, explicit unavailable states and no fabricated replacement values or premature finalized fact. Separately capture sanitized entitled-provider samples before claiming real support; fixtures alone do not pass that gate.

**Response.** Maintain a dependency/admission record per required path: provider, rights, identity/unit, calendar/cadence, time fields, history and failure state. Implement shared plumbing once, then prove each actual path. Narrow active universes when necessary without treating an absent required market as accepted completion.

### DR02 — A broad discovery catalog can accidentally become an unbounded active workload

**Known gap.** The catalog/actively-monitored distinction is mandatory. TRY 5,000 is cumulative project spend, not a monthly allowance; no operating period, allocation or affordability has been verified. Event explanations should be shared and browser refreshes should read cached application data [D01, D04, D06, D08].

**Inferred failure.** Watchlists, global awareness and per-user chat can silently multiply ingestion, explanation and notification jobs. A catalog-sized or user-sized fanout can consume the cap even though a small static demo is inexpensive. Free quotas or development subscriptions do not establish runtime capacity.

**Acceptance probe (planned).** Using free local provider/model stubs with recorded call counters, hold the admitted active asset set constant while multiplying catalog entries, watchers and browser refreshes. Assert provider ingestion and shared event-explanation calls do not multiply per watcher/refresh; notification intents do grow only for eligible recipients. Then request an asset outside the active set under exhausted reservations: require an explicit admission/coverage result, no unreserved call and no implied monitoring. Reconcile a simulated timed-out billable request as uncertain cost rather than automatically refunding its reservation.

**Response.** Make active-set admission, job fanout and remaining cumulative budget observable. Define bounded chat and investigation policies before load tests; validate actual prices and entitlements before spending. Do not promise how long TRY 5,000 will last.

### DR03 — The shared worker can keep running while starving important work

**Known gap.** One durable worker handles ingestion, detection, investigation, publication, notifications, digests and maintenance. Leases, bounded claims and retry limits are specified, not implemented or load-tested. The proposed 45-second chat deadline is unvalidated and is not an ingestion/notification service guarantee [D01, D03, D04].

**Inferred failure.** Slow provider/model calls, permanently retrying jobs or recipient fanout can monopolize the worker. A healthy process and correctly expiring leases do not establish fair service; a late owner can also attempt completion after its lease has been reassigned.

**Acceptance probe (planned).** Stall one external stub until its configured deadline while enqueueing cheap ingestion, a correction and bounded notification batches. Add a poison job that keeps failing. Observe queue age by type, not just total throughput. Kill a leased worker, allow another claimant to take over, then resume the original worker. Require that the stale owner cannot commit; the poison job reaches its terminal retry state; and other types advance within a **predeclared test service bound**. Choose that bound before the run rather than inventing a product SLA afterward.

**Response.** Use bounded claims, explicit timeout/cancellation, retry/backoff and fair scheduling within the existing worker. Measure whether that is sufficient before proposing another execution topology. Keep external calls outside database locks as specified.

### DR04 — Durable jobs alone do not prove alerts survive races and crashes

**Known gap.** Transactional event/outbox publication, unique notification keys, lease ownership and send-time eligibility are specified. Backend delivery integration is pending; reference helpers only evaluate policy. Universal exactly-once email is expressly not promised [D01–D03, D07, D08].

**Inferred failure.** A crash between event publication and intent insertion can lose an alert if implementation splits the transaction. A provider acceptance followed by a crash can duplicate a retry. Concurrent publication, unsubscribe or invalidation can release a stale queued message. Restore/replay can resurrect previously resolved work if ledger reconciliation is missing.

**Acceptance probe (planned).** Exercise a small event with two recipients and duplicate producers. Inject crashes before commit, after commit and after a fake provider records acceptance but before the application records it. Concurrently unsubscribe one recipient and invalidate the queued revision. Inspect persisted event, intent, attempts and fake-provider ledger after recovery: no eligible logical intent disappears, one logical intent per eligible key exists, stale consent/revision sends are suppressed, and uncertain acceptance is reconciled using the declared provider-idempotency policy. Repeat from a saved database snapshot. This is a transactional/delivery test, not another call to the boolean helper.

**Response.** Implement the atomic boundary and persisted attempt reconciliation before enabling external send. Keep real delivery disabled until its separate authorization and sender/consent gates are satisfied.

### DR05 — Missing history can make a required market look functional while most detectors cannot operate

**Known gap.** Real licensed history is absent. Fund NAV/AUM/investor/allocation capabilities must be demonstrated separately. Market methods require prior comparable completed observations; a new asset, feed switch or unknown adjustment can invalidate that history. Official disclosures and finalized transfers can still be factual without an outlier baseline [D02, D05, D08].

**Inferred failure.** A superficially successful current-data endpoint can leave nearly all active assets cold. Artificial backfill, current constituents or mixed-feed windows can appear to solve the problem while introducing leakage. Conversely, withholding every event until a volume window fills can unnecessarily hide useful official facts.

**Acceptance probe (planned).** Start the actual app with an empty history store and a provider that supplies current observations but denies historical fields. Add an asset mid-session; then switch its feed while other assets retain valid history. Verify persisted detector eligibility and visible reasons, with no invented candles/zeros, reused incompatible window or historical-live claim. Supply an independently eligible official disclosure and require the factual path to work while its statistical classification remains unavailable. Retry when legitimate history arrives and verify that the original actual-system record is preserved.

**Response.** Treat warm-up and unavailable history as product states. Record coverage per detector/asset and source semantics; admit numerical methods only when their inputs are actually comparable. Do not replace unavailable mandatory market experience with fabricated statistical coverage.

### DR06 — Monitoring may report green while evidence silently stops updating

**Known gap.** Freshness, queue age, disabled detectors, unknown confidence and separate liveness/readiness are specified. No implemented monitoring or runbook exercise exists. Unknown must not be rendered as normal or safe [D02–D04].

**Inferred failure.** HTTP 200 with repeated old bars, unchanged input watermarks, a disabled detector or a stuck outbox can evade process-uptime checks. Applying one age threshold to continuous crypto, session-based equities and published-cadence funds can also create false outage alarms or conceal genuine stale data.

**Acceptance probe (planned).** Keep API and worker health responses successful while a stub repeats old data; separately stop watermark advancement, exhaust investigation budget and strand one notification. Run the same setup across a scheduled market closure and a fund publication delay. Require that source-specific freshness/readiness, detector status and outbox age show the fault without calling expected closure an outage. Verify the public screen and admin screen describe the same missing coverage and existing evidence remains readable. Exercise ingestion, generation and sending pauses independently.

**Response.** Instrument observed progress and source-specific expected cadence, not only requests and exceptions. Give each silent-failure state an owner/runbook and a visible user limitation. A high average heuristic confidence is not a health or quality metric.

### DR07 — Corrections can be correct in storage and still mislead users

**Known gap.** Immutable revisions, exact-revision approval and publish/update/invalidate policies are proposed. Actual feed, cache, conversation, in-app notification and email behavior is unimplemented; a revision is not automatically a new external send [D01–D03, D08].

**Inferred failure.** An old strong title can survive in a cached timeline, saved chat or inbox after its evidence is withdrawn. Replacing it silently erases what the user previously saw. Sending every revision can create alert floods; silently discarding corrections can leave material misinformation unaddressed.

**Acceptance probe (planned).** Publish revision 1, open it in a session and save a dependent conversation/in-app alert. Correct or invalidate it while that session is paused and its email intent is queued. On resume and direct old-link access, require an explicit current status and traceable old revision; suppress the stale queued send. Verify a material correction follows the declared attention/consent policy rather than a generic resend. A frozen replay must retain its historical context while distinguishing the current live correction.

**Response.** Define correction visibility and material-change semantics across all surfaces before polishing the happy path. Preserve the ledger and dated claims; recheck current status at live read/send boundaries without rewriting frozen historical bundles.

### DR08 — Scientific gates may produce safe abstentions but insufficient useful coverage or unacceptable delay

**Known gap.** Thresholds, labels, provider-quality gates and natural-Turkish semantic extraction are not empirically validated. Offline laboratories use synthetic data or hand-supplied evidence atoms; no real financial, LLM or prospective performance has been measured. Tool/time/source limits are proposals [D02, D04, D08].

**Inferred failure.** Independent rights, time, provenance, baseline and claim gates can compound into low publication coverage. Investigation may finish after a useful attention window, or a refusal-heavy chat may fail the meaningful AI experience. Relaxing gates to improve demo throughput risks unsupported causes or false certainty.

**Acceptance probe (planned).** Freeze a small independent reviewer-authored set containing a supported official fact without market history, an unexplained valid outlier, a contradictory source, missing provenance and an unavailable explanation. Include both ordinary and unusual cases; record coverage and denominators, abstention reasons, claim correctness, end-to-end delay, calls and cost. Withhold a source and exhaust the tool deadline. Require timely preserved factual context plus named uncertainty rather than an invented cause. Run real provider/LLM evaluation only when separately authorized; the fixture exercise cannot establish semantic accuracy or financial performance.

**Response.** Separate fact publication from causal explanation and numerical classification. Share eligible explanations, bound investigation, and display partial results honestly. Measure usefulness and delay along with errors; defer unsupported methods rather than deleting a required market or presenting a weaker integrity policy as scientific validation.

## Reading and verification boundary

All sources are current project documents read in full; paths, section anchors and hashes are recorded in `delivery_risk_sources.json`. No external lookup, service/account action, paid call, deployment, production failure injection or application test was performed for this review. The acceptance probes above are **planned**, not passed. Existing reference/lab executions supply bounded local evidence only. No requirement, release gate or product capability is marked complete here.

| Source | Project record |
|---|---|
| D01 | docs/14_Architecture_and_ADRs.md |
| D02 | docs/20_Test_and_Validation_Strategy.md |
| D03 | docs/21_Implementation_Backlog_and_Traceability.md |
| D04 | docs/22_Deployment_Operations_and_Costs.md |
| D05 | docs/25_Release_Gates_and_Open_Decisions.md |
| D06 | research/USER_DECISIONS_2026-10-02.md |
| D07 | AGENTS.md |
| D08 | research/engine_lab/ENGINE_SYSTEM_DESIGN.md |
| D09 | reports/OPEN_DECISIONS.md |
