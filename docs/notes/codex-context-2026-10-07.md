# Codex context: Project 50K on 2026-10-07 (evening)

Written by Claude Code at the owner's request so that Codex can continue the implementation. It describes the project as of 2026-10-07 22:59 (Europe/Istanbul). For the current phase, DEC-024 and this file win over the handoff where they conflict; where they are silent, `docs/handoff-v0.5/` applies.

**Superseded as the entry point on 2026-10-10:** read [current-state.md](current-state.md) first. This file stays
as the 2026-10-07 record. Sections 5, 6, 7 and 11 still apply. Sections 1–4 and 8–10 describe 2026-10-07 and are partly
out of date: the app, API and UI now exist, the unit-test count is no longer 81, and the market research brief is
tracked. The section 10 commands and the section 12 start prompt are superseded by `AGENTS.md`. Section 7's development/test split and its unopened-files rule are superseded by DEC-029 (all funds opened, no held-out test set).

**Path maintenance on 2026-10-08:** local file locations and rebuild paths below now
refer to the repository-root `raw/` layout. The original dated findings, pending
decisions and test counts are preserved as a historical snapshot, not a new run.
See [local raw data layout](local-raw-data-layout.md) for the relocation boundary,
legacy aliases and verification record.

## 1. In one minute

- **Product:** investment intelligence for Turkish retail investors. When something notable happens to a fund they follow, they see why it might matter, with its sources. No buy/sell advice, no claim to predict markets. Codename "Project 50K".
- **Scope now:** Turkish investment funds (TEFAS) only ([DEC-024](../decisions/DEC-024-turkish-funds-first.md)). BIST, crypto, US equities and on-chain are postponed, not dropped.
- **Deadline:** Startup Weekend Urla, 9–11 October 2026. Three-person team; the owner is the developer. Gate G01 (a written organizer ruling on using pre-event material) is open.
- **Built so far: a data layer and research. There is no application, API, UI or auth.** All 284 requirement IDs are still `NOT_IMPLEMENTED`.
  - TEFAS client, daily snapshot job, price-history job, KAP report reader, retry/circuit-breaker helpers: 81 unit tests.
  - A case study on SPK's liquidation order of 17 September 2026, with five pre-registered price detectors and their results.
  - Local data (not in git): five years of prices for 2,022 funds and a year of KAP monthly reports for 101 funds.
- **Open owner decision that blocks evaluation work:** how to split the liquidated funds into development and test data (section 7). Until the owner answers, do not compute detector output on the unopened funds (section 4).
- **Suggested next work:** section 9. Per the handoff, propose one slice and wait for approval before implementing.

## 2. People, constraints and gates

- **Owner/developer:** Safa (GitHub `Safa675`). Reply to the owner in simple, short Turkish. Code, commit messages, docs and prompts stay in English.
- **Budget and accounts (DEC-020, 2026-10-02):** TRY 5,000 cumulative ceiling, excluding Claude/Codex subscriptions. **No service accounts exist**, so there is no Google OAuth, Supabase, LLM API key, email sender or hosting. The ceiling is not authorization to spend. Ask in chat before anything that needs an account or money.
- **Data rights (G03 and TEFAS/KAP terms) are not reviewed.** No real TEFAS or KAP values go into git.
- **G01** open: do not claim competition eligibility.
- **Repo:** `github.com/Safa675/project-50k` (private). `main` holds PRs #1 and #2. This file arrives with the PR that follows them.
- An untracked file, `docs/notes/2026-10-06-market-research-brief.md`, is not part of any change. Leave it alone.

## 3. What exists

