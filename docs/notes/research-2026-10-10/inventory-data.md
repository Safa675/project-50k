# Project 50K data inventory and source evaluation (2026-10-10, about 12:40 Istanbul)

## Bottom line

- **The local real data is enough to build the shared core tonight.** It has 5-year daily prices for 2,022 funds and one full cross-section of fund size, units and investors for 1,071 TEFAS-traded funds as of 2026-10-09. It also has 12 months of parsed KAP monthly reports for 101 funds and one SPK liquidation bulletin.
- **In TEFAS's current API only the price is dated.** The repo spike and the 2026 rewrite note in tefas-crawler agree. The legacy `BindHistory*` endpoints, which gave dated size, investors and allocation for every fund, are retired.
- **One lead could change that.** SPK's "Portföy Değerleri" page says fund amount, units, investor count, portfolio distribution and unit price can be viewed daily, through TEFAS or a "Portföy Değerleri Web Servisi". This is unverified. A one-hour spike tonight decides it.
- **Forward snapshots cannot add a new dated day before the freeze.** TEFAS publishes no weekend rows. The scheduled task first runs on Monday 12 October at 21:00.
- **No official machine-readable list of past liquidations was found.** One can be built from the SPK bulletin archive, which goes back to 2005, and from KAP's "Tasfiye Olmuş Fonlar" list.
- **Data rights are unreviewed for TEFAS, KAP and SPK.** Only the EVDS terms were read. Both B2B stories sell derived data, so a rights review blocks any sale.

## 1. Local inventory (this machine, read-only)

All counts were made with `.venv\Scripts\python.exe`. SQLite files were opened with `mode=ro&immutable=1` and nothing was modified.

| Location | Count and size | Date range | Notes |
|---|---|---|---|
| `raw/tefas/prices/` | 2,022 JSON files, 48.7 MB; 1,673,412 non-null daily prices | First rows 2021-10-07 → 2026-09-08; every file ends 2026-10-07; all retrieved 2026-10-07 | All `periyod` 60, the 5-year maximum. 656 files have the full 1,258 rows and 157 have ≤250 rows. 27 files end in null: 2 are all-null and 25 series stopped during 2026. 2,133 − 2,022 = 111 listed funds have no file (reason unverified). |
| `raw/kap/reports/` | 106 fund folders (5 without PDFs); 1,342 PDFs; 1,769 files; 668 MB | 102 report lists with 1,267 entries, all fund disclosures, published 2025-10-06 → 2026-10-07 | Median 12 PDFs per fund, maximum 40 (weekly reporters) |
| `raw/kap/series/` | 101 JSON files, 0.6 MB | Last 12 months | Parsed headline fields: 1,246 of 1,255 reports parse (`research/spikes/2026-10-06-tefas/REPORT.md`) |
| `raw/kap/flow-analysis/` | 1 JSON file, 2.7 MB | n/a | Research output |
| `raw/snapshots/fund_snapshots.sqlite3` | `fund_snapshots` 100 rows; `collector_runs` 0 rows | `as_of` 2026-10-06: 94 rows; unknown: 6; all retrieved 2026-10-06 | A 100-fund copy that the demo re-hashes, so it is load-bearing |
| `raw/spk/` | 1 PDF (bulletin 2026/61, 0.2 MB) | 2026-09-17 | |
| `raw/tefas/responses`, `logs`, `price-detectors` | 10, 2 and 1 files | 2026-10-06/07 | Spike responses, download logs, D1–D5 output |
| `raw/research/fund-review-app/` | 397 files | n/a | Sealed bundles |
| `%USERPROFILE%\.local\share\project-50k\fund_snapshots_forward.sqlite3` | `fund_snapshots` 1,073 rows; `collector_runs` 2 rows | `as_of` 2026-10-09: 1,063 rows; unknown (no price): 10; all retrieved 2026-10-10 | Only the 1,071 TEFAS-traded funds were requested. Run 1 (09:32–10:39) dated 263 and stopped after repeated TEFAS failures. Run 2 (10:51–11:54) dated 800 more. |

