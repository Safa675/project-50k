---
paths:
  - "research/events/**"
  - "docs/decisions/**"
---

# Research protocols and decisions

- Committed `PROTOCOL.md` and `PREREGISTRATION.md` files are frozen. A changed rule needs a new versioned protocol,
  committed alone before any real calculation under it, with an "Already seen before writing this" list.
- Never edit `price_detectors/detectors.py`, `PREREGISTRATION.md` or `results.json`; write a v2 beside them.
- All downloaded funds are in scope (DEC-029) and there is no held-out test set: every detector figure is a
  development result. Fix a recalibration's or new detector's parameters in a dated note before running it.
- No threshold, date or rule may be chosen by looking at how the liquidated targets behave. Report development
  results as development results; no accuracy, lead-time or "would have caught" claims.
- Committed files name only THF, TP2, TLY, DFI, DOH, PRY, KHA and PNU. An anomaly or liquidation is not fraud.
- Real values and outputs stay under `raw/`; tests and docs use synthetic or aggregate figures only.
- New owner or team decisions go in a new `docs/decisions/DEC-NNN-*.md`; earlier records are not rewritten.
