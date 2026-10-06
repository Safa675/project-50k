# TEFAS / borsapy provider spike — 2026-10-06

Backlog: T04 (provider interfaces and spike reports). Gate: G03 (fund history). Scope: DEC-024, Turkish funds only.

## Short answer

- **Only the unit price (NAV) is genuinely dated.** TEFAS returns one row per business day, with a date, for a rolling 5-year window.
- **Everything else is an undated "latest" snapshot.** That covers fund size, units outstanding, investor count, market share, category, category rank, period returns and the profile fields.
- **Category rank and category size inside the history rows look dated but aren't.** Both funds show the same value on all 1,258 rows, equal to today's snapshot.
- **borsapy fills history `FundSize` and `Investors` with placeholders** (`NaN` and `0`) on every row, and its `info["date"]` is always empty.
- **No admissible allocation source from TEFAS.** borsapy reaches it only through a stealth browser that gets past Akamai bot detection, and it stamps every row with today's date. KAP's monthly portfolio reports are dated, but their contents are PDFs.
- **TLS works with certificate verification on.** borsapy's `verify=False` is unnecessary.

## Field by field

Units: prices in TRY per unit (both funds are TL funds), fund size in TRY, returns in percent.

| Field (TEFAS name) | Endpoint | Dated? | Verdict |
|---|---|---|---|
| Unit price (`fiyat`) | `fonFiyatBilgiGetir` history rows | **Yes**, `tarih` per row as `YYYY-MM-DD`, no time or zone | Usable. 5-year window, up to 6 decimals. |
| Latest price (`sonFiyat`), daily return % (`gunlukGetiri`) | `fonBilgiGetir` | No | Price equals the newest history row exactly; daily return matches the last two history prices (diff < 0.0001 pp). Both recomputable from dated history. |
| Fund size (`portBuyukluk`), units outstanding (`payAdet`), investors (`yatirimciSayi`), market share (`pazarPayi`) | `fonBilgiGetir` | No | Latest value only. Units × price equals size (relative diff ≤ 1.2e-7), so they're consistent with the price's date, but the API never states it. |
| Category (`fonKategori`), rank (`kategoriDerece`), category size (`kategoriFonSay`) | `fonBilgiGetir` | No | Current only. No dated category membership. |
| Rank and category size inside history rows | `fonFiyatBilgiGetir` | **Looks dated, isn't** | One distinct value across 1,258 rows per fund, equal to today's snapshot. Must not be used as history. |
| Period returns 1m, 3m, 6m, YTD, 1y, 3y, 5y (`getiri*`) | `fonGetiriBazliBilgiGetir` (all 2,133 funds) | No | As-of date unknown. Recompute from price history instead. |
| Profile: ISIN, min/max amounts, settlement days (`*Valor`), fees, trading hours, risk 1–7, KAP link, TEFAS status | `fonProfilBilgiGetir` | No | Current only; changes are not dated. |
| Fund size, investor and units **history** | none | Not available | No tested endpoint returns them. |
| Allocation | TEFAS HTML page behind Akamai | borsapy stamps today | Not admissible. Not run. |
| Allocation and holdings | KAP "Portföy Dağılım Raporu", monthly | **Yes**: publish timestamp plus year and month | Dated, but contents are PDFs (not downloaded or parsed). Published 3 to 10 days after month end. |

## What borsapy 0.10.1 does with this

| borsapy output | Behavior | Evidence |
|---|---|---|
| `Fund.info["date"]` | Always `""` | Code and live |
| `founder`, `manager` | Always `""` | Code and live |
| `weekly_return`, `allocation` | Always `None` | Code and live |
| `price`, `fund_size`, `investor_count`, `risk_value` | Missing becomes `0` (`... or 0`) | Code only; not triggered here because raw values were present |
| Real zeros | Look identical to coerced zeros. AAL's settlement days are genuinely `0`. | Live |
| `history()["FundSize"]`, `["Investors"]` | `NaN` and `0` on every row | Code and live, 1,258 rows × 2 funds |
| `history()` index | Time-zone-naive dates | Live |
| Units outstanding, category rank and size | Dropped | Code and live |
| Unknown fund code | Raises `DataNotAvailableError` (TEFAS itself returns HTTP 200 and an empty list) | Live |
| TLS | `verify=False`; urllib3 insecure-request warnings disabled at import | Code |
| Allocation | Scrapling `StealthyFetcher` past Akamai; `Date = datetime.now()`; rows with weight ≤ 0 dropped | Code; deliberately not run |
| KAP holdings | Downloads PDFs and parses them with a paid LLM (OpenRouter) | Code; not run |

## What this means for the funds-phase anomalies

| Entry | Data status after this spike |
|---|---|
| AN-FND-001 NAV/category divergence | Price side is dated. Peer side is not: there is no dated category membership, and today's membership leaves out closed funds such as AAK (survivorship). Needs a decision on how to build peer sets. |
| AN-FND-002 net-flow estimate | Disabled. No size or units history. Collecting the undated snapshot daily would build one; units outstanding allow a more direct flow estimate (change in units × price) than the AUM residual, though the fund-accounting lab's caveats about actual cash timing still apply. |
| AN-FND-003 investor count change | Disabled. Same as above: needs our own daily snapshot series. |
| AN-FND-004 allocation shift | TEFAS path not admissible. KAP monthly reports are the dated alternative, giving monthly cadence with about a week of lag, after a decision on how to parse the PDFs. |
| AN-FND-005 access/regulatory event | Not tested. Needs KAP disclosure types other than portfolio reports. |
| AN-DQ-001 / AN-DQ-002 | An unknown or retired code returns HTTP 200 with an empty list and no error. Detection has to check codes against the fund list. |