Other facts:

- **Scheduled task.** The Windows task "P50K fund snapshots" is registered but has never run. Its next run is Monday 2026-10-12 21:00, and it runs on weekdays only.
- **Missing full snapshot.** The full 2,133-fund snapshot of 2026-10-06 exists only on the owner's Linux laptop (`docs/notes/codex-context-2026-10-07.md` §4).
- **No database or LLM code yet.** The repo has no PostgreSQL, Docker Compose or OpenAI code. I searched `pyproject.toml`, `uv.lock`, `frontend/package.json` and `services/**/*.py`.
- **Throughput.** Observed TEFAS speed is about 3.5 s per fund for a snapshot, which takes two requests. That works out to about 1.8 s per request at the 1.5 s pause (derived from `collector_runs`).

## 2. Repository facts that constrain the design

From `research/spikes/2026-10-06-tefas/REPORT.md` and §5 of the codex context:

- **Price 0 means "no price".** A TEFAS price of 0 must be treated as missing.
- **Empty is not "nothing happened".** An unknown or retired fund code returns HTTP 200 with an empty list.
- **Price dating.** A TEFAS price is dated one business day after its valuation date, and the row dated D is present by about 11:05 on D.
- **Undated fields.** Size, units, investors, category and rank are latest-value-only. The rank inside history rows is today's value.
- **KAP report list.** It covers 365 days at most; a longer window returns an empty list.
- **KAP pacing.** A 1.5 s pause was cut off after about 180 requests. A 6 s pause has run thousands without failure.
- **KAP report layouts vary by company.** Ziraat, Garanti and Yapı Kredi are unparsed, five PDFs are image-only, and the cash-flow fields are unreliable.
- **Ziraat reports** are dated one business day earlier than the others against TEFAS.

## 3. External sources

| Source | What it gives | Access, key and cost | Cadence and history | Limits | Rights | Effort |
|---|---|---|---|---|---|---|
| **TEFAS JSON API** (`tefas.gov.tr/api/funds/`: `fonFiyatBilgiGetir`, `fonBilgiGetir`, `fonProfilBilgiGetir`, `fonGetiriBazliBilgiGetir`) | Dated daily price for each fund. Latest size, units, investors, category and profile. Undated period returns for all funds in one request. | POST with a JSON body; no key; free | Price history is a fixed look-back enum with a 5-year maximum (tefas-crawler lists {1,3,6,12,36,60} months; the repo tested 12/36/60). Other fields: today only. | No bulk daily endpoint found: per tefas-crawler "the new backend exposes prices per-fund only", so all-funds means one request per fund. TEFAS failed repeatedly on 10-10. The allocation HTML is behind Akamai and not admissible. | Unreviewed; no terms page found in one search | Already built (`services/p50k/providers/tefas.py`) |
| **SPK Portföy Değerleri page and web service** (`ws.spk.gov.tr/help/index.html`) | SPK says fund amount, units, investor count, portfolio value, distribution and unit price are available "günlük ve konsolide" | Help page exists but its schema did not render, and a guessed swagger path returned 404. Key or registration is unknown. | Unverified | Unverified | Unreviewed | **1 h spike tonight.** If it is dated and historical, it closes G03. |
| **KAP public website JSON** (report list `…/disclosure/filter/FILTERYFBF/{fundId}/{type}/365`, `/tr/Bildirim/{index}`, `/tr/api/file/download/{fileId}`) | Monthly and weekly portfolio reports (PDF) with publish timestamps; the AB/HB period code; fund pages | No key; free; the fund id comes from TEFAS's `kapLink` | Each report about 5 days after month end. Last 365 days only. | 6 s pacing. Fund material-event filters (prospectus changes, liquidation notices) are untested, and borsapy covers stocks only. | Unreviewed. KAP directs high-volume use to its contracted service. | Reports: built. Events: 30-min spike. |
| **KAP publication service (official REST)** | Disclosure feed for selected issuers and funds | A distribution contract plus MKK IP and API-key authorization (`SOURCE_REGISTER.md` S34) | Real time | Contract scope | Contractual | After the event; cost unverified |
| **SPK bulletins** | Liquidation orders, TEFAS trading closures, fund-guide changes, licence and administrative actions | Public PDFs at `spk.gov.tr/data/{opaque-id}/{yyyy}-{nn}.pdf`, found by scraping the yearly index pages. No RSS or API was seen; an email subscription exists. | Irregular: 16 bulletins between 29 Aug and 7 Oct 2026, the latest being 2026/69 of 7 Oct. Archive years go back to 2005; completeness is unverified. | Some pages are images (2026/61 per `OFFICIAL_INCIDENT_CASES.md`), so OCR may be needed. Old layouts are unverified. | Public government publication; terms not reviewed | Download: small. Extraction: keyword filter, then LLM plus human check. |
| **TCMB EVDS (EVDS 3)** | Policy and deposit rates, CPI, FX, used as money-market benchmarks | **API key required**: a free account, with the key taken from the profile page. EVDS 3 launched in January 2026. | Daily or monthly; long history | Unverified | Terms read: data may be used and published **with attribution**. In commercial products it must **not be passed on as an extra fee** to users. No investment advice. | About 1 h, after Mirza approves creating the account |
| **Borsa İstanbul data** | Real-time, delayed and end-of-day stock data | Licensed distributors only. **Non-display use** (monitoring, risk management and investment-analysis systems) needs a Data Distribution Agreement signed directly with Borsa İstanbul. Index calculation from delayed or end-of-day data has been licensed since 2014. | n/a | Fees unverified | Contractual | Not this weekend (DEC-024/025) |

