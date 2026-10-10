# Two product ideas: technical and regulatory check (2026-10-10)

This is for Safa. It is orientation, not legal advice. I accessed all web sources on 2026-10-10. "Unverified" means I did not check the claim against the primary legal text. Repository facts cite file paths.

## Bottom line

- **Insurance (Idea 1):** we cannot issue, price or sell policies ourselves. A licensed insurer must carry the risk under general conditions the regulator has approved. Only banks, registered agencies or licensed brokers may sell. The role we can defend is the insurer's **trigger and risk-evidence engine**. The product we can defend pays on an objective public regulatory event, such as an SPK order that halts TEFAS trading in a fund or liquidates it. It does not pay on price falls. Our data cannot support an actuarial price: the archive holds one labelled event cluster.
- **B2B anomaly data (Idea 2):** this is closer to DEC-025 and to what we have built. The safest legal form is descriptive anomaly data that cites its evidence, sold to licensed institutions, never buy/sell signals. The larger blocker is data rights for TEFAS and KAP, not SPK.
- **Technical view (the team decides):** both stories run on the same core. Each story adds about two screens. B2B data is easier to defend by Sunday. Insurance can be shown as a product built on the same engine, with a licensed insurer as the risk carrier.

## 1. Idea 1: event-triggered insurance for fund investors

### 1.1 Who may do what (Insurance Law 5684, TSB-hosted text [W1])

| Activity | Rule |
|---|---|
| Carrying risk | An insurer needs a licence for each branch it writes (art. 5(1)). Unlicensed activity can close the workplace for up to one year and stop its advertising (art. 34(1)). |
| Policy wording | A policy's main content must follow general conditions approved by the regulator. Special conditions may be added (art. 11(1)). |
| Premium | Insurers set tariffs freely using actuarial techniques (art. 12(1)). Prior approval applies only to compulsory insurance and certain lines: life, accident cover over one year, health, and voluntary earthquake (art. 12). |
| Selling | Agencies must be registered on TOBB's register (Levha) (art. 23(1)). Banks are exempt from that registration and its certificate (art. 23(3)). Agencies other than banks may not run other commercial activity, apart from insurance-related intermediation (art. 23(10)). Brokers need a licence. A SEDDK amendment reportedly raised a broker's minimum paid-in capital to TRY 2.5 million, plus TRY 500,000 for each life or non-life licence [W3]. I did not verify the amendment's date. |
| Claims handling | Under the July 2026 amendment (Resmî Gazete 33318, 23 July 2026), claims management, assistance and claims investigation reportedly became "support services" that need SEDDK permission. New providers reportedly need TRY 250 million in equity [W2]. This comes from a secondary source and is unverified. |

The text says "Müsteşarlık" (the former Treasury undersecretariat). SEDDK is now the regulator (Ek Madde 5).

**What this means for us:**
- We can design the trigger index and the risk evidence, and help an insurer co-design the product.
- The insurer issues the policy, its actuary sets the tariff, and a bank or licensed intermediary sells it.
- **Banks' investment apps are the cleanest sales channel.** A brokerage app such as Midas would probably need an agency or broker partner, because of art. 23(10). That is a question for a lawyer.
- **We must not decide claims.** We supply a trigger report and the insurer decides. If [W2] is accurate, this also keeps us outside the support-services licence.

### 1.2 Product approval

- If an existing branch's approved general conditions can host the cover with special conditions, no new approval may be needed. Otherwise new general conditions need regulator approval. I could not verify which branch would host "loss from a regulatory fund halt or liquidation". A financial-loss branch is the natural candidate, and the approval timeline is unknown.
- I found no separate legal category for parametric (event-triggered) insurance. Turkey already has a retail parametric-style product: a flight-delay cover called "Uçuşum Güvende" from Mehrwerk Türkiye [W9]. I found no SEDDK statement on parametric products.
- **Insurable interest:** pay only investors who held the fund on the trigger date, as shown by the distributor's custody records, and cap the payout at the value of the holding. A payout with no link to an actual loss risks being treated as a wager or a derivative (unverified).
- **Do not trigger on NAV declines.** That is market risk, which makes the product an option or a guarantee, and those fall under SPK. Turkish fund rules already contain guaranteed and principal-protection fund types (I did not re-verify this).

### 1.3 What already protects investors

