# Product, requirements, UX and backlog audit

Reviewed immutable baseline: `received/Project_50K_Work_Handoff_v1/baseline/Project_50K_v0.3`. No shared baseline or working-copy edits were made by this reviewer. Findings below are proposed documentary corrections for root integration. Severity describes preparation-package risk, not an observed production incident.

## Confirmed strengths

The current product narrative preserves mandatory BIST, Turkish funds as a differentiator, public discovery, one watchlist without cost-basis entry, Google-only personal accounts, a responsive web MVP with mobile-first vision, Turkish terminology, in-app/email, off-watchlist critical awareness, on-chain product intent, and designer/Impeccable review. AI is meaningfully involved in extraction, classification, evidence investigation and contextual chat; it has not been reduced to decorative summaries. Heuristic evidence strength, severity and incomplete-data states are separated. The documentation repeatedly says the application, live integrations and empirical performance have not been delivered. Those are strengths, not defects to manufacture findings around.

## Findings and concrete resolutions

### PUX-01 — High: core user requirements are routed to a later expansion task

Evidence: `docs/09_Requirements_Traceability_Matrix.md` lines 16,21,32,36–37,56,60,62,68–69,72,74,76–78,81–85,87–92; equivalent `contracts/traceability.json` records. Twenty-six CORE URs and two CONDITIONAL URs use only T18 and have no acceptance IDs. T18 in `docs/21_Implementation_Backlog_and_Traceability.md:30` is a LATER task for mobile/broader on-chain/calibration/broker import. Examples are UR-004 public evidence, UR-048 asset-aware chat, UR-057 in-app alerts, UR-069 admin inspection, UR-076 design and UR-078 historical replay. These are already explicitly assigned to core slices elsewhere; this is an incorrect task map, not owner-approved deferral.

Correction: use `audit_work/product_ux_traceability_suggestions.json` to remap all 28 records to existing task IDs, direct related requirements and existing partial acceptance families; regenerate document 09 consistently. Leave the three genuinely later T18 URs (UR-014, UR-039, UR-063) as later unless a separate scope decision changes them. Do not change implementation or verification statuses. UR-044 retains its CORE safety phase while routing to T14: exact network/identity transparency applies whenever on-chain is exposed.

### PUX-02 — Medium: task-family test names do not supply meaningful feature acceptance

Evidence: document 09 lines 7–9 correctly disclose partial task coverage, but its public search rows 13–17 map to fund-placeholder/NAV/IEX/staleness/split scenarios. Those cases do not test asset search or identity disambiguation. All NFR-001–010 rows (215–224) use the provider-outage scenario TC-OPS-001, which does not measure NFR-006 page usability within 2.5 seconds or NFR-007 search within 500 ms. Core sign-out, contextual asset identity, Turkish comprehension, feedback interaction, admin metrics, current-fetch proof and digest-window behavior lack dedicated meaningful acceptance in the named case register. This is openly incomplete, not a false passed-test claim, but matters before coding.

Correction: preserve `TASK_COVERAGE_NOT_EXHAUSTIVE` and NOT_IMPLEMENTED/NOT_VERIFIED. Add the concrete `required_acceptance_detail` from the suggestion file to the relevant task records before feature implementation. Document 20 or the task record can hold those requirements without inventing new product requirement IDs. Define a reproducible staging load/measurement method for performance targets when the environment exists. Do not label generic inherited cases as complete atomic coverage. UR-062 has no matching existing named case; its browser-push exclusion requires an explicit manual feature review.

### PUX-03 — Medium: a BIST-only sequence is labeled sufficient MVP acceptance

Evidence: `docs/07_Functional_Requirements.md:903–920` says the MVP is functionally acceptable for jury presentation after a BIST-only sequence and a “demonstrable e-mail.” It does not require a fund-specific event, observed current-fetch proof, disclosure of reduced crypto/on-chain/US scope, or distinguish dry-run from real email delivery. It is weaker than `docs/04_MVP_Techstars_Startup_Weekend_Scope.md:9–26`, NFR document quality gate (lines 449–465), and `docs/25_Release_Gates_and_Open_Decisions.md` G11. A future implementer could stop at this sequence and incorrectly declare the agreed product complete.

Correction: rename section 24 to “Core demonstration acceptance, not full MVP completion”; require both a BIST and a fund-specific evidence loop; explicitly distinguish historical replay from synthetic mechanics; require actual current/near-current fetch evidence for UR-079; say in-app and labeled email dry-run exercise mechanics while verified authorized real delivery is required for email-feature completion. Refer full MVP acceptance to the agreed scope and G11; unimplemented crypto/on-chain/US/email is transparently incomplete and reduced acceptance needs owner agreement. This preserves the requirements and does not itself approve a narrower MVP. The NFR jury gate should likewise distinguish desired full acceptance from an owner-approved reduced demo, rather than silently remove its crypto example.

### PUX-04 — Medium: EVM/Solana are misattributed to explicit user choice

Evidence: `docs/07_Functional_Requirements.md:347` calls EVM “User-required EVM coverage”; `docs/21_Implementation_Backlog_and_Traceability.md:32` says “User-requested EVM/Solana.” The user required on-chain intelligence (U07 answer 9); the decision ledger explicitly warns that U08 answer 10 did not choose exact chains/provider. H-49 records EVM plus Solana as the current architecture proposal.

Exact proposed FR-041 replacement: “Provide a bounded EVM adapter for supported showcase contracts after provider/right/finality validation. On-chain intelligence is user-required; EVM is a proposed initial network implementation. An untested or absent adapter is NOT_IMPLEMENTED, not a successful MVP feature.”