| Path | What | State |
|---|---|---|
| `services/p50k/providers/tefas.py` | `TefasClient(transport)`: `snapshot(code)`, `price_history(code, periyod)`, `fund_list()`. `Decimal` numbers, `None` for missing, `FundNotFound` on an empty list, certificate verification on. A price of 0 becomes `None`. | tested |
| `services/p50k/providers/kap_report.py` | `read_headline(lines)` finds total value, units outstanding, period-end price, previous price, period change and cash flows in a KAP monthly report by keyword. Works on text lines; the PDF-to-lines step (pymupdf) is in `research/spikes/2026-10-06-tefas/kap_pdf_check.py`. | tested on synthetic text |
| `services/p50k/providers/resilience.py`, `disk_cache.py`, `services/p50k/series.py` | Ported from the owner's bist-quant repo with fixes ([notes](bist-quant-reuse.md)). | tested |
| `services/p50k/jobs/fund_snapshots.py` | Collector: latest size, units, investor count per fund into SQLite. A snapshot is dated only when its price is positive and equals the newest dated price. | ran once (2026-10-06) |
| `services/p50k/jobs/price_history.py` | Downloads dated prices per fund as JSON, `null` where there is no price. | ran for all 2,022 funds |
| `ops/systemd/` | Weekday-evening timer for the snapshot job. **Not installed**; needs the owner's OK. | |
| `tests/unit/` | 81 `unittest` tests, standard library only. | pass |
| `research/spikes/2026-10-06-tefas/` | [REPORT.md](../../research/spikes/2026-10-06-tefas/REPORT.md) (what TEFAS and KAP return, field by field), `kap_batch.py` (download/check), `kap_series.py` (reports into monthly series), `kap_series_coverage.json`. | |
| `research/events/2026-09-17-spk-liquidations/` | [NOTES.md](../../research/events/2026-09-17-spk-liquidations/NOTES.md), `liquidated_funds.json` (131 funds), `top100_funds.txt`, and `price_detectors/` (pre-registration, code, results). | |
| `docs/handoff-v0.5/` | The frozen v0.5 handoff: requirements, anomaly catalog, JSON contracts, an offline reference harness (88 tests pass). Do not edit. | |

Not in the repo yet: `pyproject.toml` or any lockfile, CI, an API, a UI, a database schema beyond the snapshot SQLite file. Libraries seen in use: Python 3.13.13, numpy 2.4.6, httpx 0.28.1, pymupdf 1.27.2.3, borsapy 0.10.1 (pandas 2.3.3 comes with it). `services/` itself imports only the standard library.

## 4. Local data that is not in git

Gitignored under the repository-root `raw/`, or outside the repo. The old research
paths remain ignored compatibility symlinks on the owner's laptop. **If you run in
a fresh clone or a cloud sandbox, none of the local data or aliases is there**;
section 10 says how to rebuild data. Relocation is not a backup.

| Location | Content |
|---|---|
| `~/.local/share/project-50k/fund_snapshots.sqlite3` | One snapshot per listed fund (2,133 funds), taken 2026-10-06: size, units outstanding, investor count, category, raw TEFAS row. 2,000 are dated; 133 are "unknown" after the zero-price fix. A backup, `.before-zero-price-fix`, sits beside it. TEFAS keeps no history of these fields, so a day not collected is lost. |
| `raw/tefas/prices/{CODE}.json` | Five-year dated prices, `[date, price or null]`, 2,022 funds, retrieved 2026-10-07. One shared calendar of 1,258 business days, 2021-10-07 to 2026-10-07. |
| `raw/spk/spk-bulten-2026-61.pdf` | The SPK bulletin with the liquidation list. |
| `raw/kap/reports/{CODE}/*.pdf` | KAP monthly (and weekly) portfolio reports, last 365 days, 101 funds, about 1,340 PDFs, plus each fund's report list and acquisition context. |
| `raw/kap/series/{CODE}.json` | The parsed series (values) for those 101 funds. |
| `raw/tefas/responses/`, `raw/kap/reports/` | Original provider-spike responses. The former also retains the unchanged mixed-provider `requests.json`; KAP list/page responses and the standalone spike PDF are in the latter. |
| `raw/tefas/logs/`, `raw/tefas/price-detectors/` | Existing download logs and detailed research outputs. Moving them does not run detectors or change prior results. |

