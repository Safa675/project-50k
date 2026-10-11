# Real agent evaluation of the original 100-fund cohort

Authorized by Mirza on 2026-10-11 after code freeze. Product code stays frozen.
He requested actual agent-workflow results for the eight later SPK liquidation-order
funds inside the saved original 100, and a realistic time estimate.

## Fixed evaluation rules (commit before reading decision outcomes or queueing)

- Cohort: the existing `top100_funds.txt` membership, not a newly ranked or selected universe.
- Historical input: the existing 12 September view and run
  `23d372f2-dfa0-43ac-97a8-ee6d92fe7e26`, using its eligible evidence only.
- Comparison labels: the eight confirmed 17 September SPK liquidation-order funds in
  that cohort. These labels never enter an agent prompt, case title, evidence packet,
  test, or user investigation request. No new monthly-rule integration or threshold changes.
- Primary automatic measure: use each cohort fund's FIRST sentinel-opened case for
  this run. Record its ID before reading outcomes. Do not replace it with a later,
  more favorable user review. Funds not opened by the sentinel are not automatic discoveries.
- A completed positive requires all four review-role tasks done, actual live model
  output for each role, a VALID live TEAM decision attached to the selected case,
  and a MATERIAL decision. MATERIAL means worthy of further review, not wrongdoing
  or a predicted liquidation. DATA_ISSUE, INSUFFICIENT_EVIDENCE, NOT_MATERIAL, incomplete
  and failed cases are separate outcomes; none is silently counted as a positive.
- Complete pending automatic cases across the original 100, not only among the eight
  known cases. Queue promotion may change scheduling priority/source but must preserve
  original sentinel provenance, prior evidence, original decisions and human reviews.
- Separately audit all eight known cases through the ordinary existing workflow. Reuse
  the first existing case for each fund; for funds without a case, make one ordinary
  user investigation request containing only the fund code. Label these new cases as
  user-requested, never automatic discoveries. No repeated run to seek a desired answer.
- Report automatic escalation, completed review, final review recommendation, missing
  data, technical failures, manual requests and remaining work separately. Also report
  recommendations among the other 92 funds; absence from this SPK list does not prove
  a false positive. No claim of validated accuracy or future lead time: this remains a
  historical development study informed by a known case, without a held-out test set.
- Record selected case IDs, task/model/prompt provenance, costs and outcomes outside
  Git under the existing local data directory. Commit only aggregate outcomes and the
  eight permitted case-fund names/codes. Never store raw source or private data in Git.
- Use normal application services and the running worker. No human review submission,
  synthetic responses, direct result edits, product rebuild or fallback-demo changes.
- Use the existing approved budget. If the daily allowance prevents completion, report
  that blocker and the remaining amount/work; never silently remove a spending guard.

## Preflight, before outcomes

- Five of the eight have existing reports. Three have no agent case.
- The original 100 have seven first sentinel cases: five reached report/closed state;
  two remain open. These two must also be completed for the automatic cohort comparison.
- The live team is running. Recent completed reviews cost roughly USD 0.03-0.04 each.
- Today's agent bucket has USD 5.0023225 booked of USD 5.25, with no reservation at
  inspection. The focused work is estimated at 5-15 minutes if calls and budget permit.
- The earlier combined price/portfolio 5/8 result is separate and remains unchanged.

Results will be recorded in a separate note so these fixed rules remain reviewable.
