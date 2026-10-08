# TEFAS / borsapy provider spike — 2026-10-06

Backlog: T04 (provider interfaces and spike reports). Gate: G03 (fund history). Scope: DEC-024, Turkish funds only.

Updated later the same day with a full read of borsapy's fund-related code and a check of one KAP monthly portfolio report. Both are described below.

**Path maintenance on 2026-10-08:** references to local files and reproduction
locations below use the canonical repository-root `raw/` layout. The provider
findings and dated results remain the original research record. Files were
relocated without changing raw bytes or embedded provenance; ignored legacy
symlinks preserve the old paths. See
[local raw data layout](../../../docs/notes/local-raw-data-layout.md).

## Short answer

- **Only the unit price (NAV) is dated day by day.** TEFAS returns one row per business day for a rolling 5-year window. In the sample, TEFAS dates each price one business day after its valuation date: the KAP report's September month-end price equals TEFAS's 1 October row, and its August month-end price equals the 1 September row.
- **Everything else from TEFAS is an undated "latest" snapshot.** That covers fund size, units outstanding, investor count, market share, category, category rank, period returns and the profile fields.
- **TEFAS writes 0 where it has no price.** A price of 0 appears in history rows before a fund starts and after its price stops, and as the latest price. On 2026-10-06 133 of 2,133 funds had a price of 0; only 21 of them are in SPK's list of 131 funds ordered liquidated on 17 September, the rest are mostly special-purpose funds not traded on TEFAS. Read as a price, 0 would give a return of -100% and a false match between two zeros.
- **Category rank and category size inside the history rows look dated but aren't.** Both funds show the same value on all 1,258 rows, equal to today's snapshot.
- **KAP's monthly portfolio reports give a dated monthly history for the last 12 months.** Each report has the month-end fund total value, units outstanding, month-end price and the monthly average asset mix. They are plain text in a PDF, so a simple parser reads them without an LLM. Investor count is not in them.
- **borsapy adds nothing dated beyond price.** It fills history `FundSize` and `Investors` with placeholders (`NaN` and `0`), its `info["date"]` is always empty, it doesn't expose units outstanding, and it stores nothing.
- **No admissible allocation source from TEFAS.** borsapy reaches it only through a stealth browser that gets past Akamai bot detection, and it stamps every row with today's date.
- **TLS works with certificate verification on.** borsapy's `verify=False` is unnecessary.

## Field by field: TEFAS

Units: prices in TRY per unit (both funds are TL funds), fund size in TRY, returns in percent.

| Field (TEFAS name) | Endpoint | Dated? | Verdict |
|---|---|---|---|
| Unit price (`fiyat`) | `fonFiyatBilgiGetir` history rows | **Yes**, `tarih` per row as `YYYY-MM-DD`, no time or zone | Usable. 5-year window, up to 6 decimals. Dated one business day after valuation (see above). `0` means no price: it starts the series of funds younger than the window (THF: 24 rows, TP2: 28 rows) and follows a price that has stopped (TP2 from 2026-09-17, THF from 2026-09-25). A fund's row for date D was already present at 11:05 on D (one observation). |
| Latest price (`sonFiyat`), daily return % (`gunlukGetiri`) | `fonBilgiGetir` | No | Price equals the newest history row exactly; daily return matches the last two history prices (diff < 0.0001 pp). Both recomputable from dated history. |
| Fund size (`portBuyukluk`), units outstanding (`payAdet`), investors (`yatirimciSayi`), market share (`pazarPayi`) | `fonBilgiGetir` | No | Latest value only. Units × price equals size (relative diff ≤ 1.2e-7), so they're consistent with the price's date, but the API never states it. For funds with a price of 0, size and units are also 0 (or inconsistent, e.g. a size of 0.01 with positive units) while the investor count remains; those values are placeholders or stale and must not date anything. |
| Category (`fonKategori`), rank (`kategoriDerece`), category size (`kategoriFonSay`) | `fonBilgiGetir` | No | Current only. No dated category membership. |
| Rank and category size inside history rows | `fonFiyatBilgiGetir` | **Looks dated, isn't** | One distinct value across 1,258 rows per fund, equal to today's snapshot. Must not be used as history. |
| Period returns 1m, 3m, 6m, YTD, 1y, 3y, 5y (`getiri*`) | `fonGetiriBazliBilgiGetir` (all 2,133 funds) | No | As-of date unknown. Recompute from price history instead. |
| Profile: ISIN, min/max amounts, settlement days (`*Valor`), fees, trading hours, risk 1–7, KAP link, TEFAS status | `fonProfilBilgiGetir` | No | Current only; changes are not dated. |
| Daily fund size, investor and units history | none | Not available | No tested endpoint returns them. Monthly size and units come from KAP (below). |
| Allocation | TEFAS HTML page behind Akamai | borsapy stamps today | Not admissible. Not run. |