**Opened vs unopened.** The 100 funds in `top100_funds.txt` are *opened*: detectors have run on them and TP2/THF were studied in detail. The other 1,922 price files were downloaded and format-checked only (row counts, sorted dates). They are **unopened**. Computing anything on them is governed by section 7.

## 5. Data-source facts that bite

Full detail is in `REPORT.md`. The ones that have already caused bugs:

1. **TEFAS prices of 0 mean "no price"** (before a fund starts, after it stops, and as the latest price). Treat as missing. The first collector matched 0 against 0 and dated 133 snapshots wrongly.
2. **An unknown or retired fund code returns HTTP 200 with an empty list.** Never read empty as "nothing happened".
3. **Only the price is dated.** Size, units outstanding and investor count are latest-value-only. Category rank and size in history rows are today's values.
4. **TEFAS dates a price one business day after its valuation date.** The row dated D is available by about 11:05 on D.
5. **History:** `fonFiyatBilgiGetir` with `periyod` 12, 36 or 60 (1, 3 or 5 years; 60 is the maximum). Other values or date ranges fail.
6. **KAP:** the fund page comes from TEFAS's `kapLink`; the fund id is a 32-character hex string that can be lower case (borsapy's pattern misses those). Report list: `GET kap.org.tr/tr/api/disclosure/filter/FILTERYFBF/{fundId}/8aca490d502e34b801502e380044002b/365`. A longer window returns an empty list. The attachment is a wrapper; the PDF starts at the `%PDF-` marker.
7. **KAP rate limit:** a 1.5 s pause got us cut off after about 180 requests. A 6 s pause has run thousands of requests. `kap_batch.py` stops after three consecutive server failures and now waits (up to 20 minutes) when the local network drops.
8. **Report layouts and wording vary** across 19 companies: "Ay Sonu", "Dönem Sonu", "Haftalık"; numbers as `1.234,56` or `1,234.56`; values on the next line; a lone separator with three digits (`1,234`) is ambiguous and rejected. 1,246 of 1,255 reports parse; the rest are image-only PDFs or attachment-only disclosures.
9. **Ziraat reports** are dated one business day earlier than the others against TEFAS, and their unit count differs from total value ÷ price by 0.1–0.4%. Use total value and price.
10. **KAP cash-flow fields are zero in most reports** even when units outstanding moved a lot. The usable flow measure is the month-to-month change in units outstanding (or the AN-FND-002 estimate from total value and price).
11. **Report cadence:** KAP's period code is `AB` (monthly) or `HB` (weekly). All 15 Serbest Fon in the set switched to weekly reports in early September 2026; no other category did. This is not specific to liquidated funds.
12. **borsapy 0.10.1** adds nothing dated beyond price for funds (placeholders for size and investors, `verify=False`, no rate limiter). Prefer our own client.

## 6. The case study: SPK's order of 17 September 2026

- **Event:** on 17/09/2026 SPK ordered 131 funds of seven portfolio management companies liquidated (decisions 57/1707 and 57/1708; Bulletin 2026/61, section C). Companies: Pardus 42, Hedef 31, Atlas 16, Bulls 15, Pusula 12, A1 Capital 9, Tera 6. By TEFAS category, 117 of the 131 are Serbest Fon, 9 money-market, 3 participation, 2 equity. SPK's reasons are not in our files: **do not call the funds fraudulent or manipulated.**
- **Today:** 21 of the 131 show no price on TEFAS (all six Tera funds among them); 110 still show one.
- **Universe:** the 100 funds with the most investors in the 2026-10-06 snapshots. Eight liquidated funds are in it:

