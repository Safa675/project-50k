# Data, provider and cost risks

Reviewed 2026-10-02 against current owner decisions, docs 10/22/25, prior source-verification records and selected freshly reopened primary sources. This review performed document browsing only: no accounts, entitlement tests, live data/API samples, purchases, contact or deployment. Severity describes consequence **if the risk materializes**; evidence strength describes what is established, not its probability. Prices below are dated public list-price observations, not vendor quotations or purchase recommendations.

The main weakness is a dependency chain: accessible data → usable fields → permitted analysis/display → reliable collection → affordable operation. A successful download proves only the first step. Current documents correctly leave those gates open. Neither feasibility nor blanket infeasibility of the four-market target has been established.

| Priority | Concrete risk | Severity | Evidence strength |
|---|---|---|---|
| DC-01 | BIST/KAP use rights and authorized acquisition may block the central public workflow | Critical | Strong official route/requirements; actual entitlement and price unknown |
| DC-02 | Fund history may support price charts but not dated flow/count/allocation claims | High | Strong prior source inspection and local counterexamples; fresh live coverage untested |
| DC-03 | Cheap US feed changes the meaning of volume/divergence signals | High | Strong current official feed documentation; business redistribution unknown |
| DC-04 | Meaningful on-chain coverage may outrun free RPC reliability and quota | High | Strong official public-RPC caveat; actual load/provider capacity unmeasured |
| DC-05 | Free hosting assumptions may conflict with intended use or reliable demo operation | High | Strong current published plan limits; applicability/account acceptance untested |
| DC-06 | Recurring commitments can consume a cumulative TRY 5,000 ceiling | High | Strong owner constraint and published billing examples; duration/FX/taxes unknown |
| DC-07 | Runtime research/retries and retained evidence can create uncontrolled variable spend | High | Strong architecture/workload path; actual unit workload/cost not measured |
| DC-08 | Missing publication history and corrections can defeat honest replay despite stored prices | High | Strong existing provenance contract and offline counterexamples; provider completeness unknown |

## DC-01 — Acquisition and use permissions are separate dependencies

**Causal path:** use an accessible wrapper/page → compute anomalies and retained histories → display derived alerts to users → intended use falls outside the demonstrated entitlement → public release is blocked or acquisition must be redesigned. BIST's official FAQ describes separate non-display and derived-data contractual requirements [DC-S01]. KAP's official one-page REST description specifies contract, MKK authorization, IP scope and API key, and directs high-volume requests to that route [DC-S02]. These are publisher statements, not a legal conclusion about this particular project. Current G02/G04 are open; no price or lead time was verified.

If personal Fintables/EVO access is considered, its published additional terms restrict automated access without authorization and commercial redistribution of EVO outputs [DC-S11]. A connected personal tool does not establish this product's data or output entitlement.

**Early signals:** no entitlement evidence ID for processing/history/derived display/redistribution; development subscription offered as business permission; website polling proposed instead of an authorized acquisition route. **Cheapest honest falsification:** prepare the exact use/field/retention/user matrix and compare it with publicly available distributor terms; unknown clauses remain unresolved. A future owner-authorized written provider confirmation would establish actual scope, but was not sought here. **Contingency:** keep four-market adapters and local synthetic examples; use permission-cleared replay only where a manifest permits it. Preserve G11 as unmet until accepted real-data paths exist; simulation is not silently substituted as the completed live target. Trace: DR-006, G02/G04/G11.

## DC-02 — Fund data richness and timing are weaker than the interface suggests

**Causal path:** historical method returns a familiar schema → placeholders/latest details are treated as dated historical AUM/counts → flow or allocation anomaly looks precise → unsupported financial interpretation reaches users. Prior inspected wrapper sections document historical placeholders and unsafe date/TLS behavior; this short refresh could not independently recover those code sections [DC-S09]. SPK supplies the NAV/unit definition, not a historical API coverage promise [DC-S08]. This session's TEFAS public homepage retrieval was rejected [DC-S10]; that observation does not prove the service is unavailable to all users. The fund lab already demonstrates that valid endpoint residuals still do not identify transaction cash or asset sales.

