# Product direction: B2B evidence data and API

Living note, started and updated 2026-10-10. Mirza confirmed the direction in
[DEC-032](../decisions/DEC-032-b2b-evidence-data-api.md). Earlier options and research below are retained with their
status; insurance is permanently deferred and is no longer an implementation path.

## Confirmed direction

- **Offer and buyers.** Sell evidence data and API access through an agent workflow to banks and financial
  institutions. The buyer class and revenue direction are decided; pricing, a pilot and customer demand remain
  hypotheses to test.
- **Asset focus.** Turkish funds and Turkish stocks. Start with the existing historical fund case. Mirza confirmed
  that stocks must also work in the hackathon demo; stock support is required, not yet implemented. Build it on
  resume with real entitled data and new stock-specific evidence rules, preserving immutable fund protocols.
- **Alignment pause.** Finish the immediate chat/import/documentation block, then stop until Mirza resumes.
  Do not start a new stock feature during this requested pause.
- **Institutional workflow.** Deterministic detectors produce evidence, agents explain and assess it, and human
  reviewers can override every decision. Preserve the original decision, evidence references and review trail.
- **Insurance.** Permanently deferred. Build no insurance screens, eligibility checks, policy writer, policy PDFs
  or insurer-review print view.
- **Publication.** Commercial data rights remain unreviewed. Real data stays on localhost; the revenue direction
  does not authorize resale, deployment or a claim that institutions already want to buy it.
- **Design.** Mirza will supply the design system and logos soon; existing approved tokens and the text wordmark
  remain until then.

## What stays constant

- **The core.** Scientific, mathematical anomaly evidence for Turkish funds and stocks, with the historical fund
  case implemented first. Stock support is required in the hackathon demo; implementation and entitled sources
  still need work after the alignment pause.
- **AI-native.** An LLM decides from the deterministic detector evidence, a human can override every decision,
  and users talk to the LLM in the product (DEC-028).
- **Data scope.** Every downloaded fund is in scope (DEC-029). Each detector result is a development result, not a
  validated accuracy figure.

## Earlier options (superseded by DEC-032; retained as history)

### 1. Insurance policies designed from fund-risk data — permanently deferred

The proposal below is historical. Its requirements are not active build work.

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

### 2. Earlier B2B anomaly-data proposal — refined by DEC-032

- **Product.** The earlier proposal sold anomaly-detection output to institutions. DEC-032 specifies evidence
  data and API access for banks and financial institutions, supplied through an agent workflow for research and
  monitoring.
- **What the platform must provide:**
  - an anomaly feed with evidence;
  - per-fund history;
  - a documented API with keys;
  - daily exports or reports;
  - usage limits;
  - clear data-mode labels.

The proposals shared ingestion, detectors, decision records and the API. That core remains; only the confirmed
B2B direction receives story-specific implementation.

### Agent team (under study since 2026-10-10)

The team is looking at [TauricResearch/TradingAgents](https://github.com/tauricresearch/tradingagents)
(Apache-2.0) as a model.

- **How it would work.** A team of LLM agents reads the data, analysts report, a challenger debates them, and a
  committee reaches an outcome.
- **Historical policy-writer proposal.** Permanently deferred with insurance; no policy-writing or PDF task is
  active.
- **Our constraints.**
  - Scores stay deterministic.
  - Every agent decision can be overridden by a human.
  - Agents never issue buy/sell calls.
  - The retained insurance research never established an issued or priced policy; insurance is now deferred.
  - The $20 LLM cap holds.
- **Status.** Studied, designed and critiqued on 2026-10-10; see `docs/notes/research-2026-10-10/agents-*.md` and
  section 7 of the build plan. TradingAgents' code is not reused; we copy only its structure, as a fixed pipeline in our
  own worker. Before the freeze that means server-written briefs, then a challenger, then a committee with human
  override. The earlier insurer-review print-view and policy-writer/PDF proposals are superseded by DEC-032 and
  receive no implementation slot.

The B2B choice, buyer class and revenue direction are now confirmed. Safa still develops the commercial plan and
validates the customer workflow, pricing and data-rights route.

## Open questions

| Question | Who | Status |
|---|---|---|
| Headline story for the demo and pitch | Mirza, with the team | Closed 2026-10-10: B2B evidence data and API for banks and financial institutions (DEC-032) |
| Include stocks in the hackathon implementation, or complete the historical fund case first and add stocks next? | Mirza | Closed 2026-10-10: stocks must work in the hackathon demo too. Build new isolated stock support on resume; fund protocols remain immutable |
| First institutional workflow, pilot and pricing for evidence data/API | Safa | Open; buyer class and revenue direction confirmed, customer demand unvalidated |
| Can a data/model company design or sell insurance policies in Turkey, or must a licensed insurer issue them (SEDDK rules, product approval)? | Safa | Deferred with insurance by DEC-032; retained research only |
| Does selling fund anomaly signals to institutions count as investment advice or research under SPK rules? | Safa | Open |
| Commercial rights to TEFAS, KAP and MKK data, or to signals derived from them | Safa | Open; real data stays on localhost until reviewed (DEC-027) |
| How would a policy be priced? A defensible price needs event base rates, and the archive has one labelled event cluster (the 17 September 2026 SPK order, 131 funds) | Team | Deferred with insurance by DEC-032; no policy pricing task |
| Which institutions to name in the pitch without implying a partnership | Safa | Open |

## Research notes (2026-10-10; orientation, not legal advice; verify before relying on them)

**Insurance — historical research, permanently deferred by DEC-032.**
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

**Historical technical view, superseded by DEC-032.** The research compared two stories on the same core. The
current implementation serves B2B evidence data and API access; insurance is no longer a demo path.

Sources and details: `docs/notes/research-2026-10-10/research-product.md` (regulation and products) and
`inventory-data.md` (data sources).