| Rank | Code | Company | Category |
|---|---|---|---|
| 9 | THF | Tera | Equity |
| 11 | TP2 | Tera | Money market |
| 21 | TLY | Tera | Serbest |
| 40 | DFI | Atlas | Serbest |
| 44 | DOH | Tera | Serbest |
| 49 | PRY | Pusula | Money market |
| 77 | KHA | Pardus | Equity |
| 90 | PNU | Pusula | Money market |

  The universe is chosen with data from after the order (survivorship), and TEFAS keeps no history of investor counts.
- **Owner's demo idea:** replay a fixed historical window, 6 Oct 2025 to 6 Oct 2026, labeled historical replay.
- **Price-only detectors**, pre-registered before the run (`price_detectors/PREREGISTRATION.md`, commit b01da35), evaluated on 2025-10-06 to 2026-09-16:

| Detector | Targets flagged | Other funds flagged |
|---|---|---|
| D1 persistent excess return over category peers | 5 of 8 | 5 of 63 |
| D2 change in excess return | 3 of 7 | 5 of 63 |
| D3 return autocorrelation | 0 of 8 | 4 of 83 |
| D4 correlation with peers | 0 of 8 | 4 of 63 |
| D5 young fund (under 730 days) | 6 of 8 | 5 of 92 |

  **These are development results, not validation.** The ideas behind D1, D2 and D5 came after looking at TP2 and THF, the targets are four companies' funds that move together, and the universe is selected after the event. D1 flagged all three liquidated money-market funds and none of the other 16 money-market funds. THF showed nothing in prices except its age.
- **KAP shows what prices don't:** TP2's units outstanding grew 4.3-fold from October 2025 to August 2026 (+26% to +37% a month from November to February) while three bank money-market funds stayed at 0.7–1.0 times. THF's August report, published 2 September 11:02 (15 days before the order), shows units up 54-fold in one month. Both were seen before any rule was written.
- **A hypothesis that did not hold:** a switch to weekly KAP reports looked specific to three liquidated funds in a partial sample. With all 101 funds read, all 15 Serbest Fon switched. It is withdrawn (see NOTES.md). Keep it as a reminder to check a pattern on the full development set first.

## 7. Evaluation rules (binding on further detector work)

1. **Do not tune detectors on the funds you evaluate them on.** Thresholds in `price_detectors/` are label-free percentiles of values dated before 2025-10-06. Do not edit `detectors.py` or `PREREGISTRATION.md`; they are hash-linked to `results.json`. Write a v2 beside them with its own dated pre-registration.
2. **Pre-register before running:** thresholds, windows, universe, evaluation window and the count rules, committed before any result exists.
3. **Count false alarms:** report targets flagged, other funds flagged, the number expected if the same count were drawn at random, and the flag rate in the year before the window.
4. **Use only what was knowable on the day** (section 5, items 4 and 6), and add a look-ahead test.
5. **Naming:** committed files name only the eight targets. Other funds are counted, never named as flagged.
6. **Case study, not statistics:** eight targets from four companies; a fund with no visible warning in public data is a finding too.

**Pending owner decision (asked 2026-10-07, unanswered): split by company, not by fund.**

| Group | Companies | Liquidated funds | Use |
|---|---|---|---|
| Development | Pardus, Atlas, Pusula, Tera | 76 (the 8 seen targets plus 68 unopened) | Explore and tune freely |
| Sealed test | Hedef, Bulls, A1 Capital | 55 (50 Serbest Fon, 5 money market or participation) | Do not look until the rules are frozen; run once |
| Controls | Non-liquidated funds: the 64 other funds of the three sealed companies, plus other companies' funds split by company by a rule written before looking | | False-alarm counts |

None of the 55 sealed funds is in the top 100, and nobody has looked at their prices or KAP reports. The reason for splitting by company: funds of one company behave alike, so developing on one and testing on its sibling would let a rule memorize the company's style.