**Early signals:** zeros/NaNs, AUM dated by the NAV timestamp, retrieval time replacing source date, missing distribution/split status, allocation snapshot called current holdings. **Cheapest honest falsification:** offline contract checks now; when acquisition and rights are separately admitted, capture two funds × two valuations plus one allocation change with raw fields and independent publication dates, using verified TLS. Test malformed dates/placeholders rather than only happy paths. **Contingency:** retain the fund experience with honest published-NAV/snapshot context and clearly disabled unsupported detectors; keep required capability gaps visible. Trace: DR-002/004/005, G03/G10; `research/engine_lab/FUND_ENGINE.md`.

## DC-03 — US market coverage can silently change the detector

**Causal path:** Basic feed appears to cover all US symbols → IEX-only volume is presented as consolidated volume, or IEX/SIP histories are mixed → thresholds and comparisons become incomparable → false alert or hidden omission. Alpaca currently documents Basic IEX coverage, 30-symbol streaming and distinct paid coverage [DC-S03]. A personal/developer plan description does not establish multi-user commercial display rights.

**Early signals:** missing `feed`/venue fields, “US volume” without venue qualification, free-plan stream universe over 30, subscription price treated as redistribution permission. **Cheapest honest falsification:** pin feed metadata and compare one synthetic IEX/SIP mismatch through admission guards; later obtain one authorized same-window bar sample with known feed. **Contingency:** preserve US equities with explicit feed/delay and bounded active universe; do not imply market-wide consolidated volume or silently change feed. Alternative official filings provide context, not a replacement price feed. Trace: DR-003/008, G04/G11.

## DC-04 — Public on-chain RPC is a fragile production assumption

**Causal path:** token discovery/history scans plus retries → public RPC throttles or blocks → finality/backfill gaps → delayed or incorrect on-chain alerts. Solana's official documentation warns that public endpoints are not intended for production and rates can change; 403/429 behavior is documented [DC-S07]. This supports a reliability concern, not an assertion that a bounded demonstration will fail.

**Early signals:** request budget grows with chain history or every user page load, wide `getLogs`/account scans, missing checkpoints/finality, retry bursts, unknown token-account coverage. **Cheapest honest falsification:** offline request-count worksheet and injected 403/429/timeout/reorg fixtures for a bounded contract/mint/block range; any later live spike must record quota and gaps without claiming full-chain coverage. **Contingency:** keep meaningful on-chain identity/finalized evidence for a disclosed bounded universe, shared collection/cache and clear partial coverage. Permission-cleared replay can support development; devnet/synthetic examples remain labeled and do not establish mainnet coverage. Exact networks remain a capability decision, not silent removal of on-chain. Trace: DR-008/012, G04/G10/G11.

## DC-05 — “Free” does not mean appropriate or dependable

**Causal path:** architecture assumes free front end/database/worker indefinitely → usage terms, inactivity pause or exhausted resource credit → unavailable demo or forced upgrade → cost and schedule change. Vercel documents Hobby as personal non-commercial use [DC-S04]; project applicability requires review rather than a blanket legal verdict. Supabase lists inactivity pausing and limited active projects [DC-S06]. Railway's current trial/credits and usage billing differ from unlimited free operation [DC-S05].

**Early signals:** commercial startup experience planned on an assumed Hobby entitlement; paused database; three development/staging/production databases assumed within two free projects; worker estimates omit idle RAM. **Cheapest honest falsification:** inspect the intended-use plan matrix and run local process-memory/storage sizing, with no provisioning. Before any deployment, verify selected plan behavior against the actual topology. **Contingency:** keep local reproducible four-market/on-chain demonstration paths available, choose appropriately permitted hosting only after a priced decision, and schedule readiness checks when deployment is separately authorized. A local fallback is a development contingency, not accepted final scope reduction. Trace: docs22 topology, G05/G08/G11.