## 4. Past Turkish fund liquidations, closures and suspensions

No official consolidated machine-readable list was found. Candidate sources, most authoritative first:

1. **SPK bulletins, 2005–2026.** Bulletin 2026/60 directs the TEFAS trading closure and 2026/61 the liquidation (`docs/handoff-v0.5/research/problem_market/OFFICIAL_INCIDENT_CASES.md`). A 1 October news item reports an **updated liquidation list**, so bulletins 2026/62–69 must be read. Only 2026/61 is local.
2. **KAP "Tasfiye Olmuş Fonlar"** at `/tr/YatirimFonlari/TEYF`. The page renders client-side, so its count and liquidation dates are unverified. KAP fund pages have a "Fonun Tasfiye Tarihi" field.
3. **SPK press notices** (S01–S11 in the same file): the 23 Sep investor-count statement, the 28 Sep process clarification, and the two 1 Oct notices on interim payments and conditional reopening.
4. **TEFAS price stops.** A closed fund leaves no trace in TEFAS. Locally, 25 price series stopped in 2026; the causes are unverified.
5. **Secondary pages** (news and law-firm lists of the 131 funds) are useful for cross-checks only.

## 5. Sources the business side already found (repository)

- **`docs/handoff-v0.5/research/SOURCE_REGISTER.md`:**
  - S01: BIST licensing FAQ.
  - S04: SPK portfolio values page.
  - S07: SPK web service (schema never recovered).
  - S34: KAP REST service (contract, MKK authorization, API key).
  - S35: Fintables packages.
- **`problem_market/OFFICIAL_INCIDENT_CASES.md`:**
  - SPK bulletins 2026/54, /60 and /61 and the bulletin index.
  - KAP disclosure 1664479 (the bulletin reference).
  - KAP disclosure 1665519 (a correction-flagged disclosure).
- **`problem_market/ANOMALY_FREQUENCY_MAP.json`:** all 28 catalog frequencies are unknown.
- **`docs/notes/2026-10-06-market-research-brief.md`:** MKK VAP investor cohorts, KAP 2025 notification totals and a competitor list. These are market-sizing figures, not product data feeds.
- **`risk_review/DATA_AND_COST_RISKS.md`:** the wrapper and entitlement risks.