- **Yatırımcı Tazmin Merkezi (YTM, the investor compensation scheme):** it covers investment firms that fail to pay cash or deliver instruments owed from investment services [W4].
  - A law-firm note of 19 September 2026 says YTM excludes fund value declines, liquidation shortfalls, and losses from advice or market commentary [W5].
  - The same note says the failure of a portfolio management company triggers no YTM payment, because fund assets are kept separate [W5].
  - The statutory base is TRY 100,000 per investor, adjusted every year [W5]. The 2026 figure is unverified.
- **Deposit insurance (TMSF)** does not cover funds [W5].
- **SPK's own process:** on 1 October 2026 SPK announced interim payments for four managers' liquidating funds, capped at TRY 1 million per investor per fund (`OFFICIAL_INCIDENT_CASES.md`, S10). Press results say the liquidation period was extended from three to six months. This is unverified against SPK's text.
- **The protection gap is real:** the loss and the waiting time after a regulatory liquidation are not covered. A gap does not show that anyone will buy cover for it.

### 1.4 Comparable products abroad

- **Nexus Mutual "Custody Cover":**
  - It paid out when a centralised crypto custodian halted withdrawals for more than 90 days. Claimants had to wait 90 days and prove their loss.
  - About $6.37 million was paid across Hodlnaut, FTX, BlockFi and others.
  - The product was sunset after a governance vote, NMPIP-193 [W10]. Figures come from search snippets of its documentation.
  - **Lessons:** it is the closest analogue to fund-suspension cover. It still required proof of loss, the risk was correlated, and it was discontinued. My understanding is that Nexus is a discretionary mutual, not a licensed insurer; I did not verify this.
- **Parametric travel covers** show the model of paying automatically when a defined event occurs [W9].
- This short search found no regulated product that insures retail fund investors against suspension or liquidation. That does not prove none exists.

### 1.5 Base rate and what pricing we can defend

**Repository facts:**
- **One labelled event cluster:** SPK's order of 17 September 2026 covered 131 funds of seven managers and 455,758 unique investors according to MKK (`docs/handoff-v0.5/research/problem_market/OFFICIAL_INCIDENT_CASES.md`, S01, S05 and S07). That file states that no base rate follows from it. The cluster is one correlated episode, not 131 independent events.
- **The price archive:** I counted aggregates only and printed no values.
  - `raw/tefas/prices/` holds 2,022 files, 2,020 of them with at least one price.
  - Row dates run from 2021-10-07 to 2026-10-07, which is TEFAS's five-year maximum.
  - **No series ends before 2026-09-01.** 16 series have their last price in September 2026.
  - TEFAS returns an empty list for retired codes (`docs/notes/codex-context-2026-10-07.md` §5), so closures before September 2026 cannot be seen. The archive is survivorship-biased by construction.
  - 583 of the 2,020 series (29%) started on or after 2024-10-01. Only 635 cover the full five years.
- **Fund size and investor counts** exist only as latest values. Forward snapshots have been collected since 2026-10-09 (`docs/notes/current-state.md`).
- **Severity is unknown:** the liquidations are still running and final recoveries are not known.

**What we can defend:**
- **Not an actuarial premium.** Suppose the five-year window held exactly one such cluster. The exact 95% Poisson interval for the yearly cluster rate is then about 0.005 to 1.1, a range of roughly 200 times.
- **A base-rate study.** Count SPK-ordered TEFAS halts, liquidations and licence cancellations in the SPK bulletin archive over ten years or more, grouping notices into episodes. This is the next real research task.
- **Pricing by scenario and limits, owned by the insurer or reinsurer.** Use a "repeat of the 2026 cluster" stress test, with aggregate limits per manager and per event. The 2026 cluster hit 131 funds in one day, so a portfolio of these policies is one correlated tail risk and needs reinsurance.
- **Detectors for underwriting only.** Detectors (for example fund age, or persistent excess return over peers) can serve as underwriting eligibility or risk-tier evidence, labelled as development results (DEC-029). They are never a probability.
- **Anti-selection rules.** Use waiting periods, and offer no new cover once a public SPK action names the manager.

### 1.6 A product shape we can defend

The pitch line: "An insurer issues the policy and a bank distributes it; we are the trigger and evidence engine."