## DC-06 — The ceiling is cumulative, while vendors bill repeatedly

**Causal path:** small monthly prices look affordable → renewals, data entitlement, taxes, FX, domain/email and contingency are added over an unspecified duration → total commitments exceed TRY 5,000. The owner excludes only development Claude/Codex subscriptions, not runtime inference or search. Current observations: Railway Hobby minimum usage USD 5 with excess usage; Supabase Pro from USD 25/month; Alpaca individual Algo Trader Plus USD 99/month [DC-S03/05/06]. None is a complete quote for this project's commercial configuration, and none was purchased. Do not sum these as a required deployment bill or convert using an invented exchange rate.

**Early signals:** TRY 5,000 becomes a monthly allowance; plan credits double-counted; operating end date missing; automatic renewals or distributor fee unreserved. **Cheapest honest falsification:** price only the chosen configuration over an explicit operating horizon, with dated FX/tax assumptions and rights route; compare `committed + actual + reserved + contingency` with 5,000. **Contingency:** bounded local development, optional vendor choices and time-limited authorized operation; surface any capability/budget conflict before spending. Do not drop a market or on-chain to make arithmetic fit without owner approval. Trace: DEC-020, docs22 §0, G05/G11.

## DC-07 — Fan-out, agent retries and retained evidence are variable-cost multipliers

**Causal path:** one event/chat fans out to searches, sources, explanations, notification recipients and retry attempts → runtime calls/egress/storage grow faster than user count → a small nominal plan fails the cumulative ceiling. The proposed 6,000 monthly chats and per-turn tool caps are authored workload assumptions, not measurements. Data licenses and allowed retention are independent from storage prices. No runtime model/search plan is selected or priced in this review.

**Early signals:** regenerated explanation per recipient, provider calls on page refresh, multiple providers retried without persistent budget accounting, long context copied repeatedly, unlimited full raw-document retention. **Cheapest honest falsification:** use local authored worst-case traces to count input/output tokens, tool calls, retries, stored bytes and fan-out; substitute verified selected-model/tool prices only later. **Contingency:** one shared permitted event explanation, persistent per-project quotas, bounded retries/context, reuse allowed artifacts and a deterministic evidence-only degraded response. Keep all four domain paths; no unsupported “AI is free because development accounts are excluded” assumption. Trace: docs10 §6, docs22 §6, DR-006/009, G05.

## DC-08 — Historical price availability does not supply historical knowledge

**Causal path:** current corrected price/fund/disclosure/identity metadata is retained → backtest treats it as known earlier → apparently convincing anomaly performance or attribution is overstated. A price history endpoint alone does not demonstrate publication timestamps, first receipt, corrections or historic label versions. The offline fund cutoff cases establish the logical failure mode, not actual provider accuracy.

**Early signals:** only valuation time stored, current holdings/wallet labels used in old examples, unknown `available_at`, deleted disclosure correction, historical record created from today's page. **Cheapest honest falsification:** replay an immutable offline fixture with later publication and revision; require explicit abstention if source availability is unknown. Later provider spike must recover original/revised versions and timestamps, not only current values. **Contingency:** label retrospective context honestly, preserve dated snapshots and unknown availability, restrict causal replay claims while retaining all domain experiences. Trace: DR-002/007/009, G10; fund lab publication-cutoff cases.

## Decision order

Resolve use/entitlement and actual historical fields before polishing live-data claims. Then choose a bounded cross-market/on-chain universe, estimate collection/runtime load and price the actual horizon. This research does not change the owner's target, authorize external work, clear any gate, certify compliance or establish that the project cannot be built.

Source IDs resolve to exact URLs, dates, web references, reading depths and failures in `data_cost_sources.json`. Pages were reviewed selectively; entire contracts/pricing feature catalogs were not audited.
