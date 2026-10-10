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

### Agent team (under study since 2026-10-10)

The team is looking at [TauricResearch/TradingAgents](https://github.com/tauricresearch/tradingagents)
(Apache-2.0) as a model.

- **How it would work.** A team of LLM agents reads the data, analysts report, a challenger debates them, and a
  committee reaches an outcome.
- **Policy writer.** For the insurance route, a policy-writer agent would draft the policy document as a PDF.
- **Our constraints.**
  - Scores stay deterministic.
  - Every agent decision can be overridden by a human.
  - Agents never issue buy/sell calls.
  - Any policy PDF is a draft for an insurer's review, not an issued or priced policy.
  - The $20 LLM cap holds.
- **Status.** Studied, designed and critiqued on 2026-10-10; see `docs/notes/research-2026-10-10/agents-*.md` and
  section 7 of the build plan. TradingAgents' code is not reused; we copy only its structure, as a fixed pipeline in our
  own worker. Before the freeze that means server-written briefs, then a challenger, then a committee with human
  override. For insurance, the policy writer becomes a deterministic insurer-review print view, "Tetikleyici Endeksi
  ve Kanıt Spesifikasyonu", never a policy schedule. LLM policy writing and PDFs come after the event.

The final business plan is due Saturday evening, after the mentor meetings.

## Open questions

| Question | Who | Status |
|---|---|---|
| Headline story for the demo and pitch | Safa, with the team | Due Saturday 2026-10-10, about 22:00 |
| Can a data/model company design or sell insurance policies in Turkey, or must a licensed insurer issue them (SEDDK rules, product approval)? | Safa | Open; research notes below once verified |
| Does selling fund anomaly signals to institutions count as investment advice or research under SPK rules? | Safa | Open |
| Commercial rights to TEFAS, KAP and MKK data, or to signals derived from them | Safa | Open; real data stays on localhost until reviewed (DEC-027) |
| How would a policy be priced? A defensible price needs event base rates, and the archive has one labelled event cluster (the 17 September 2026 SPK order, 131 funds) | Team | Open |
| Which institutions to name in the pitch without implying a partnership | Safa | Open |

## Research notes (2026-10-10; orientation, not legal advice; verify before relying on them)

**Insurance.**
- **Who may do what.** Under Insurance Law 5684:
  - only licensed insurers carry risk (art. 5);
  - policy wording follows general conditions approved by the regulator (art. 11);
  - only registered agencies, licensed brokers or banks may sell (art. 23).

  A data company cannot issue, price or sell policies itself. The defensible role is the insurer's **trigger and
  evidence engine**.
- **Channels.** Banks are exempt from agency registration. A brokerage app such as Midas would probably need an
  agency or broker partner (unverified).
- **Defensible trigger.** An objective public regulatory event: an SPK order halting a fund's TEFAS trading or
  liquidating it. Never a NAV fall. That is market risk, which would turn the product into an option or a
  guarantee under SPK.
- **Claims.** We supply a trigger report and the insurer decides the claim. A 2026 amendment reportedly made claims
  handling a licensed support service (secondary source, unverified).
- **Existing protection.**
  - YTM (the investor compensation scheme) excludes fund value declines and liquidation shortfalls.
  - TMSF does not cover funds.
  - SPK's own interim payments (1 October 2026) are capped per investor per fund.
  - So the gap is real. A gap does not prove demand.
- **Pricing.** The archive holds one correlated event cluster. A single cluster in five years gives a 95% interval of
  roughly 0.005 to 1.1 clusters a year, so there is no actuarial premium. The defensible next step is a base-rate study
  of SPK bulletins from 2005 on. The insurer prices with scenario stress tests and aggregate limits.
- **Comparable.** Nexus Mutual's "Custody Cover" paid on withdrawal halts after a 90-day wait with proof of loss. It
  was later discontinued.

**B2B anomaly data.**
- **SPK line.** Under Communiqué III-37.1 art. 45(2), "general recommendations and financial information" are not
  investment advice. Services called buy/sell signals may breach capital-markets law. Sell **descriptive** anomalies
  with evidence to licensed institutions, never buy or sell calls, and disclose conflicts of interest.
- **Data rights are the larger blocker.**
  - TEFAS (Takasbank) has no published redistribution licence.
  - KAP sends high-volume use to its contracted REST service, which needs MKK authorization.
  - Real data stays on localhost until rights are reviewed (DEC-027).

**Technical view.** Both stories run on the same core and each adds about two screens. B2B is easier to defend by
Sunday; insurance can be shown on the same engine with a licensed insurer as the risk carrier.

Sources and details: `docs/notes/research-2026-10-10/research-product.md` (regulation and products) and
`inventory-data.md` (data sources).