## 6. Collisions to surface

1. **Dated history.** The spike says only the price is dated; SPK says daily units, investors and size exist. If SPK's service works, investor-count and flow detectors get history up to 5 years. If it does not, they start on 2026-10-09.
2. **Rights versus B2B sale.** TEFAS, KAP and SPK rights are unreviewed, and KAP routes high-volume use to a contract. Stock monitoring is BIST "non-display" use, which needs a direct agreement. EVDS forbids passing its data on as an extra fee. DEC-027 (real data only in the private local demo) fits the localhost build but not a pilot with an insurer or a broker.
3. **LLM processing.** The spike's admission template lists "model-processing rights" as not confirmed. Sending TEFAS or KAP-derived evidence to OpenAI is new third-party processing. Send detector outputs and public text only, and log every call.
4. **Accounts and budget.** The OpenAI key and an EVDS key conflict with the handoff's "no service accounts" rule. The $25 OpenAI cap counts against the TRY 5,000 cumulative ceiling.
5. **Evaluation scope.** With the split dropped, every number is a development result. TEFAS prices reach back only to 2021-10, so SPK events from 2005 to 2021 can give frequencies for insurers but no price backtests, unless SPK's service has deeper history.
6. **Demo-critical files.** The demo re-hashes the main checkout's registered `raw/` files and `raw/snapshots/fund_snapshots.sqlite3`. `kap_batch.py` writes into `raw/kap/reports/`, and the price job writes to whatever `--out` directory it is given. Overnight output must go to **new** directories.
7. **Coverage gaps.** `--tefas-only` collects 1,071 of the 2,133 funds, the scheduled task is weekday-only, and a missed day is lost permanently.

## 7. Data plan for the next 25 hours (until the Sunday 13:00 freeze)

### A. Saturday 13:00–20:00: load PostgreSQL first, offline, in this order

1. **Schema.** Every observation carries `source`, `origin`, `effective_date` and `available_at`. Create the app tables at the same time: `llm_decision`, `human_override`, `chat_message`.
2. **`fund`.** About 2,133 rows, built from the forward snapshot's raw rows plus the price-file list.
3. **`price_obs`.** 1,673,412 rows, with 0 or null kept as missing. Loading takes minutes with COPY.
4. **`snapshot_obs`.** 1,073 forward rows (2026-10-09) plus the 100 local rows (2026-10-06).
5. **KAP data.** `kap_report` (1,267 list entries with file paths and hashes) and `kap_monthly` (the 101 parsed series).
6. **`regulatory_event`.** The 2026/61 order and its 131 funds, with each mapping to a fund code human-checked; the repo says the list is not fully audited.
7. **`detector_result`.** D1–D5 recomputed on all funds and labelled as development results.

Two spikes, at most 1.5 h together, using THF and TP2 only and GET requests at 6 s:

- the SPK Portföy Değerleri web service;
- the KAP filter ids for fund material events.

Optionally, Safa can copy the full 2026-10-06 snapshot privately, not through git. That would give all funds two cross-sections.

### B. Overnight, about 20:00–08:00, unattended

There is one process per host. Each job writes to new directories or a staging database, stops after 3 consecutive failures, and logs URL, status and SHA-256 for every request.

