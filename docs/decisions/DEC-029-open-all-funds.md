# DEC-029 — Open every downloaded fund for product use

**Date:** 2026-10-10 (Europe/Istanbul)
**Source:** Mirza (technical lead), in chat on 2026-10-10. He answered "Open everything now" when asked how a product that monitors all Turkish funds should be unblocked. The development/test split had been put to Safa on 2026-10-07 and was still unanswered.

## Decision

- **Scope.** All downloaded fund data is opened for product use now, including the 1,922 price files that had been kept unopened. The product may load, compute, chart and show every fund.
- **Split.** The proposed company split (codex context, section 7) is dropped, and there is no held-out test set.
  - Every detector figure from now on is a **development result** and must be labelled as one.
  - No pitch or product text may present such a figure as validated accuracy, recall or lead time.
- **Detectors.** The frozen detectors D1–D5 keep their stored thresholds, which were calibrated on data dated before 2025-10-06 from the 100-fund universe. Applying them to all funds is a new use, not a recalibration.
  - A recalibration, or a new detector, still gets a short dated note committed before it runs, so its parameters are visibly fixed in advance.

## Superseded

This replaces the rule "do not compute anything on the 1,922 unopened price files until the owner approves a split" in:

- `AGENTS.md`;
- `docs/notes/codex-context-2026-10-07.md` section 7;
- `.claude/rules/research-protocols.md`;
- the project skills.

## Unchanged

- **Naming.** Committed files name only the eight liquidated top-100 funds, and no fund is ever called fraudulent or manipulated. The product shows real fund names only on localhost (DEC-027).
- **No real values in git.** Tests use synthetic data.
- **Frozen files stay frozen.** The preregistered detectors, their results and committed protocols.