- **Trigger:** an SPK bulletin that orders a TEFAS trading halt or the liquidation of the insured fund, timestamped from KAP.
- **Payout:** a fixed percentage of the insured holding at the last NAV before the trigger, capped, and paid by the insurer within days. An optional top-up can follow once the liquidation ends.
- **Our deliverables:** trigger monitoring, an eligibility API, an evidence report, and an LLM explanation that a human at the insurer confirms.

## 2. Idea 2: selling B2B anomaly data

### 2.1 Where SPK draws the line

- Communiqué III-37.1, art. 45(2): "Genel yatırım tavsiyeleri ile finansal bilgi sunulması" is outside investment advice [W6]. (General investment recommendations and financial information are not advice.)
- Art. 45(6), added in 2022, says a distributor's guidance on TEFAS funds based on the client's risk and return preferences is not investment advice. Arts. 48(2) and 50 still apply: objectivity and disclosure of conflicts of interest [W7].
- According to a QNB Invest notice, SPK said, in the leveraged-FX context, that services called "al-sat sinyali" (buy/sell signals) or similar, which may amount to investment advice, breach the capital markets legislation [W8].
- Investment advice is a licensed investment service. I did not verify the article in Law 6362 that penalises unauthorised activity.
- **Design:**
  - Sell descriptive anomalies only: what changed, when it became known, and its sources.
  - No buy/hold/sell calls and no tailoring to a client.
  - Disclose conflicts of interest.
  - Sell to licensed institutions for their internal processes.
- Pitching the data "for their own investment strategies" pushes it towards signals. Frame it as risk monitoring and get a capital-markets legal opinion before any contract.

### 2.2 Data rights

- **TEFAS:** Takasbank operates it. Its site notice disclaims accuracy and says the content is not investment advice [W11]. I found no redistribution licence, so commercial use is unverified.
- **KAP:** the official REST route requires a contract, MKK authorisation, a fixed IP scope and an API key, and KAP directs high-volume use to that route (`docs/handoff-v0.5/research/risk_review/DATA_AND_COST_RISKS.md`, DC-01). Our collector uses public web endpoints with pauses between requests (codex context §5). That works for research but is not a commercial way to acquire the data.
- **Derived signals:** whether anomaly scores count as redistribution depends on each publisher's terms. Borsa Istanbul licenses derived and non-display use explicitly (DEC-025). I found no equivalent policy for fund data.
- **Fintables** cannot serve as our backend: its additional terms restrict commercial redistribution and automated access (`docs/handoff-v0.5/research/risk_review/PRODUCT_AND_COMPETITION_RISKS.md`).
- Until the rights are reviewed, real data stays on localhost (DEC-027).

### 2.3 Delivery formats

- A REST/JSON API with keys and quotas; FastAPI's OpenAPI page doubles as its documentation.
- A per-fund history endpoint and a daily CSV export. Webhooks can come later.
- Every record carries:
  - the fund;
  - the detector ID and version, score and threshold;
  - evidence IDs and source URLs;
  - the effective and available-at timestamps;
  - the data mode;
  - a "development result" label.

### 2.4 Comparable vendors

- **Fintables:** fund comparison and filtering, fund-to-stock positions, allocation history, price alarms and its "Evo" AI assistant (`docs/handoff-v0.5/docs/24_Competitor_Evidence_and_Positioning.md`, checked 2026-10-02). **Midas and Investing.com** offer price and event alerts (same file). TEFAS offers free comparison.
- Global fund-research and risk-analytics vendors were not researched in this pass.
- The same file warns against claiming that "nobody does this". Our difference is a hypothesis: evidence tied to the date it became known, and the timing of sources.

## 3. AI-native layer (DEC-028): what it needs

- **Decision records.** Three decision types:
  - materiality of each detector flag: "material", "not material" or "insufficient evidence", with reasons;
  - a policy-trigger assessment: "appears met", "not met" or "insufficient";
  - a fund summary.

  The server validates the structured output. Each record stores its evidence IDs, the model ID, the prompt version, a hash of the input evidence, token use and a timestamp. Records are append-only.