| Order | Job | Pacing | Requests | Estimated time |
|---|---|---|---|---|
| T1 | TEFAS profiles for all 2,133 funds (ISIN, fees, risk, `kapLink`, status) | 1.5 s | about 2,133 | about 1 h |
| T2 | Snapshots of the roughly 1,062 non-TEFAS-traded funds (no `--tefas-only`; they stay as-of 2026-10-09) | 1.5 s | about 2,100 | about 1 h |
| T3 | Price refresh (`--periyod 12`) for all funds into a **new** directory | 1.5 s | about 2,133 | about 1 h |
| S1 | SPK bulletins: all of 2026, then 2024–2025 | 6 s | about 230 | about 25 min |
| S2 | SPK bulletins 2005–2023 (count unverified) | 6 s | about 1,000–1,500 (estimate) | 2–2.5 h |
| K1 | KAP fund page and report list for the roughly 970 TEFAS-traded funds without one (starts after T1 provides `kapLink`) | 6 s | about 1,950 | about 3.3 h |
| K2 | Latest monthly report PDF for each of those funds | 6 s | about 1,950 | about 3.3 h |
| K3 | KAP lists for the remaining roughly 1,060 funds (best effort) | 6 s | about 2,100 | about 3.5 h |
| X | Backfill from the SPK service, only if the spike shows it is dated and open | Spike decides | Spike decides | Spike decides |

TEFAS (T1–T3) takes about 3.2 h in sequence. SPK and KAP run in parallel on their own hosts. KAP totals about 10 h, so K3 finishes only partly.

### C. Sunday 07:00–12:30

1. Import the overnight output and reconcile it with the 2026-10-07 prices.
2. Rerun the detectors.
3. Turn SPK text into candidate events with a keyword filter ("tasfiye", "işlem", "faaliyet izni", "fon"). The LLM extracts only from the matching passages; total spend is capped well under $25, and a human confirms each event.
4. Freeze at 13:00.

## 8. After the event

- **Collect every weekday for all 2,133 funds,** not only the TEFAS-traded ones. The dated size, units and investor history is the moat.
- **Collect KAP reports every month for all funds,** because the 365-day window rolls and older reports can no longer be listed.
- **Review rights:** TEFAS (Takasbank), KAP (MKK; the publication-service contract for production) and SPK. Add EVDS attribution. A BIST agreement is needed only if stocks return.
- **Build a 2005–2026 event table** from SPK bulletins and KAP TEYF, human-verified. It gives yearly event frequencies for insurers, labels for evaluation, and a new prospective holdout from 2026-10-12.
- **Extend the parsers** to the Ziraat, Garanti and Yapı Kredi layouts, and add OCR for the image-only PDFs.

## Sources (web, accessed 2026-10-10)

- [tefas-crawler README (2026 rewrite note)](https://github.com/burakyilmaz321/tefas-crawler)
- [SPK Portföy Değerleri](https://spk.gov.tr/kurumlar/fonlar/yatirim-fonlari/menkul-kiymet-yatirim-fonlari/portfoy-degerleri)
- [SPK web services help](https://ws.spk.gov.tr/help/index.html)
- [SPK 2026 bulletins](https://spk.gov.tr/spk-bultenleri/2026-yili-spk-bultenleri)
- [SPK past years](https://spk.gov.tr/spk-bultenleri/gecmis-yillara-ait-bultenler)
- A KAP fund page with category navigation (`https://kap.org.tr/tr/fon-bilgileri/genel/<fund-slug>`; the specific
  fund is omitted because committed files name only the eight target funds)
- [KAP TEYF](https://www.kap.org.tr/tr/YatirimFonlari/TEYF)
- [EVDS terms](https://evds3.tcmb.gov.tr/igmevdsms-dis/documents/showDocument?docId=18)
- [EVDS 3 relaunch](https://www.alomaliye.com/2026/01/26/tcmb-elektronik-veri-dagitim-sisteminin-yenilenmesine-iliskin-basin-duyurusu/)
- [tcmb-py (API key)](https://github.com/kaymal/tcmb-py)
- [BIST data licensing FAQ](https://borsaistanbul.com/sss/veri-dagitim-ve-endeks-lisanslama)
- [BIST veri yayını](https://borsaistanbul.com/veriler/veri-yayini)
- [Foreks, updated liquidation list (01-10-26)](https://www.foreks.com/haber/detay/6abddcf295016b5817e6320d/FRKS/tr/spk-guncellenen-tasfiye-listesinde-yer-alan-fonlarin-tasfiye-surecinin-yurutulmesi-esaslarini-acikladi-01-10-26/)