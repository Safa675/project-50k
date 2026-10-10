# DEC-033: Nontechnical product experience

Mirza's decision, 2026-10-10. Applies to the BlackSwan product UI; frozen research
bundles, protocols and the handoff remain unchanged.

- Users see understandable developments, source names, dated prices and explanations.
  Internal identifiers, hashes, detector codes, storage names and availability-rule
  enums remain in the authenticated API and audit records, not in the product UI.
- Remove the operational rights-review warning from end-user screens. Rights are
  still unreviewed; this decision does not authorize redistribution or deployment.
  Keep that status in internal records and API metadata.
- Replace meaningless missing-value/threshold pairs with a specific explanation.
  Show the last usable price with its actual date when the latest entry is empty.
  Missing observations and chart gaps remain missing; never imply an old price is current.
- Use verified asset/company/manager logos, with truthful labels and source provenance.
- Chat must answer the actual question in ordinary Turkish, explain what each
  observation means and stream useful content. Stream complete validated paragraphs
  as the model generates them; retain their audit trail. No artificial typing delay.
- Explain the actual algorithms beside results and on the method page: what is
  compared, which dated observations are used, how the result is reached and
  what it cannot establish. Distinguish fixed calculations, AI interpretation
  and human review. Do not imply that fund algorithms already run on stocks.
- Preserve deterministic numbers, source citations, read-only tools, derived-only
  OpenAI egress, human overrides and concise factual limitations. Describe prototype
  findings plainly as preliminary assessments rather than validated predictions.

Implementation work is authorized by Mirza's request. No repeated design or Git
approval is needed. Backend progress percentages are estimates against the local
hackathon scope, with a documented feature breakdown, not production-readiness scores.
