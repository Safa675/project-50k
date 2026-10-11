# Real agent results: the original 100 funds

Completed 2026-10-11 at approximately 13:35:48 Istanbul under DEC-039. Fixed rules
were committed in `88392f3` before admission; recording isolation in `2a530e2`.
This is a historical development evaluation, not independently validated prediction.

## Outcome

| Result | Funds |
|---|---:|
| Original saved cohort selected for agent review | 100 |
| All four real AI stages completed with a valid TEAM proposal | 98 |
| Further review recommended (MATERIAL) | 7 |
| No escalation recommended (NOT_MATERIAL) | 81 |
| Insufficient evidence | 10 |
| Did not complete all stages because of output validation failure | 2 |

The seven recommendations contain four of the eight later liquidation-order funds
in this cohort, and three of the other 92. All eight received complete four-role
reviews. Four of eight were therefore flagged for further review, and four were not.
The automatic first-round subset also consists of seven cases, all seven completed
and recommended further review: four of the eight and three outside that list.
The other 93 full-cohort cases are explicitly user-requested; do not relabel them
as automatic discoveries. No human override replaces the original model proposal.

| Later liquidation-order fund | Actual original agent conclusion |
|---|---|
| THF | Further review recommended |
| TP2 | Further review recommended |
| PRY | Further review recommended |
| PNU | Further review recommended |
| DFI | Insufficient evidence |
| DOH | Insufficient evidence |
| KHA | Insufficient evidence |
| TLY | No escalation recommended |

Among the other 92, three received further-review recommendations, 80 received no
escalation recommendation, seven had insufficient evidence and two failed validation.
Absence from this SPK list does not establish an erroneous anomaly finding. Do not
label the three as proven false positives or report 93% accuracy. The ten evidence
abstentions and two technical failures are not assurances of safety or completed
negative findings. A MATERIAL recommendation means further review, not wrongdoing
or a prediction that a fund will be liquidated.

## What actually ran

- Same installed product image as production:
  `sha256:b2cda0f09d92751f44b2d4ae78a14e1665a609be77892277019f6aa3dd6baf54`.
- Same live models, prompts, stored detector evidence, tests and validators. No model,
  detector or threshold was changed, and the separate monthly research rule was not
  added to the pipeline. That rule's five-of-eight result remains separate.
- Same September 12 scope and detector run `23d372f2-dfa0-43ac-97a8-ee6d92fe7e26`,
  whose data date is September 11. The later September 17 SPK list was joined only
  by the read-only evaluator after case identities were fixed, never given to agents.
- First existing case per fund was mechanically selected before outcomes. Six
  terminal reviews were preserved, two pending automatic reviews promoted and 92
  new user-requested reviews created. The remaining 94 were processed now; this is
  not a claim that all 100 were newly generated in this batch.
- Two workers initially, then four on the same fixed cases through normal atomic
  task leases. Only the local operator's scheduling scope changed. No model-result
  filtering, favorable-round selection, threshold fitting or human review submission.
- Runtime: 800 seconds (13 minutes 20 seconds), from 13:22:28 to 13:35:48 Istanbul.
- Additional booked API cost: USD 3.4889325, within the approved additional USD 5.
  Both runners exited zero; no paid reservation remains and no selected task remains
  queued/running. There were 398 done role tasks and two failed role tasks.
- One verifier and one reporter failed output validation, both outside the eight.
  Normal built-in repair attempts were preserved. Failed output was not accepted.

## Coverage and method limits

Completion is checked against actual COMPLETED live API calls, corresponding role
messages, a valid attached TEAM decision and matching historical packet/run dates.
There are 99 valid reports, but one report followed a failed verifier; it is excluded
from the 98 full four-role completions. A stored report alone is not full completion.

98 cases contain all five standard code tests; 98 complete all four AI stages.
These are not the same 98: 96 satisfy both. Two reused earlier cases, including THF,
predate the monthly-test addition; they retain their original four-test reports.
The two failed cases nevertheless contain all five code tests. No later report was
substituted to conceal this history. New batch cases use the current installed tests.

The reporter can recommend MATERIAL only when the original detector packet permits
it. Reviewing all 100 does not give the LLM authority to invent a new trigger from
the separate monthly experiment. This helps explain why KHA remains an evidence
abstention here while it appears in the separate combined research result.

The original cohort and detectors were developed with knowledge of the historical
case. There is no held-out test set. These observed historical matches are not
validated accuracy, demonstrated future lead time or fraud detection performance.

## Recording protection and retained evidence

The complete run used `p50k-evaluation-db` on a separate Docker network/volume with
no host ports. Production's queue, budget, services and browser were unchanged;
Claude's recording was not operated by Codex. No result was imported into production.
Product source remains frozen; only evaluation documentation changed in Git.

Local-only artifacts are under
`C:/Users/mirza/.local/share/project-50k/evaluations/2026-10-11-agent-cohort-100/`:
`manifest.json`, `run-start.json`, `sidecar-start.json`, `progress.json`,
`evaluation-final.json`, operator/evaluator scripts, the original snapshot and the
completed evaluation database export. They preserve cases, calls, provenance and
results without committing real data. Only aggregate results and the eight permitted
case-fund codes are in this note.

The copied agent ledger went from USD 5.0023225 to USD 8.4912550; its cap was
USD 10.0023225 and reservations ended at zero. Production's USD 5.25 daily cap was
not changed. For future project-wide budget accounting, include the additional
USD 3.4889325 from this isolated run; do not double-count the copied historical spend.

Verification: the read-only evaluator checked all 100 distinct frozen identities,
run/cutoff consistency, four-role live-call/message provenance and proposal linkage,
then joined the eight comparison labels. An independent agent checked final totals.
Operator/evaluator syntax checks and nine synthetic evaluator assertions passed.
No product regression/build/browser suite was rerun for this operational task.

## Accurate Turkish pitch copy

**12 Eylül'de bilinebilen verilerle yaptığımız 100 fonluk tarihsel testte, ajan ekibimiz
7 fonu ileri incelemeye ayırdı. Bu 7 fonun 4'ü, 17 Eylül'de tasfiye kararı verilen
8 fon arasındaydı.**

Nearby context: **Geriye dönük geliştirme testidir; bağımsız doğrulama yapılmamıştır.
Dört ajan adımı 98 fonda tamamlandı; 2 fonda teknik doğrulama hatası oluştu.
İnceleme önerisi, tasfiye tahmini değildir.**

Next: use these actual agent figures in the pitch. Keep the separate combined-method
5/8 explicitly labeled as research if retained. Investigate the two validation
failures and old test-version coverage in a later authorized development slice;
do not modify the frozen product or disrupt the recording to improve these numbers.