## Provider spike template

**Provider / endpoint / SDK / exact version:** TEFAS JSON API at `https://www.tefas.gov.tr/api/funds/`: `fonBilgiGetir`, `fonProfilBilgiGetir`, `fonFiyatBilgiGetir` (periyod 60 = 5 years) and `fonGetiriBazliBilgiGetir` (all investment funds), all POST with a JSON body. The site is operated by Takasbank (certificate subject `www.takasbank.com.tr`). KAP: the fund page from TEFAS's `kapLink`, then `GET https://kap.org.tr/tr/api/disclosure/filter/FILTERYFBF/{fundId}/8aca490d502e34b801502e380044002b/365`. borsapy 0.10.1 from PyPI: `_providers/tefas.py` sha256 `1f03fe2a21e09ddffdc6345d34d208fe73d0ce5e17918ee07c8a2c4a377fe503`, `fund.py` sha256 `161bf7c7f9850f2c29feb74a7e13f40bf65aadde20c95701f092590ea5d5bda5`. httpx 0.28.1, certifi 2026.06.17, OpenSSL 3.6.3, Python 3.13.13.

**Date and deployment region:** 2026-10-06, 19:09 Europe/Istanbul, run from a local developer machine.

**Entitlement document and allowed use:** None reviewed. TEFAS/Takasbank and KAP terms were not read. Raw responses are kept out of git.

**Credential source:** None needed; public endpoints.

**Request shape and rate policy:** One run of 13 requests, 1.5 s apart, no retries, certificate verification on, borsapy's default browser User-Agent with a JSON content type. An earlier run at 19:07 made 10 requests using AAK; it was discarded because AAK no longer exists. borsapy's parsing was run on the same raw responses with its network access blocked, so the comparison is exact.

**Sample response path + hash:** `raw/` next to this file, gitignored and not sanitized. Every request's URL, payload, status, size and SHA-256 is in `results.json` under `requests`.

**Actual observed fields, units, publication/availability times:** See the field table. Today's price (2026-10-06) was already available at 19:09 Istanbul time on the same day. That is one observation, not an established publication schedule. KAP `publishDate` has the form `DD.MM.YYYY HH:MM:SS` with no offset; reading it as Europe/Istanbul is an assumption to verify.

**History depth and missing values:** 1,258 rows per fund, 2021-10-06 to 2026-10-06, the API's 5-year maximum. Ascending order, no duplicate dates, no weekend rows, no missing or non-positive prices. Eight gaps of 5–6 days look like public-holiday closures; not checked against an official calendar. Both funds have identical date sets.

**Venue/chain coverage:** TEFAS investment funds (YAT): 2,133 listed on 2026-10-06. Pension funds (EMK) not tested. Funds sampled: TTE (İş Portföy BIST technology equity fund) and AAL (Ata Portföy TL money-market fund).

**Corporate-action / NAV / finality behavior:** Not established whether `tarih` is the valuation date or the date the price applies to orders. Fund closures leave no trace: AAK returns the same response as a code that never existed. No splits or renames were observed in the sample.

**Failure, stale-response and retry tests:**
- Unknown code (AAK, retired; ZZZZZ, never existed): HTTP 200, `{"errorCode":null,"errorMessage":null,"resultList":[]}`.
- TLS negative control: a context that trusts no CA fails with `SSLCertVerificationError` for both hosts, so certificate errors surface.
- Not tested: WAF or empty-body responses (borsapy's code says they occur), rate limits, stale-data detection, retries.

**Results:** DOCUMENTED: borsapy docstrings. CODE_INSPECTED: yes, `tefas.py`, `fund.py` and `kap_holdings.py` of 0.10.1. LIVE_TESTED: yes for snapshot, profile, history, the all-funds list and the KAP report list, two funds. RIGHTS_APPROVED: no.

**Detector capabilities enabled:** None yet. Dated price history supports the price side of AN-FND-001 and the data-quality checks.

**Detector capabilities explicitly disabled:** AN-FND-002 and AN-FND-003 until our own dated snapshot series exists. AN-FND-004 through TEFAS. Use of history-row rank or category size as history.

## TEFAS admission cases (from the template)

| Case | Result |
|---|---|
| Pinned version; certificate verification on; bad certificates surface an error | **Pass** for a direct client: verified TLS works and the negative control fails. **Fail** for borsapy as shipped (`verify=False`). Version and hashes recorded above. |
| Raw allocation date preserved; missing date quarantined, never replaced by today | **Fail** for borsapy (always today). TEFAS allocation not admissible. KAP reports carry their own dates. |
| Historical AUM and investor placeholders stay missing | Placeholders confirmed live. They must be normalized to missing, as `reference/engine.py` `normalize_borsapy_fund_history` already does. |
| Access, storage, analytics, display and model-processing rights confirmed | **Not done.** |

## Open issues

1. Data rights for TEFAS and KAP (owner).
2. Whether to start a daily snapshot collector for size, units and investors (owner and developer). A safe as-of rule: accept a snapshot's date only when `sonFiyat` equals the newest history price, otherwise record as-of unknown.
3. How to read KAP portfolio-report PDFs: a deterministic parser, or an LLM with budget approval (owner).
4. What `tarih` means (valuation date or order date) and when prices publish: check TEFAS/SPK documentation or repeat observations.
5. How to build peer sets for AN-FND-001 without dated category membership.
6. Pension funds (EMK), WAF behavior and rate limits are untested.

## Reproduce

From the repo root, with borsapy 0.10.1 and httpx installed:

```sh
python research/spikes/2026-10-06-tefas/spike.py
```

It makes about 13 requests and rewrites `results.json` and `raw/`. Live values change daily, so results will differ in values but should not differ in structure.