## Field by field: KAP monthly portfolio report

One report checked: TTE's "Portföy Dağılım Raporu" for September 2026, published 05.10.2026 13:00:53. Checks are in `kap_pdf_results.json`; the original PDF now lives in repository-root `raw/kap/reports/`.

| Field (report label) | Section | Dated? | Verdict |
|---|---|---|---|
| Fund total value (`Toplam Değer/Net Varlık Değeri`), units outstanding (`Katılma Payı Sayısı`) | I | **Yes**, report month | Units × month-end price equals total value (relative diff 9e-8). |
| Month-end and previous month-end price; monthly, year-to-date and annual change % | II A–E | **Yes**, report month | Both prices equal TEFAS's first row after each month end, exactly. |
| Monthly average asset mix, 20 standard categories (`Aylık Ortalama Portföydeki Menkul Kıymetler Yüzdesi`) | II F | **Yes**, report month | Sums to 100. A monthly average, not a month-end snapshot. |
| Month-end holdings, line by line, with a total per asset class | III | **Yes**, report month | Contains negative rows (10 negative amounts); their meaning is not established. |
| Fund total value table: portfolio, cash, receivables, payables | IV | **Yes**, report month | Total matches section I. |
| Cash in from unit issuance, cash out from redemptions | II I–İ | Report month | Both `0.00`, implausible for a fund of this size: probably not filled in. Unverified. |
| Expenses, corporate actions, legal changes, securities lending | V–VII | Report month | Present; not analyzed. |
| Investor count | none | **Not present** | Only TEFAS's undated snapshot has it. |

Notes for a parser:
- The PDF is generated from Excel and has a text layer (no images), so no OCR or LLM is needed. Labels and values sit in separate text blocks, so lines have to be rebuilt from word positions; `kap_pdf_check.py` shows how.
- Sections I and II write numbers as `1,234.56`, but section IV writes percentages as `100,00 %`. Both conventions appear in one file.
- Download: the KAP disclosure page links one file; `GET https://kap.org.tr/tr/api/file/download/{fileId}` returns the PDF wrapped in a Java-serialized byte array, starting at byte 27.
- Only one management company's report was checked. Others may lay out the file differently.

## KAP batch: ten funds from ten companies

Owner-approved batch, `kap_batch.py`: a year of reports for ten funds covering nine fund types and ten management companies (TTE, AAL, ACC, ADE, AHU, BCO, AHV, DBA, YAK, AC1). Checks are in `kap_batch_results.json`; files now live in repository-root `raw/kap/reports/`.

- **KAP stopped answering partway through.** After 180 successful KAP requests in about 9 minutes, 1.5 s apart, KAP started closing connections without a response (`RemoteProtocolError`), first on file downloads, then on disclosure pages. This is consistent with rate limiting, though the cause isn't confirmed. The script stopped itself after three consecutive failures. 78 of about 123 reports were downloaded (90 files, 122 MB); BCO, AHV and AC1 are missing and AHU is partial. Resume later at a much slower pace.
- **borsapy can't find half of these funds on KAP.** Its fund-id pattern matches only upper-case ids. ACC, AHU, BCO, AHV and AC1 have lower-case ids, so `Fund.get_holdings` would report them as not found. Our scripts now match both.
- **Layouts differ by company.** Three families so far:
  - İş, Ak, Deniz and İstanbul: `I-FONU TANITICI BİLGİLER` and `D-)Toplam Değer/Net Varlık Değeri`. All nine fields parsed for 38 reports (TTE, ADE, DBA). İstanbul uses the same labels, but some values sit on separate lines, so the current line matcher misses them.
  - Ata and Atlas: `1- FONU TANITICI BİLGİLER` and `E. TOPLAM DEĞER/NET VARLIK DEĞERİ`, with an extra `D. FON TUTAR` line and percentages written as `1.80%` or `%2,98`.
  - Yapı Kredi: labels wrapped over two lines, and list letters that include `Ç.`.

  Numbers appear both as `1,234.56` (İş, Ata) and `1.234,56` (Ak, Deniz, Atlas, İstanbul). A parser needs keyword-based labels for each family, both number formats and tolerance for wrapped lines; the current one handles only the first family.
