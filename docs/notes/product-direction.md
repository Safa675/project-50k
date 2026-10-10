# Product direction (open)

Living note, started 2026-10-10. The market and the headline product are not decided. This file records the ideas,
what the shared platform must provide for each, and what is still open. Decisions that close a question go into
`docs/decisions/`.

## What stays constant

- **The core.** Scientific, mathematical anomaly detection in Turkish investment funds. Stocks come later, only if
  time and licensed data allow.
- **AI-native.** An LLM decides from the deterministic detector evidence, a human can override every decision,
  and users talk to the LLM in the product (DEC-028).
- **Data scope.** Every downloaded fund is in scope (DEC-029). Each detector result is a development result, not a
  validated accuracy figure.

## Ideas under consideration

### 1. Insurance policies designed from fund-risk data

- **Product.** Event-triggered policies for fund investors, designed from fund-risk and anomaly data.
- **Customers.** Sold B2B to insurers, brokers such as Midas, and banks' investment apps, which sell them on to
  their customers.
- **Example.** A client buys a fund and optionally a policy. If a liquidation order or an "act of god" event meets
  the policy terms, the client is paid quickly, without going through institutions or lawyers.
- **Money.** The team never handles money; the institution does.
- **What the platform must provide:**
  - per-fund risk evidence and scores;
  - an event history of past triggers and how often they happened;
  - trigger definitions and live trigger monitoring;
  - an eligibility check for a given policy and date;
  - LLM-written explanations;
  - human override of every LLM decision;
  - a partner view for the institution.

### 2. B2B anomaly data

- **Product.** Sell the anomaly-detection output to institutions for their own investment strategies.
- **What the platform must provide:**
  - an anomaly feed with evidence;
  - per-fund history;
  - a documented API with keys;
  - daily exports or reports;
  - usage limits;
  - clear data-mode labels.

Both ideas run on the same pipeline: ingestion, detectors, decision records and the API. That is why the core is
built first.

## Open questions

| Question | Who | Status |
|---|---|---|
| Headline story for the demo and pitch | Safa, with the team | Due Saturday 2026-10-10, about 22:00 |
| Can a data/model company design or sell insurance policies in Turkey, or must a licensed insurer issue them (SEDDK rules, product approval)? | Safa | Open; research notes below once verified |
| Does selling fund anomaly signals to institutions count as investment advice or research under SPK rules? | Safa | Open |
| Commercial rights to TEFAS, KAP and MKK data, or to signals derived from them | Safa | Open; real data stays on localhost until reviewed (DEC-027) |
| How would a policy be priced? A defensible price needs event base rates, and the archive has one labelled event cluster (the 17 September 2026 SPK order, 131 funds) | Team | Open |
| Which institutions to name in the pitch without implying a partnership | Safa | Open |

## Research notes

The build plan's research pass fills this section with sourced findings. Treat it as orientation, not legal advice.
