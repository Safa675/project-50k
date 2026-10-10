# DEC-032 — B2B evidence data and API; Turkish funds and stocks

**Date:** 2026-10-10 (Europe/Istanbul)
**Source:** Mirza, technical lead, in chat during Startup Weekend Urla on 2026-10-10.
**Status:** User-confirmed product direction, including real stock support in the hackathon demo.

## Decision

- **Offer.** BlackSwan sells evidence data and API access, supported by an agent workflow, to banks and other
  financial institutions. This is the selected B2B direction, replacing the open insurance-versus-B2B story pick.
- **Product scope.** Turkish investment funds and Turkish stocks. Crypto, US equities and on-chain remain
  postponed. The first demonstrated case is the historical Turkish-fund case already in the repository. Mirza
  subsequently confirmed that stocks must also work in the hackathon demo.
- **Insurance.** Permanently deferred from the product direction. Do not build insurance screens, trigger
  eligibility, policy writing, policy PDFs or the insurer-review print view. Existing research is retained as
  historical work, not active requirements.
- **Workflow.** Deterministic detectors produce the numerical evidence. Agents explain and assess that evidence,
  with a stored audit trail, bounded read-only tools and human override. The workflow supplies institutional
  research and monitoring evidence; it does not produce investment advice.
- **Commercial hypothesis.** The intended buyers are banks and financial institutions, and revenue comes from
  evidence data and API access. No price, pilot, customer demand, willingness to pay or partnership is established
  by this direction decision.
- **Design.** Mirza will supply the design system and logos soon. The approved existing typography, colours and
  text wordmark remain until the assets arrive. No placeholder stock or insurance screens are added.

## Implementation and unchanged gates

- **Stocks are required in the hackathon demo.** The timing question is closed by Mirza's subsequent answer.
  Stock ingestion, detectors and screens are not implemented yet and must not be presented as already working.
- **Alignment pause.** Mirza asked to finish the immediate chat/import/documentation block and stop for a while
  to align. Do not start new stock features during that pause. On resume, implement stocks through new isolated
  modules, with real data, source entitlements, timestamps and a new versioned detector record. Existing fund
  detector parameters and committed protocols remain immutable and are not silently applied to stocks.
- Feature freeze remains Sunday 2026-10-11 10:30, and code freeze remains 13:00 Istanbul. Work continues tonight
  and Sunday morning within that scope and the established integrity rules.
- TEFAS, KAP and MKK rights remain unreviewed. Real data stays on localhost. Selling access is the business
  direction; it does not authorize publication, redistribution, external deployment or paid data acquisition.
- All current detector figures are development results. This decision establishes no validated accuracy,
  prediction, fraud finding or advance warning in the historical case.
- The AI egress rules in DEC-031, budget controls, append-only provenance, human override, secret handling,
  frozen-file protections and merge-only Git policy remain binding.

## Supersession and preservation

- Supersedes DEC-024's postponement of BIST equities for the **product and hackathon demo**. The fund-first
  implementation and its recorded history remain valid; real stock implementation is now required on resume.
- Supersedes DEC-028's pending Saturday story pick and every active insurance option in the current build plan.
- Refines DEC-025's B2B direction with the chosen buyer class, evidence-data/API offer and agent workflow.
- DEC-024, DEC-025 and DEC-028 remain unchanged records of the decisions made at those times. Frozen handoff
  files, committed protocols and research notes are retained, not rewritten or renumbered.

The stock requirement, alignment pause and business-validation follow-ups are recorded in
[team-asks.md](../notes/team-asks.md).
