# Project 50K — Data Requirements & Provider Matrix

**Version:** 0.4 audit revision · **Prepared:** 2026-10-02
**Status:** implementation specification / not a claim of deployed functionality.

## 1. Provider status vocabulary
`DOCUMENTED`: publisher describes the capability. `CODE_INSPECTED`: wrapper source inspected. `LIVE_TESTED`: a successful dated response captured in the deployment environment. `RIGHTS_APPROVED`: written scope permits this use. These are independent states. No provider is marked live-tested or rights-approved in this package.

## 2. Field-level provider matrix
| Domain | Candidate / route | Needed fields / cadence | Review and decision | Failure behavior |
|---|---|---|---|---|
| BIST | borsapy adapter for research; licensed distributor for release | Final OHLCV bars, timestamps, volume unit, corporate actions, benchmarks | DOCUMENTED/README reviewed; BIST implementation not independently inspected here. TradingView session access is not a business data license [S01,S05]. | Replay only with permission; never silently replace by another venue. |
| Turkish funds | TEFAS via isolated adapter | Published NAV/date, AUM/date, investors/date, category, allocation as-of/publication | borsapy provider inspected [S06]. Latest detail and price history have different capabilities. | Disable flow/investor detector on missing historical fields. |
| Fund allocation | Adapter around `dagilimSiraliGetirT` where permitted | Asset-type code, weight, date, fund identity | Wrapper source supports endpoint; schema/labels/rate limits need local test [S06]. | Preserve unknown codes; do not guess category; negative weights may be meaningful. |
| Fund holdings | KAP reports / issuer disclosures | Security identifier, weight, reporting date, publication time | Separate ingestion spike; no claim of live complete coverage. | Show last disclosed date; no inferred current exposure. |
| KAP | Authorized KAP publication API / approved vendor | Stable disclosure ID, issuer/fund IDs, title, publication, correction/version | Official REST route documented: distribution contract, MKK IP authorization and API key; selected issuer/fund scope supported [S34]. Entitlement not obtained. | Respect authorized acquisition route and blocked/corrected disclosures; no `no disclosure` conclusion during outage. |
| SPK | Official announcements; web services only after schema discovery | Exact affected entities, decision date, publication date, effective date | Announcements verified; help page available but endpoint schema not recovered [S02–S04,S07]. | Admin-curated source link with entity review; do not invent API paths. |
| US prices | Alpaca candidate | Bars, feed, venue coverage, adjustments, timestamp | Basic real-time IEX is not consolidated market volume [S08]. Contract needed for retail redistribution. | Label IEX/delayed; reduce stream universe; never silently mix SIP/IEX. |
| US filings | SEC submissions + companyfacts | CIK, accession, filed/accepted time, periods, taxonomy, units | Official docs reviewed [S09]. No CORS: fetch server-side. | Cache and respect fair-access policy; retain original filing contexts. |
| Crypto market | Binance spot candidate; BtcTurk alternative pending doc verification | Venue/pair, final bars, base/quote volume, close time | Binance docs reviewed [S10]; no account/trading permissions needed by product. | Reconnect with overlap/backfill/dedup; no multi-venue price merge by ticker alone. |
| Crypto catalog | CoinGecko | Provider ID, chain/contract identity, market ranking snapshot | Docs reviewed [S14]; catalog only until entitlement confirmed. | Admin selection snapshot; do not call hardcoded list `current top 100`. |
| EVM | Managed JSON-RPC or indexed provider | chain ID, block hash/time, tx/log IDs, token decimals, removed/finality | JSON-RPC reviewed [S11]. Raw RPC cannot discover all beneficial owners. | Bounded contracts/block ranges; unfinalized not eligible for broadcast. |
| Solana | Managed RPC / indexed provider | signature, slot, commitment, mint, token accounts, balances | `getTokenLargestAccounts` returns top 20 accounts [S12]. | Explicit partial coverage; distinguish mint accounts from wallet owners. |
| DEX pools | DEX Screener candidate | chain/pair address, liquidity, price, timestamp | API reviewed [S13]; aggregate USD liquidity may fall merely because prices fall. | No historical pool-drain inference from a single snapshot. |
| News | Contracted finance news or approved retrieval tool | title, canonical URL, issuer, publication/retrieval, corrections | AA/Reuters/Bloomberg-type sources are candidates, not licensed integrations. Web research [S19] is not an unrestricted news wire. | Headline/link/minimal permitted excerpt only; do not bypass paywalls or store full text without rights. |

## 3. Borsapy-specific acceptance spike
Do not assume a public API method's DataFrame columns imply populated data. Inspect sample responses and normalization. In the inspected TEFAS implementation, history fills `FundSize` with NaN and `Investors` with zero for compatibility; normalize both to missing for this path [S06]. `fund.info` supplies latest values, not a reconstructed time series. Source availability date can be absent: store `retrieved_at` separately and mark `as_of_unknown`; never use it as historical proof.