Exact proposed document 21 line 32 replacement: “Conditional means explicitly approved or transparently incomplete, not silently ‘done.’ User-required on-chain intelligence, US coverage and email remain in the product scope; EVM and Solana are the proposed initial network implementation. Failure to deliver an agreed required experience means a reduced demo, not full acceptance of the earlier expansive MVP promise.”

Keep FR-041/FR-042 IDs and proposed adapters. Do not silently erase on-chain scope or treat a proposed chain choice as the user's direct instruction.

### PUX-05 — Medium: quiet state still implies health

Evidence: `docs/07_Functional_Requirements.md:684` (FR-084) says “quiet/healthy state” when no eligible event is present. DEC-011 says no alert is not a clean bill of health, and `docs/18_UX_Design_and_Turkish_Content.md:55` supplies “İzlediğimiz verilerde yeni bir uyarı yok.” Missing/disabled detectors are a separate coverage state.

Exact proposed FR-084 replacement: “The dashboard shall display an intentional quiet state when no eligible event is present, using wording such as ‘İzlediğimiz verilerde yeni bir uyarı yok.’ It shall disclose unavailable, stale or disabled coverage separately and shall not imply that an asset is safe or healthy.” Keep legitimate provider-health language in FR-023; the defect concerns financial asset interpretation.

### PUX-06 — Low: design-review record link does not resolve

Evidence: `docs/18_UX_Design_and_Turkish_Content.md:63` references `templates/DESIGN_REVIEW.md`; no such file exists in the baseline. `templates/DESIGN_ACCEPTANCE.md` already contains the required screenshot, real Impeccable results, designer sign-off and unresolved-issues fields.

Correction: replace that path with `templates/DESIGN_ACCEPTANCE.md`.

### PUX-07 — Low: designer review is conditionally optional in one requirement

Evidence: NFR-059 in `docs/08_Non_Functional_Requirements.md:320` ends “before final acceptance where time allows.” DESIGN.md, document 18's design gate and G09 require designer review. The user explicitly required deliberate high-quality design and Impeccable use; time pressure is not recorded approval to bypass final design acceptance.

Correction: remove “where time allows.” If Impeccable cannot be installed/run in an actual implementation, record the failure/availability and unresolved gate rather than fabricate a pass; obtain an owner-agreed alternative if required for release. Do not claim any review has run on this specification package. Keep design tokens in proposed status until the designer approves them.

## Scope observations and owner choices

- The 10–20 BIST / 5–10 funds / 10–20 crypto / 5–10 US active cut remains a baseline proposal. It is not the user's approved complete MVP. Catalog size is separate from actual monitored/on-chain capabilities.
- The full set of desired cross-market, accounts, AI, email and operations features presents substantial work for one developer. The package already recognizes this; this audit cannot substantiate an exact achievable feature count or schedule without spikes and implemented slices.
- Turkish investment funds are confirmed. Pension/specialized/restricted categories remain an unresolved expansion decision; no need to rerun the whole discovery interview.
- Exact network choice, scope shortfalls, budget/providers/latency, email cadence, restricted/public audience and final visual tokens remain owner decisions at the applicable stage. Natural Turkish, mobile vision, high design quality, on-chain intelligence, sources/abstention and email requirement are already decided.
- T18's “broker import” is an unrequested future possibility, not a user-confirmed requirement. Removing it from the committed output or explicitly marking it as unapproved future exploration avoids implying authorization. It is later scope, so it is not evidence of weekend scope expansion.

## Recommended first build slice after gates

Approve one representative Turkish asset/event layout and its states, then implement one BIST and one fund evidence path through public discovery, sourced event, Google sign-in, follow, bounded asset question, in-app alert and minimal admin health/pause. A dated disclosure/allocation event is a legitimate first fund path; do not manufacture AUM/investor history to force an outflow demo. Exercise time-correct replay and current-fetch proof separately. Broaden crypto/on-chain/US and real email only after the anchor behavior and applicable gates pass. This is a proposed sequence, not acceptance of reduced final product scope.

## Review coverage and verification limits

Full text read: baseline AGENTS.md, START_HERE.md, PRODUCT.md, DESIGN.md; documents 00–09,18,20,21,23,25; design_tokens.json; DESIGN_ACCEPTANCE.md, TASK.md and USER_INTERVIEW.md; context 02_DECISION_LEDGER.md,03_FIRST_TASK_AUDIT_AND_OPEN_QUESTIONS.md,04_USER_MESSAGES_TR.md.

All 284 requirement registry objects were parsed; their bodies were compared with the corresponding fully read requirement blocks, with no mismatches. All traceability rows were read through document 09 and their machine objects checked for title/status/amendment alignment, task/phase allocation, empty acceptance and verification status. All 284 remain NOT_IMPLEMENTED; 279 are NOT_VERIFIED and five explicitly REFERENCE_SUBSET_ONLY. No product requirement was marked complete.

Additional local checks here: file existence for the design template; count/phase analysis of T18 mappings; registry/document body identity; registry/traceability title/status/amendment identity; verification-status enumeration. No deployed UI, accessibility, Impeccable, actual auth, live provider, email, real-data replay, E2E, LLM or statistical performance test was run by this reviewer. External source/regulator/provider/literature claims are not verified by this reviewer and must be covered by the separate research audit. No current-source claim is based on this reviewer browsing. No verified user validation findings or final design approval exist in the reviewed package.