**Until the owner approves a split, do not compute detector output, thresholds, charts or any other statistic on the 1,922 unopened price files.** Downloading and format checks are fine. If the owner picks a different split, update this section.

The owner also floated testing on US data. Findings: SEC Form N-PORT data sets are free and official, hold net assets, monthly total returns and monthly flows from October 2019 and include funds that later liquidated, but are monthly, not daily. CRSP, the standard survivor-bias-free source, is a paid subscription. Open question to the owner: access to WRDS/CRSP through a university? The one close US analogue found is Infinity Q (SEC: NAVs falsely inflated February 2017 to February 2021; redemptions suspended 22 February 2021; fund liquidated). Not started; the daily detectors would need monthly versions.

## 8. Decisions

**Made**

| Decision | Date |
|---|---|
| Turkish funds first; BIST, crypto, US, on-chain postponed (DEC-024) | 2026-10-06 |
| Repo private, named `project-50k`, handoff copied unchanged under `docs/handoff-v0.5/` | 2026-10-06 |
| TRY 5,000 ceiling, no service accounts, preparation authorized, no organizer ruling (DEC-018/019/020) | 2026-10-02 |
| Universe: the 100 funds with the most investors | 2026-10-07 |
| Bulk downloads approved: TEFAS prices for all funds with a price, KAP monthly reports for the top 100 | 2026-10-06/07 |

**Pending (owner)**

1. The company split in section 7.
2. Install the daily snapshot timer (`ops/systemd/`)? Not approved; no timer is running.
3. US data as an external check after the weekend; WRDS/CRSP access.
4. Which vertical slice comes first (section 9).
5. External: G01 ruling, TEFAS/KAP data rights (G03), accounts for auth, LLM and email.

## 9. Suggested next slices

Choose one at a time, as the handoff asks (`docs/handoff-v0.5/prompts/IMPLEMENT_ONE_SLICE.md`). Requirement IDs come from `docs/handoff-v0.5/requirements_registry.json`. Everything here works without an account.

**A. Fund evidence store and point-in-time replay cursor** (FR-032, FR-018, FR-019, FR-108, FR-109, NFR-038). Load the price files, KAP series and snapshot DB into one SQLite store. Every row carries source, effective time, availability time and origin `HISTORICAL_REPLAY`. `ReplayCursor(cutoff)` returns only what was available at the cutoff.
- Done when: tests with synthetic data show that nothing after the cutoff is visible, that changing a future value leaves every output at the cutoff unchanged, that a price of 0 is missing, and that every row has provenance.

**B. Detector interface and event candidates** (FR-037, FR-064; `contracts/event.schema.json`, `contracts/evidence.schema.json`). Port the five price detectors, and AN-FND-002 as written, into `services/p50k/detectors/` as pure functions returning `TRIGGERED`, `NOT_TRIGGERED` or `ABSTAINED` with reasons, as `docs/12_Anomaly_Catalog.md` requires.
- The research `detectors.py` stays frozen; the service version must give identical numbers on a synthetic golden series.
- AN-FND-002: estimated flow = A_t − A_prev × (NAV_t ÷ NAV_prev); rate = flow ÷ A_prev; candidate at |rate| ≥ 10%. The catalog also says "only after historical baseline checks" without defining them. Implement the literal threshold, report the baseline check as a separate parameter, and record the ambiguity; do not choose it by looking at the seen targets.
- Event assembly fills every required field of `event.schema.json`. Confidence is inspectable heuristic evidence strength, not probability, and no LLM assigns it. Turkish `title_tr` and `summary_tr` come from templates (docs 18 glossary). No advice wording.
- Done when: emitted events validate against the schema, negative cases pass, and nothing real is committed.

**C. Read-only API** (FastAPI and Pydantic; `contracts/openapi.yaml` operations `searchAssets`, `getAsset`, `listEvents`, `getEvent`, `health`). Serve funds, events and evidence from the store, with the data mode (`HISTORICAL_REPLAY`) in every response. Done when contract tests pass and unknown or unavailable states are explicit.