Try authorized, low-rate samples for two funds, two valuation dates and one allocation change. Confirm symbols, decimal units, date buckets, unknown category codes, missing values, response errors and access rights. Do not disable TLS verification to make a wrapper work. Pin an audited version/commit and keep networking isolated. `pytefas` is an unverified alternative until its current source and response behavior are inspected; no fallback is presumed safe just because it has a similar name.

Current S06 source sections inspected on 2026-10-02 initialize TEFAS transport with certificate verification disabled and replace an allocation-date parsing failure with the local current date. Direct wrapper instantiation is therefore not an admitted adapter. Require reviewed certificate-verifying transport, surfaced certificate errors, preservation of the raw source date, and rejection/quarantine of malformed or missing allocation dates. Retrieval time cannot replace a source valuation date. Test these behaviors against the pinned source before using any dated allocation-change signal. The historical blob hash reported in v0.3 was not independently recovered in this audit; record an immutable commit/content hash in the integration spike.

## 4. Data requirements
- **DR-001 Identity:** internal UUID; asset type and market; ISIN/CIK/contract/mint where applicable; provider aliases with valid-from/to. BTC, wrapped BTC and exchange trading pairs must remain separate entities/relationships.
- **DR-002 Temporal provenance:** event/valuation time, source publication time, first observation, ingestion time, revision, timezone and source URL/ID. Store UTC; render Istanbul; use exchange calendars for session logic.
- **DR-003 Market bars:** open/end, interval, OHLC, volume and unit, feed/venue, currency, adjusted state, completeness and correction version. No provisional bars for P0 detection.
- **DR-004 Fund observations:** NAV, AUM, investor count and allocation each carry their own valuation dates. No last-price date implicitly attached to latest AUM.
- **DR-005 Missingness:** `null` + reason (`unavailable`, `not_applicable`, `source_failed`, `placeholder`, `not_yet_published`); never zero-fill numerical evidence.
- **DR-006 Rights:** per source, record display, processing/non-display, history retention, redistribution, model-processing and attribution status. Publication jobs must enforce permitted uses.
- **DR-007 Point in time:** choose only versions eligible at a specified cutoff. Unknown historical availability means no causal replay claim.
- **DR-008 Coverage:** searchable, priced, detected, contextualized and on-chain-covered flags are separate and queryable.
- **DR-009 Lineage:** each signal points to input record IDs/checksums and config hash. Raw content retention depends on rights and privacy.
- **DR-010 Normalization QA:** reject impossible OHLC relationships, duplicate bars, unsorted timestamps, invalid decimals, unknown volume units and inconsistent sessions.
- **DR-011 Financials:** period start/end, consolidated/standalone, unit scale, reporting currency, inflation accounting and restatement version. TTM must not sum cumulative quarterly reports twice.
- **DR-012 Chain finality:** transaction/block identity and status are durable; reorgs invalidate dependent signals/events and suppress unsent alerts.

## 5. Scheduling — proposed defaults, not provider SLAs
BIST/US: process completed 5- or 15-minute bars after permitted delivery lag. Crypto: completed five-minute bars and bounded finalized chain scans. Funds: poll for newly published observations, not synthetic intraday prices. Official disclosures: permitted polling cadence with cache/ETag. Worker owns scheduling; API page loads never fan out to upstreams.

Freshness = expected source publication/delivery schedule versus last successful observation, not `now minus last exchange trade` across weekends. Explicit states: `LIVE`, `DELAYED`, `DAILY_PUBLISHED`, `REPLAY`, `SIMULATED`, `STALE`, `UNAVAILABLE`.

## 6. Load and storage sizing
Illustrative capacity, not measurement: 20 equities × 80 bars/day × 5 fields × 30 days = 240,000 numeric field observations before metadata. Market events should be computed once per asset/window, then reused by all users. Full-chain scans and per-user regeneration are out of scope.

Capture storage size and request counts during the first spike; set per-provider concurrency one initially, honor Retry-After, exponential backoff with jitter, circuit breaker and bounded retries. Persistent quotas, not only an in-process counter. Retain provider credit balance and last error in admin.

## 7. Data fixture policy
`fixtures/` contains synthetic test evidence only; it must never appear as a real event for a named issuer. Permission-cleared historical packs need a manifest with provenance, availability timestamps and licensing record. A historical label discovered today can be a future outcome label, never evidence the detector had then.

## 8. Integration release checklist
For each candidate: official documentation → entitlement → one dated sample → semantic validation → failure test → persisted capability/rights record → deployment smoke test. Success downloading a sample does not establish legal permission. See `templates/PROVIDER_SPIKE.md` and document 25.

## 2026-10-03 risk review

Accessible responses, usable dated fields and permission for this use are separate capabilities; see data/cost risk review. Current synthesis: reports/RISK_REVIEW.md; register: research/risk_review/RISK_REGISTER.json.

## Problem solution and market research continuation 3 October 2026

No complete admitted historical market dataset was obtained in this task. The frequency map specifies required exposures for 28 unchanged rules. Retain missing/excluded records separately and point-in-time revisions; official aggregates and other studies cannot substitute for eligible detector inputs. See `reports/PROBLEM_MARKET_RESEARCH.md` and the linked source-depth appendices.