- **Deniz splits each report into two attachments:** the main report and a separate "sales from portfolio" section.
- **Price dating held in 49 of 50 checked months** across TTE, ADE, DBA and ACC. The exception is TTE's year end: its December 2025 month-end price, repeated as January's previous-month price, matches no TEFAS row. ADE's and DBA's year-end prices match. Cause unknown.
- **The cash-flow fields are filled in some months:** non-zero in 3 of 13 TTE reports, 6 of 13 ADE reports and all 12 DBA reports. A zero can't be read as either "not filled in" or "no flow" without more evidence.
- **No report had an investor count.**

Availability: the September report was published five days after month end, so a replay must not use a report before its publish time. KAP's list for the last 365 days had 13 reports for TTE and 12 for AAL. A single request for a 1,825-day window returned HTTP 200 with an empty list, so reaching back more than a year is not established.

## KAP stage 1: the top ten funds plus TP2 (2026-10-07)

Same script at a slower pace (`--pause 6`), for THF, TP2, HLL, TKM, GTL, YLB, HPV, DLY, TI1, TTA and TZL: 316 requests and 142 files, with no failures and no sign of throttling at one request every six seconds. The checks are in `kap_stage1_results.json`.

- **All nine fields parsed** for TP2 (Tera), TKM (TEB), TI1 and TTA (İş), and for DLY's main reports (Deniz). TP2 lacks only the yearly change in its first year.
- **THF (Tera) puts its size and units outstanding on the line after the label,** as İstanbul does. The values are in the PDF, but the line matcher misses them.
- **Nothing parsed for three more layouts:**
  - Ziraat (HLL, HPV, TZL), made with pdf-lib.
  - Garanti (GTL).
  - Yapı Kredi (YLB), as before.
- **Both cash-flow fields were zero in 34 of the 59 reports that have them,** including 8 of TP2's 11, while TP2's units outstanding rose more than fourfold. Month-to-month units outstanding is the usable flow measure; the cash-flow fields are not.

## KAP reports: reading the headline fields (2026-10-07)

`p50k.providers.kap_report.read_headline` finds total value, units outstanding, period-end price, previous price and the period change by keyword in a report's first section. `kap_series.py` runs it over every downloaded PDF and writes monthly series to the gitignored, repository-root `raw/kap/series/`; `kap_series_coverage.json` holds structure and checks only. Result on the 101 funds read (19 companies, 1,255 reports):