- **Override.** A separate row holds the user, the new decision, the reason and the time. The UI shows "LLM said" next to "a human decided". The roles are an analyst, who can override, and a partner, who views.
- **Chat.** Read-only, bounded tools: search funds, get a fund's evidence, list decisions, and get a policy's terms. The server validates arguments. There is no web search, and KAP PDF text is treated as data. The assistant refuses advice and answers in Turkish.
- **Guardrails.** Reject any claim that cites no evidence ID or an unknown one. Filter fraud, manipulation and buy/sell wording. Fall back to "insufficient evidence".
- **The $25 budget.**
  - Set a hard cost cap inside the app.
  - Cache decisions by fund, date and evidence hash.
  - Precompute decisions for a demo subset.
  - Keep the model ID configurable from OpenAI's documentation. The pricing page returned 403 today, so I quote no prices.
  - When the API is unavailable, fall back to deterministic template text.
- **Data egress.** Prompts that contain real fund data leave localhost. That needs an explicit decision (see §7).

## 4. Platform features by story

| Feature | Core | Insurance | B2B |
|---|---|---|---|
| PostgreSQL in Docker, email/password sessions, roles | ✓ | | |
| Ingestion: 2,022 price histories, forward snapshots, KAP reports for the top 100 only | ✓ | | |
| Detectors D1–D5 on all funds, with their frozen thresholds (DEC-029) | ✓ | | |
| SPK/KAP event store with available-at times | ✓ | trigger feed | |
| Decision records, override, audit, chat | ✓ | | |
| Data-mode labels everywhere (`HISTORICAL_REPLAY` and the others) | ✓ | | |
| Trigger definitions, monitoring, eligibility check for a fund and date | | ✓ | |
| Event-history table; exposure grouped by manager | | ✓ | |
| API keys, quotas, OpenAPI docs | | | ✓ |
| Anomaly feed and daily CSV export | | | ✓ |

## 5. Minimum demo screens for the Sunday 13:00 freeze

**Core (build by Saturday night):**
1. Sign-in.
2. Fund list covering all funds, with flag status and data-mode badges.
3. Fund page: chart, detector evidence, SPK/KAP timeline, and the LLM decision with its override button.
4. Review queue of LLM decisions, with override and audit trail.
5. Chat panel with citations.

**Story pair (Sunday morning):**
- **Insurance:**
  - (6) trigger definition and eligibility check, run on the September 2026 episode labelled `HISTORICAL_REPLAY`. The screen says "trigger fired on the SPK order date", never "detectors predicted it";
  - (7) partner panel: covered funds, exposure grouped by manager, triggers fired.
- **B2B:**
  - (6) API keys and documentation;
  - (7) anomaly feed with CSV export and a usage counter.

**What to cut first:** the partner panel, webhooks, and any export format beyond CSV.

## 6. Key risks

| Risk | Mitigation |
|---|---|
| The pitch implies we insure or sell policies | Say "insurer-issued; we supply triggers and evidence" |
| Pricing credibility: one cluster, survivorship bias | Show the uncertainty interval; the insurer prices |
| Risk tiers on named funds read as accusations or move the market | Partner-only views, no fraud wording, descriptive language |
| Investment-advice classification (Idea 2) | Descriptive output, licensed buyers, a legal opinion |
| Data rights for TEFAS and KAP | Localhost only; name the licensing route (MKK, Takasbank) |
| LLM errors, cost or outage | Schema and citation checks, cache, cap, template fallback |
| Correlation and adverse selection (insurance) | Aggregate limits, waiting periods, a cut-off rule |
| Conflict of interest: banks own many fund managers | Disclose it (DEC-025) |
| One developer with about 25 hours | Core first, story chosen by 22:00, the cut list above |

## 7. Collisions with recorded decisions

- **DEC-025:** it set the pitch as compliance monitoring for distributors. Idea 2 fits it; Idea 1 needs a new DEC record.
- **Handoff integrity rules:** "Confidence v1 is not a probability" and "the LLM does not assign the score". An insurance premium needs probabilities. The LLM may decide materiality, but it should not set scores, prices or payouts. The insurer's human confirms every trigger.
- **DEC-027 versus DEC-028:** DEC-027 keeps real data on localhost, but OpenAI prompts would carry real fund data. Choose between explicit approval and sending only derived features.
- **The handoff's "no buy/hold/sell"** rule cuts against Idea 2's "for their own strategies" framing.
- **"Would have caught"** wording stays forbidden (`docs/notes/current-state.md`). This includes any insurance replay.

## 8. Questions Safa must answer before the pitch

