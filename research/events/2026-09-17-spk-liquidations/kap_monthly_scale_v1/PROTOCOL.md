# KAP monthly scale-change experiment v1

Recorded 2026-10-11 before the experiment is computed. Mirza authorized a separate development experiment before
the 12:30 freeze. This protocol and its implementation are isolated from every frozen price detector and baseline
result. No output from this experiment enters the existing detector run or model input.

## Fixed admission and rule

- Analysis cutoff: 12 September 2026, 23:59:59.999999 Europe/Istanbul.
- Cohort: every fund in the stored September 12 baseline run. No target fund or later SPK list is used by the rule.
- Inputs: the existing canonical KAP monthly portfolio series, with document publication and availability known
  and no later than the cutoff, and report-period end no later than the cutoff. Ambiguous revisions stay unusable.
- Per fund, use the latest two eligible monthly periods; they must be consecutive calendar months. Both periods
  need strictly positive total portfolio value and units outstanding. Missing/nonpositive values cause abstention.
- Flag only when **both** total portfolio value and units outstanding move in the same direction by a factor of
  at least **2**: both latest/previous ratios are >=2, or both are <=0.5. Boundaries are inclusive; Decimal arithmetic.
- No threshold search, outcome-based selection, gap filling, backdating, category tuning or parameters revised
  after the result is seen. Later reports/revisions never repair this cutoff's missing evidence.

## Interpretation and comparison

This is a monthly fund-size/share-count discontinuity, not evidence of wrongdoing or a forecast. Subscriptions,
redemptions, changes in fund structure, unit denomination and source errors are alternative explanations; NAV
returns alone are not the same observation. The two inputs are related and are not independent corroboration.

Report coverage, flagged/unflagged/abstained counts, source dates and an after-the-fact comparison to the later
confirmed SPK list. Show added detections relative to the unchanged baseline separately; never replace its figures.
Known-event inspection has informed development (including already-seen THF evidence); there is no held-out set,
so the comparison is not validated accuracy, recall, prediction or proven lead time. A failure to flag is not safety.
Any union figure must retain full-cohort and assessable denominators, and clearly label this rule experimental.

Store only protocol/code/synthetic tests in Git. Real values and per-fund experimental outputs stay in the local
database/runtime or an external ignored artifact. Commit this protocol before computing the first real result.