- **1,246 of 1,255 reports parse completely.** Five are image-only PDFs with no text layer (they would need OCR). Four are KAP disclosures that carry only trade-section attachments and no headline section.
- **units × price equals total value** within 0.01% in 1,123 of 1,246 reports and within 1% in 1,241. Of the 123 reports above 0.01%, 120 are Ziraat's (a systematic 0.1% to 0.4%), so for Ziraat the total value and price are safer than the unit count.
- **Dating differs by company.** The report's month-end price equals the TEFAS row dated the next business day in 1,014 of 1,053 monthly reports from the other companies (96%). In Ziraat's 120 reports it matches only 4 times; on three Ziraat funds it equals the row one business day earlier.
- **Wording varies:** "Ay Sonu" (monthly), "Dönem Sonu" (Yapı Kredi's September 2026 reports) and "Haftalık" (weekly reports). Number formats mix 1.234,56 and 1,234.56, and a lone separator followed by three digits (1,234) is rejected as ambiguous.
- **KAP's list carries a period code: `AB` for the monthly reports and `HB` for weekly ones** (the PDFs say "Haftalık Pay Fiyatı"). The report list therefore shows a change of reporting cadence without opening a PDF. In the 101 funds read, all 15 Serbest Fon switched to weekly reports in early September 2026 and no other category did, so the switch says nothing about liquidation.

## What borsapy 0.10.1 does with this

Checked by reading all of borsapy's fund-related code (two readers and one reviewer trying to refute the findings; file and line references in `borsapy_fund_inventory.json`), plus the live comparison above.

| borsapy output | Behavior | Evidence |
|---|---|---|
| `Fund.info["date"]` | Always `""` | Code and live |
| `founder`, `manager` | Always `""` | Code and live |
| `weekly_return`, `allocation` | Always `None` | Code and live |
| `price`, `fund_size`, `investor_count`, `risk_value` | Missing becomes `0` (`... or 0`) | Code only; not triggered here because raw values were present |
| Real zeros | Look identical to coerced zeros. AAL's settlement days are genuinely `0`. | Live |
| `history()["FundSize"]`, `["Investors"]` | `NaN` and `0` on every row | Code and live, 1,258 rows × 2 funds |
| `history()` index | Time-zone-naive dates | Live |
| `history()` periods | `'1d'` and `'5d'` return about a week, `'2y'` returns 3 years, an unknown period silently returns 1 month, and a start older than 5 years is silently cut to 5 years | Code |
| Units outstanding, category rank and size | Dropped | Code and live |
| Unknown fund code | Raises `DataNotAvailableError` (TEFAS itself returns HTTP 200 and an empty list) | Live |
| Technical indicators on funds | Those that need high, low or volume return `NaN`; `supertrend` and `heikin_ashi` raise errors | Code |
| `withholding_tax_rate` | Uses today's category for any purchase date | Code |
| Storage | None: an in-memory cache only. Daily history has to be collected by us. | Code |
| TLS | `verify=False`; urllib3 insecure-request warnings disabled at import | Code |
| Allocation | Scrapling `StealthyFetcher` past Akamai; `Date = datetime.now()`; rows with weight ≤ 0 dropped | Code; deliberately not run |
| KAP holdings (`Fund.get_holdings`) | Reaches reports from the last 365 days through `period='YYYY-MM'`, but the output has no date column and silently falls back to the latest report when the month isn't found. Its parser sends the PDF text to an LLM through OpenRouter; the source does not establish the cost. | Code; not run |
| KAP report list and PDFs | A private helper lists the last 365 days of reports with publish date, year and month. The PDFs download without any key or LLM. | Code; the PDF was fetched directly in this spike |
| KAP fund id lookup | Matches only upper-case ids, so it fails for funds whose KAP id is lower-case: 5 of the 10 batch funds | Code and live |
| Fund material events, prospectus changes | No path: borsapy's KAP provider covers listed stocks only | Code |
| `Fund.tweets` | Needs logged-in X session cookies | Code; not admissible |

## Correction: zero prices dated 133 snapshots

The first version of the snapshot collector (`p50k.jobs.fund_snapshots`) treated a price of 0 as a real price. For the 133 funds whose price is 0, the snapshot price (0) equalled the newest history price (0), so the collector dated all 133 snapshots as of 2026-10-06. That was wrong: a placeholder cannot date anything. Fixed on 2026-10-07: a price of 0 is now `None` in the client, a snapshot is dated only when its price is positive and equals the newest positive dated price, and the saved price files hold `null` instead of 0. The 133 stored rows were corrected to "unknown" (raw TEFAS rows kept; a backup of the database was taken first).

## What this means for the funds-phase anomalies

| Entry | Data status after this spike |
|---|---|
| AN-FND-001 NAV/category divergence | Price side is dated daily. Peer side is not: there is no dated category membership, and today's membership leaves out closed funds such as AAK (survivorship). Needs a decision on how to build peer sets. |
| AN-FND-002 net-flow estimate | Monthly for the last 12 months: change in KAP units outstanding × price. Daily: disabled until our own snapshot series exists. The fund-accounting lab's caveats about cash timing still apply, and 11 monthly changes are fewer than the default 20-observation baseline. |
| AN-FND-003 investor count change | Disabled. Investor counts are in neither TEFAS history nor the KAP reports; only daily collection from now on can build them. |
| AN-FND-004 allocation shift | Monthly for the last 12 months from KAP: section II F (monthly average) or the section III totals (month-end). Each report is usable from its publish time, about a week after month end. TEFAS path not admissible. |
| AN-FND-005 access/regulatory event | No borsapy path. Needs our own KAP adapter for fund disclosures. |
| AN-DQ-001 / AN-DQ-002 | An unknown or retired code returns HTTP 200 with an empty list and no error, and so does an unsupported KAP window. Empty must not be read as "nothing happened"; codes have to be checked against the fund list. A price of 0 is a placeholder: it must be treated as missing, and a price that stops (a series that turns to 0) is itself an event to surface. |

## Provider spike template

**Provider / endpoint / SDK / exact version:** TEFAS JSON API at `https://www.tefas.gov.tr/api/funds/`: `fonBilgiGetir`, `fonProfilBilgiGetir`, `fonFiyatBilgiGetir` (periyod 60 = 5 years) and `fonGetiriBazliBilgiGetir` (all investment funds), all POST with a JSON body. The site is operated by Takasbank (certificate subject `www.takasbank.com.tr`). KAP: the fund page from TEFAS's `kapLink`; `GET https://kap.org.tr/tr/api/disclosure/filter/FILTERYFBF/{fundId}/8aca490d502e34b801502e380044002b/365`; the disclosure page `GET https://kap.org.tr/tr/Bildirim/{disclosureIndex}`; and the file `GET https://kap.org.tr/tr/api/file/download/{fileId}`. borsapy 0.10.1 from PyPI: `_providers/tefas.py` sha256 `1f03fe2a21e09ddffdc6345d34d208fe73d0ce5e17918ee07c8a2c4a377fe503`, `fund.py` sha256 `161bf7c7f9850f2c29feb74a7e13f40bf65aadde20c95701f092590ea5d5bda5`. httpx 0.28.1, certifi 2026.06.17, OpenSSL 3.6.3, Python 3.13.13, pymupdf 1.27.2.3.

**Date and deployment region:** 2026-10-06, 19:07 to 19:55 Europe/Istanbul, run from a local developer machine.

**Entitlement document and allowed use:** None reviewed. TEFAS/Takasbank and KAP terms were not read. Raw responses and the PDF are kept out of git.

**Credential source:** None needed; public endpoints.

**Request shape and rate policy:** `spike.py` made one run of 13 requests, 1.5 s apart, no retries, certificate verification on, borsapy's default browser User-Agent with a JSON content type. An earlier run at 19:07 made 10 requests using AAK; it was discarded because AAK no longer exists. borsapy's parsing was run on the same raw responses with its network access blocked, so the comparison is exact. Three more KAP requests were made by hand, with the owner's approval for the PDF: the September report's disclosure page, its PDF (4.35 MB) and the 1,825-day list. That makes 26 requests for the day.

**Sample response path + hash:** responses originally lived in `raw/` next to this
file. Their canonical locations after the 2026-10-08 relocation are
repository-root `raw/tefas/responses/` and `raw/kap/reports/`, gitignored and not
sanitized. Every `spike.py` request's URL, payload, status, size and SHA-256 is in
`results.json` under `requests`. The PDF's size and SHA-256 are in
`kap_pdf_results.json`. Historical path strings in those records and in the moved
mixed-provider `requests.json` are preserved; local legacy aliases resolve them.

**Actual observed fields, units, publication/availability times:** See the field tables. Today's price (2026-10-06) was already available at 19:09 Istanbul time on the same day; that is one observation, not an established publication schedule. The September KAP report was published on 5 October. KAP `publishDate` has the form `DD.MM.YYYY HH:MM:SS` with no offset; reading it as Europe/Istanbul is an assumption to verify.

**History depth and missing values:** 1,258 rows per fund, 2021-10-06 to 2026-10-06, the API's 5-year maximum. Ascending order, no duplicate dates, no weekend rows, no missing or non-positive prices. Eight gaps of 5–6 days look like public-holiday closures; not checked against an official calendar. Both funds have identical date sets. KAP: 12–13 monthly reports in the last 365 days.

**Venue/chain coverage:** TEFAS investment funds (YAT): 2,133 listed on 2026-10-06. Pension funds (EMK) not tested. Funds sampled: TTE (İş Portföy BIST technology equity fund) and AAL (Ata Portföy TL money-market fund).

**Corporate-action / NAV / finality behavior:** A price can stop: TP2's TEFAS price stops on 2026-09-17 and THF's on 2026-09-25, after the liquidation order, and 110 of the 131 funds in the order still show a price today. In this sample, TEFAS dates each price one business day after its valuation date: the KAP report's month-end prices for August and September equal TEFAS's 1 September and 1 October rows exactly. Fund closures leave no trace: AAK returns the same response as a code that never existed. No splits or renames were observed in the sample.

**Failure, stale-response and retry tests:**
- Unknown code (AAK, retired; ZZZZZ, never existed): HTTP 200, `{"errorCode":null,"errorMessage":null,"resultList":[]}`.
- KAP report list with a 1,825-day window: HTTP 200 and an empty list.
- TLS negative control: a context that trusts no CA fails with `SSLCertVerificationError` for both hosts, so certificate errors surface.
- Not tested: WAF or empty-body responses (borsapy's code says they occur), rate limits, stale-data detection, retries.

**Results:** DOCUMENTED: borsapy docstrings. CODE_INSPECTED: yes, all fund-related code in borsapy 0.10.1. LIVE_TESTED: yes for the TEFAS snapshot, profile, history and all-funds list for two funds, the KAP report list for two funds, and one KAP report PDF. RIGHTS_APPROVED: no.

**Detector capabilities enabled:** None yet. Dated daily prices support the price side of AN-FND-001 and the data-quality checks. Parsed KAP reports would support monthly AN-FND-002 and AN-FND-004 for the last 12 months.

**Detector capabilities explicitly disabled:** AN-FND-003. Daily AN-FND-002 until our own snapshot series exists. AN-FND-004 through TEFAS. Use of history-row rank or category size as history.

## TEFAS admission cases (from the template)

| Case | Result |
|---|---|
| Pinned version; certificate verification on; bad certificates surface an error | **Pass** for a direct client: verified TLS works and the negative control fails. **Fail** for borsapy as shipped (`verify=False`). Version and hashes recorded above. |
| Raw allocation date preserved; missing date quarantined, never replaced by today | **Fail** for borsapy (always today). TEFAS allocation not admissible. KAP reports carry their own report month and publish time. |
| Historical AUM and investor placeholders stay missing | Placeholders confirmed live. They must be normalized to missing, as `reference/engine.py` `normalize_borsapy_fund_history` already does. |
| Access, storage, analytics, display and model-processing rights confirmed | **Not done.** |

## Open issues

1. Data rights for TEFAS and KAP (owner).
2. Daily snapshot collector: built as `p50k.jobs.fund_snapshots` and first run on 2026-10-06 for the 1,071 funds traded on TEFAS. It dates a snapshot only when `sonFiyat` equals the newest dated price. Installing the daily timer (`ops/systemd/`) needs the owner's go-ahead.
3. KAP PDF parsing: solved for the headline fields (see the section above). Not read yet: the holdings tables (section III) and the asset mix, whose negative rows still need explaining (issue 8).
4. KAP throttling: one request every six seconds ran 316 requests without a failure (2026-10-07); 1.5 seconds was cut off after 180 requests in about 9 minutes.
5. Price dating held in 49 of 50 months across four funds. Explain TTE's year-end exception, check funds holding foreign assets, and check when prices publish.
6. How to build peer sets for AN-FND-001 without dated category membership.
7. When and by whom the KAP cash-flow fields are filled.
8. What the negative rows in KAP holdings tables mean, before computing allocation from section III.
9. Whether KAP reports older than 365 days can be listed.
10. Pension funds (EMK) are untested. TEFAS's tolerance for a full-universe daily run is untested beyond the first run.

## Reproduce

From the repo root, with borsapy 0.10.1 and httpx installed:

```sh
python research/spikes/2026-10-06-tefas/spike.py
```

It makes about 13 requests and rewrites `results.json` and local responses under
repository-root `raw/tefas/responses/` and `raw/kap/reports/`. Live values change
daily, so results will differ in values but should not differ in structure. This
network reproduction command was not executed for the file relocation.

Then:

```sh
python research/spikes/2026-10-06-tefas/kap_pdf_check.py
```

It checks the newest KAP report in `spike.py`'s saved list. It reads the PDF from
repository-root `raw/kap/reports/` if present, otherwise downloads it (2 requests).
It needs pymupdf, which borsapy installs, and writes `kap_pdf_results.json`.

The ten-fund batch:

```sh
python research/spikes/2026-10-06-tefas/kap_batch.py download
python research/spikes/2026-10-06-tefas/kap_batch.py check
```

`download` reuses files already in repository-root `raw/kap/reports/` and stops
after three consecutive failures; mind KAP's throttling. `check` is offline and
writes `kap_batch_results.json`. Neither command was executed for the relocation;
existing research result files are unchanged.
