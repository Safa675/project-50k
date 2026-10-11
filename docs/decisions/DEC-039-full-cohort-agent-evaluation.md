# DEC-039 - Complete the original 100 through the existing agent workflow

Mirza, 2026-10-11, after code freeze.

- Run the complete saved original 100-fund cohort through the working agent workflow
  under the 12 September evidence cutoff. Do not evaluate only the eight known cases.
- Measure actual final recommendations, missed later liquidation-order cases and
  recommendations outside that later list. Outside-list recommendations are not
  automatically errors; liquidation is not the system's predicted outcome.
- Preserve automatic-opening provenance separately from user-requested batch reviews.
  The historical combined price/portfolio 5/8 remains a separate research result.
- Mirza explicitly approved up to USD 5 additional for this run: agent daily ceiling
  USD 10.25 instead of USD 5.25; existing USD 25 project target unchanged. Keep future
  daily defaults unchanged and record actual cost and any uncompleted cases.
- Product source stays frozen. Use existing application case/task/worker functions,
  real model calls, normal stored evidence and validators; preserve all prior AI and
  human decisions. No threshold/prompt tuning or future-label input to improve this score.
- Fixed measurement and case-selection rules are in
  `plans/2026-10-11-agent-case-evaluation.md`, committed before the batch is submitted.

This authorizes an operational evaluation, not a validated-accuracy claim or a code release.