**D. Event feed and detail UI** (Next.js App Router, TypeScript, Turkish copy; FR-073, FR-078, FR-103). Blocked on the designer's approval (G09); `config/design_tokens.json` and `DESIGN.md` are the starting point. Scaffold only until then.

**E. Sealed-test runner** (after the owner approves a split). A runner that refuses to read sealed data unless the committed protocol's hash matches, and a report that names only the eight targets.

**F. Housekeeping:** `pyproject.toml` with locked dependencies and CI (backlog T01); installing the snapshot timer needs the owner's OK.

Not available without the owner: Google sign-in, watchlist persistence in a hosted database, AI investigation/chat (an LLM key), email, deployment.

## 10. Environment and workflow

- **Python:** `~/miniforge3/bin/python3` (3.13.13).
- **Tests** (from the repo root):

```sh
PYTHONPATH=services python -m unittest discover -s tests -t . -v
(cd research/events/2026-09-17-spk-liquidations/price_detectors && python -m unittest test_detectors -v)
(cd docs/handoff-v0.5 && python -m unittest discover -s tests -v)
```

- **Rebuild the local data** (needs the network; be gentle):

```sh
PYTHONPATH=services python -m p50k.jobs.fund_snapshots          # about 2 hours for all 2,133 funds
PYTHONPATH=services python -m p50k.jobs.price_history --codes THF TP2 --out raw/tefas/prices --periyod 60 --pause 1.5
python research/spikes/2026-10-06-tefas/kap_batch.py download --funds THF TP2 --pause 6 --log my_log.json   # about 4 minutes per fund
PYTHONPATH=services:research/spikes/2026-10-06-tefas python research/spikes/2026-10-06-tefas/kap_series.py
PYTHONPATH=services python research/events/2026-09-17-spk-liquidations/price_detectors/run.py   # about 10 seconds
```

  Downloads reuse files already on disk. The owner's Wi-Fi dropped twice on 2026-10-07 and the laptop slept once for 55 minutes while the session was idle; long jobs stall, nothing already written is lost, and a rerun continues from the files on disk.
- **Code style:** `from __future__ import annotations`, type hints, `Decimal` for prices and money, `None` for unknown, atomic file writes, `unittest` (not pytest), paced requests with a circuit breaker. Match the surrounding comment density; comment only where the reason is not obvious.
- **Git:** branch from `main`, one PR per slice into `Safa675/project-50k`. `gh pr edit` fails with a "Projects (classic)" GraphQL error; edit descriptions with `gh api -X PATCH repos/Safa675/project-50k/pulls/N -F body=@file`.
- **Before every commit**, compare staged files with the real values in the gitignored data (long numbers from the price and KAP files). One real price slipped into a draft test on 2026-10-07 and was caught this way.
- **Report each task as the handoff requires:** requirement IDs, changed files, the exact tests run with their output, what is untested, the data mode, limitations and the next recommended task.

## 11. Do not claim

- Live data, a working product, or a tested provider beyond what REPORT.md records.
- Any accuracy, recall or false-alarm figure outside the development results in section 6, which are labeled as such.
- That the sealed test has been run (it has not), or that a rule "would have caught" a fund before 17 September.
- That any of the 131 funds were fraudulent, manipulated or guilty. A flag is not an allegation.
- Eligibility for the competition (G01 is open), or an official TEFAS/KAP/SPK relationship.

## 12. Ready-to-paste start prompt

> Read `AGENTS.md` and `docs/notes/codex-context-2026-10-07.md`. Verify the repo state with the test commands in section 10 and report the actual results. Then propose one slice from section 9 with requirement IDs, a file-change plan, acceptance tests and any ambiguity that could lead to an irreversible or unsafe choice. Do not implement anything until I approve. Reply to me in simple Turkish; keep code, commits and docs in English.