1. Which headline story, by about 22:00?
2. Insurance: do we pitch ourselves only as the data and trigger provider? Which kind of insurer do we name as a *target* partner, without implying contact?
3. What exactly is the trigger scope? Only SPK-ordered TEFAS halts and liquidations? Do manager licence cancellations count? Are price falls excluded?
4. What is the payout: a fixed percentage paid on the trigger, an indemnity after liquidation, or both? What payment time do we target?
5. Who holds the policy: the individual investor, or the distributor through a group policy for its clients?
6. Which channel do we show: bank apps, which may act as agencies, or brokerage apps such as Midas, which need an agency or broker route?
7. What is the revenue model (a hypothesis): a per-policy data fee from the insurer, a subscription, or a revenue share?
8. B2B: who is the first buyer (distributor product governance and compliance, portfolio managers, or insurers' underwriting)? Which decision does our data change for them?
9. Data rights: do we approach MKK (for KAP) and Takasbank (for TEFAS) after the event? What are the terms of the sources Safa found?
10. Who gives a capital-markets and an insurance-law opinion after the event?
11. May the demo send real fund data to OpenAI, or only derived features?
12. Which institutions may be named, and with what wording?

## Sources

**Web (accessed 2026-10-10):**
- [W1] Insurance Law 5684 (TSB copy): https://www.tsb.org.tr/content/Legislations/1.5.5684.pdf. I read arts. 5, 11, 12, 23 and 34; I did not check whether the copy is fully consolidated.
- [W2] https://www.alomaliye.com/2026/07/23/sigortacilik-destek-hizmetleri-yonetmeligi-degisti/ (secondary source; Resmî Gazete 33318 not checked)
- [W3] https://www.bloomberght.com/seddk-dan-sigorta-ve-reasurans-brokerleri-icin-duzenleme-2345867 (search snippet)
- [W4] https://www.ytm.gov.tr
- [W5] https://hukukcularevi.com/fon-magduru-yatirimci-tazmin-merkezi-ytm-para-alabilir-mi-tazmin-kapsami-tmsf-guvence/
- [W6] https://alomaliye.com/2013/07/11/yatirim-hizmetleri-ve-faaliyetleri-ile-yan-hizmetlere-iliskin-esaslar-hakkinda-teblig-iii-37-1/
- [W7] https://www.alomaliye.com/2022/04/07/yatirim-hizmetleri-ve-faaliyetleri-ile-yan-hizmetler-iii-37-1-c/
- [W8] https://www.qnbinvest.com.tr/forex/duyuru/spk-al-sat-sinyallerine-dair-tebligi (search snippet)
- [W9] https://paradergi.com.tr/sektorler/2026/05/20/yillik-policeler-demode-oldu-parametrik-sigorta-modelleri-yukseliste
- [W10] https://docs.nexusmutual.io/overview/cover-products/custody-cover and https://docs.nexusmutual.io/overview/claims-history/ftx (search snippets)
- [W11] https://www.tefas.gov.tr/tr/tefas-istatistikleri (search snippet of the site's legal notice; I did not identify the page with the exact clause)
- Liquidation-period press results: https://www.ekonomigazetesi.com/ekonomi/tasfiye-icin-henuz-yontem-belirlenmedi-88161 (unverified)
- OpenAI pricing (https://openai.com/api/pricing/) returned HTTP 403.

**Repository (absolute paths under `C:\Users\mirza\Desktop\Hackathon\project-50k\`):**
- `docs\notes\current-state.md`
- `docs\notes\codex-context-2026-10-07.md`
- `docs\notes\product-direction.md`
- `docs\decisions\DEC-025-b2b-fund-monitoring-pitch.md`
- `docs\decisions\DEC-027-event-weekend-operations.md`
- `docs\decisions\DEC-028-deploy-ready-ai-native-build.md`
- `docs\decisions\DEC-029-open-all-funds.md`
- `docs\handoff-v0.5\research\problem_market\OFFICIAL_INCIDENT_CASES.md`
- `docs\handoff-v0.5\research\risk_review\DATA_AND_COST_RISKS.md`
- `docs\handoff-v0.5\research\risk_review\PRODUCT_AND_COMPETITION_RISKS.md`
- `docs\handoff-v0.5\docs\24_Competitor_Evidence_and_Positioning.md`
- `raw\tefas\prices\` (aggregate counts only)