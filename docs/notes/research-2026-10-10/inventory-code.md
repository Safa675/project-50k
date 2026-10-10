# Project 50K: implemented code, reuse verdicts and gaps for a deploy-ready product

**Repository root:** `C:\Users\mirza\Desktop\Hackathon\project-50k` (main checkout, HEAD `2c2c725`, clean). All paths below are relative to that root. Absolute paths for the key files are at the end.

**How this was checked:** read-only. Nothing was edited, installed, started or stopped. The test suites and builds were not run. Test counts come from collecting the Python tests with unittest and from counting test calls in the frontend sources. Data facts are counts and dates only.

## 1. Bottom line

- **Size.** `services/p50k` has about 7,760 lines of Python and `frontend/src` about 2,970 lines.
  - About half of the Python, `research_reviews/` (2,208 lines) and `api/` (1,580 lines), only serves the sealed 100-fund research bundles behind the pitch demo.
- **Ready to reuse in the product.**
  - Backend: the TEFAS client, retry and circuit breaker, the KAP headline parser, the daily snapshot logic, the D1–D5 math, the AN-FND-002/004 arithmetic, the holdings concentration metrics and `series.py`.
  - Frontend: the gap-aware chart, the hash-verified PDF evidence viewer, the validate-every-response fetch pattern, the tr-TR formatters and the loading/error/empty/stale state patterns.
- **Missing completely:**
  - no PostgreSQL schema or migrations, worker or job queue, or detector service layer;
  - no auth, Dockerfile, compose file, CI, structured observability or B2B API.
  - The KAP downloader exists only as research scripts. Their HTTP library (`httpx`) is in neither `uv.lock` nor `.venv`.
- **Blocks "all ~2,000 funds with real data":**
  - The pending development/test split forbids any computation on the 1,922 unopened price files (`docs/notes/codex-context-2026-10-07.md` §7).
  - D1 thresholds and peer groups were calibrated on the 100-fund universe only.
  - KAP covers 101 funds, and at the safe pace a full backfill takes days.
  - The holdings parser supports one PDF layout.
- **None of the running apps work inside Docker as they are.** All of them accept loopback only:
  - the API checks the Host header;
  - CORS allows only loopback origins;
  - `frontend/next.config.ts` throws at startup if the API origin is not loopback.

## 2. Toolchain, pinned versions, CI

**`pyproject.toml`:**
- `requires-python = ">=3.13"`, no core dependencies, `[tool.uv] package = false`. The code runs through `PYTHONPATH=services` and is not an installable package.
- Extras:
  - `api`: `fastapi>=0.115,<1`, `pydantic>=2.12,<3`, `uvicorn>=0.30,<1`
  - `api-test`: `httpx2`
  - `research`: `numpy==2.4.6`, `pymupdf==1.27.2.3`

**`uv.lock`** (lock format version 1, revision 3) resolves:
- fastapi 0.143.0, starlette 1.7.0, pydantic 2.14.0, pydantic-core 2.50.0, uvicorn 0.54.0
- numpy 2.4.6, pymupdf 1.27.2.3, httpx2 2.13.1, httpcore2 2.13.1, anyio 4.15.1
- opentelemetry-api 1.45.1 (a FastAPI dependency; nothing is configured to use it)
- h11 0.16.0, click 8.5.0, idna 3.20, truststore 0.10.4, typing-extensions 4.16.0

**The local `.venv` has drifted from the lock.**
- It runs CPython 3.13.15 (uv 0.12.17).
- It contains `tzdata` 2026.5, which is not in `uv.lock`. Windows needs it for `ZoneInfo("Europe/Istanbul")`, which `jobs/import_evidence.py` and `analytics/holdings_divergence.py` call at import time.
- Research scripts also use packages that are not locked: `httpx` (the KAP scripts) and `pandas` (the holdings-divergence runner). Neither is installed in `.venv`.

**`frontend/package.json`** pins exact versions. `package-lock.json` (lockfile v3, 250 packages) agrees.
- Runtime: next 16.4.0, react and react-dom 19.3.0, next-intl 4.14.9, lightweight-charts 5.2.1, pdfjs-dist 6.4.299, tailwindcss and @tailwindcss/postcss 4.3.3, zod 4.6.5, clsx 2.1.1, tailwind-merge 3.7.0.
- Development: typescript 7.0.2, vitest 5.0.3, @playwright/test 1.64.0, @types/node 26.6.4, @types/react and @types/react-dom 19.3.0.
- Scripts use webpack mode and bind `127.0.0.1:3060`. There is no `engines` field and no lint script or ESLint config.

**This machine:** Node 24.14.1, npm 11.11.0, Docker 29.8.0, Compose v5.5.1, uv 0.12.17, git 2.53.

**Missing in the repository:**
- any CI configuration (no `.github/` or other CI files);
- any Dockerfile, compose file or `.dockerignore`;
- any migrations or `.sql` files;
- a root `.env.example` (the only one is the frozen `docs/handoff-v0.5/.env.example`).

## 3. Backend inventory

**Coupling legend:**
- **REG:** registered in `tests/unit/registered_sources.lock.json` or the dated-bundle set. The demo bundles re-hash these files on every load, so an edit makes the demo answer 503 until every bundle is resealed (`.claude/rules/registered-runtime.md`).
- **RUN:** hash-bound to an offline research run's manifest. An edit does not break the demo.

### 3.1 Providers (`services/p50k/providers/`)

| Module | Purpose | Tests | Coupling | Verdict |
|---|---|---|---|---|
| `tefas.py` (186 lines) | TEFAS JSON client: `snapshot`, `price_history` (periyod 13/12/36/60), `fund_list`. Standard library only, certificate verification on, Decimal values. A TEFAS price of 0 becomes None; an empty list raises `FundNotFound` | 8 (fake transport, no network). Used daily by the forward collector | none | **Reuse as-is** |
| `resilience.py` (187) | Circuit breaker and retry with jitter (ported from bist-quant, Apache-2.0) | 19 | none | **Reuse as-is** |
| `disk_cache.py` (224) | TTL JSON file cache | 15. Not imported by any runtime code | none | Reuse as-is (optional; probably unnecessary once PostgreSQL exists) |
| `kap_report.py` (126) | Keyword parser for KAP report headline fields (total value, units, period-end price, change, cash in/out); handles both Turkish and English number formats | 12 (synthetic text). 1,246 of 1,255 real reports parsed (codex-context §5) | REG + RUN | **Reuse as-is**, imported read-only; extend in a new module |
| `kap_allocation.py` (297) | Monthly-average allocation table from positioned PDF text; requires an exact 100% total | 28 | RUN | **Adapt** |
| `security_holdings.py` (340) | KAP section III holdings rows with reconciliation checks. Supports one page geometry (950×1200 pt) | 24. Real run on the top 100: 20 PARTIAL, 80 UNAVAILABLE, 0 AVAILABLE (`docs/notes/fund-concentration-app-slice.md`) | REG + RUN | **Adapt**: a new multi-layout parser beside it |
| `thf_holdings.py` (261) | THF-specific layout reader | 19 | REG + RUN | **Research-only** |
| KAP download code: `research/spikes/2026-10-06-tefas/kap_batch.py`, `kap_series.py`, `kap_pdf_check.py` (~690 lines) | KAP fund page → 365-day report list → disclosure → PDF; PDF to lines with pymupdf; per-fund series | none in `tests/unit`. Imports `httpx`, which is not locked | none | **Adapt** into `services/p50k/providers/` (no KAP client exists there) |

### 3.2 Jobs and scheduling

| Module | Purpose | Tests | Coupling | Verdict |
|---|---|---|---|---|
| `jobs/fund_snapshots.py` (218) | Daily TEFAS snapshot into SQLite: size, units outstanding, investor count, category, raw rows and the last week of prices. A snapshot gets an as-of date only when its price equals the newest dated price. Each run is logged in the `collector_runs` table | 7 (in-memory SQLite) | Registered runners import only `default_db_path`. The v1/v2 bundles re-read `raw/snapshots/fund_snapshots.sqlite3` in the main checkout | **Adapt**: keep the logic and add a PostgreSQL sink. Leave the current schedule running unchanged, because a missed day cannot be recovered |
| `jobs/price_history.py` (117) | Downloads per-fund price JSON (1, 3 or 5 years) | 5 | Research runner imports `load` | **Adapt**: write to the database, incremental |
| `jobs/import_evidence.py` (383) | Imports local files into an immutable evidence bundle. Refuses funds outside `top100_funds.txt` | 18 | Universe allowlist hard-coded | **Research-only** |
| `ops/systemd/*` | Linux user timer, weekdays 21:00 Istanbul | – | – | Adapt. Whether it is installed on the owner's laptop is unverified |
| `ops/windows/fund-snapshots.ps1` | Windows equivalent | – | – | **Adapt** (keep until a worker exists) |

**What the Windows task has done so far (verified read-only):**
- The task "P50K fund snapshots" is registered: Monday to Friday at 21:00, next run 2026-10-12 21:00. The scheduler has not run it yet (last result 267011).
- The forward database `~/.local/share/project-50k/fund_snapshots_forward.sqlite3` holds:
  - 1,073 rows for 1,071 TEFAS-traded funds;
  - 1,063 rows dated as of 2026-10-09 and 10 undated rows;
  - 2 collector runs on 2026-10-10.
- The two manual runs on 2026-10-10:
  - The first stopped on its circuit breaker after about an hour.
  - The second finished in about 63 minutes. It took about 2,142 requests at a 1.5 s pause.
- `--tefas-only` leaves out funds that are not traded on TEFAS. The 2026-10-06 snapshot listed 2,133 investment funds in total.

### 3.3 Evidence store, replay, series

| Module | Purpose | Tests | Coupling | Verdict |
|---|---|---|---|---|
| `evidence_store.py` (338) | SQLite store of immutable, content-addressed observations in sealed bundles; triggers forbid updates and deletes. Every observation carries source, version, unit, effective/published/available/observed/ingested times, availability provenance, rights status and limitations | 18 | REG + RUN | **Research-only** as storage. **Adapt** its provenance fields into the PostgreSQL schema. Limits: origins are `HISTORICAL_REPLAY`/`SYNTHETIC` only (no `LIVE`/`DELAYED`), and every read loads and re-verifies the whole bundle |
| `replay.py` (49) | As-of cursor. Excludes rows whose availability is unknown; ambiguous revisions raise an error | 12 | REG + RUN | **Research-only**. Re-implement as as-of SQL queries |
| `series.py` (143) | Returns, log returns, drawdown, quantiles, date alignment | 15. Not imported by any runtime code | none | **Reuse as-is** |

### 3.4 Detectors and analytics

| Module | Purpose | Tests | Coupling | Verdict |
|---|---|---|---|---|
| `research/events/2026-09-17-spk-liquidations/price_detectors/detectors.py` (D1–D5, numpy) | Excess-return level and change, autocorrelation, correlation with peers, fund age | 9 (frozen suite) | Frozen and hash-linked to `results.json`. `bundle.py` loads it with importlib | **Adapt**: import read-only, or write a v2 with golden-equality tests. New thresholds need a new pre-registration |
| `detectors/fund_flow.py` (268), AN-FND-002 | Arithmetic F* = A1 − A0·P1/P0, its rate, and a 10% screen. The admission path goes through `ReplayCursor` and requires APPROVED rights, all four timestamps and a stored baseline | 37 | REG + RUN | Arithmetic: **reuse as-is**. Admission: **adapt**. Real data carries rights `UNKNOWN`, so admission always abstains today |
| `detectors/fund_allocation.py` (250), AN-FND-004 | Half-L1 allocation distance with a 20% screen; same rights gate | 33 | RUN | Same as AN-FND-002 |
| `analytics/futures_contribution.py`, `analytics/holdings_divergence.py` (576 lines in total) | Diagnostics for the THF case | 36 + 42, plus 34 runner tests | RUN. The runner needs `pandas` | **Research-only** (a possible later NAV-versus-holdings detector) |

There is no common detector interface, registry, versioned configuration, run record or scheduler.

### 3.5 `research_reviews/` (the demo engine, 2,208 lines, 115 tests): **research-only**

Keep it for the pitch demo. Every file is REG.

- **Fixed view (2026-09-16):** `bundle.py`, `bundle_v2.py`, `contracts.py`, `comments.py`, `concentration.py`.
  - `validate_universe` requires exactly 100 funds.
  - The flow calculation is fixed to July → August 2026.
- **Dated view (12 dates, D1 only):** the `dated_*.py` files. `DENOMINATOR = 100`; the window and calibration dates are constants.
- **Load cost:** every load re-hashes every manifest source. The v2 bundle lists 522 sources totalling about 140 MB (v1: 501 sources, about 136 MB).
- **Worth taking out:**
  - `concentration.calculate_metrics` (top-1/5/10 shares and HHI with exact arithmetic): **reuse**;
  - the index-100 fund-versus-peer chart builder in `d1_context`/`_chart`: **adapt**;
  - the deterministic Turkish comment templates and the wording denylist: **adapt**.

### 3.6 API (`services/p50k/api/`, 64 tests): **replace for the product**

Keep it running for the demo.
- **Fixed view:** `app.py`, `research_routes.py`, `models.py`. Endpoints: `GET /research/v1/health`, `summary`, `funds`, `funds/{code}`, `sources/{id}` (PDF).
- **Dated view:** `dated_app.py`, `dated_routes.py`, `dated_models.py`. Endpoints: `GET /research-dated/v1/dates`, `/dates/{d}/summary`, `/funds`, `/funds/{code}`.
- **Why it cannot be reused:**
  - it verifies a sealed bundle on every request;
  - it reads the universe file;
  - the Host check, CORS and fixed cutoffs are loopback-only;
  - OpenAPI is disabled (`openapi_url=None`);
  - there is no auth.
- **Patterns worth keeping:** strict Pydantic models with decimal strings; an error envelope that carries `message_tr`; `no-store`/`nosniff` headers; source IDs that cannot be turned into file paths.

### 3.7 `ops/local/`: **research-only**

`run_app.py` and `run_dated_app.py` are loopback launchers with a `--check` mode (2 + 8 tests). Replace them with compose for the product.

## 4. Tests per area (Python root suite: 663 collected, not run)

| Area | Tests |
|---|---|
| Providers (tefas 8, resilience 19, disk_cache 15, kap_report 12, kap_allocation 28, security_holdings 24, thf_holdings 19) | 125 |
| Jobs (fund_snapshots 7, price_history 5, import_evidence 18) | 30 |
| Evidence store 18 and replay 12 | 30 |
| Series | 15 |
| Service detectors (fund_flow 37, fund_allocation 33) | 70 |
| Analytics for THF (futures 36, holdings 42) | 78 |
| Research runners (flow 30, allocation 38, concentration 19, futures 23, holdings 11) | 121 |
| research_reviews bundles (37 + 6 + 22 + 23 + 27) | 115 |
| Research API (32 + 16 + 14 + 2) | 64 |
| Launchers (2 + 8) | 10 |
| Repository guards (registered-sources lock 4, hermetic git 1) | 5 |

- **Split:** about 270 tests (41%) cover modules worth keeping; 388 (59%) cover research or demo code.
- **Other suites:**
  - the frozen D1–D5 suite: 9 tests;
  - the frozen handoff suite: 88;
  - agent hooks: 8 (`.claude/hooks/hooks.test.mjs`).
- **Count mismatch:** `docs/notes/current-state.md` records 605 tests run at `33c6064`, with 43 failures and 33 errors that it attributes to Windows. No test file has changed since that commit, so the difference from 663 is unexplained (unverified).

## 5. Frontend inventory

**Routes** (every page is `force-dynamic` and `noindex`; data is fetched only in the browser):

| Route | What it shows | Data path |
|---|---|---|
| `/` | Fixed-date list of the 100 funds | `/api/research/v1/*` rewrite → API on 8767 |
| `/funds/[code]` | Chart, D1 and flow panels, publication record, sources, PDF dialog, concentration | same |
| `/dates`, `/dates/funds/[code]` | D1 at 12 dates | route handler `src/app/api/research-dated/[...path]/route.ts` → 8768 |
| `/preview`, `/preview/dates` | Synthetic design previews with a switcher for loading, error, empty and mismatch states | no API |

**Components and libraries:**

| Item | Verdict |
|---|---|
| `components/primitives/*` (DataTable, Toolbar, Chip, Stat, EmptyState, form.ts) and `lib/cn.ts` | **Adapt**: restyle or replace with Barış's components. The header notice says "Adapted from Bilun … Copyright (c) 2026 Safa Öksüz. All rights reserved" (`frontend/BILUN-NOTICE.txt`) |
| `FundChart.tsx` (Lightweight Charts; separate line segments so missing days show as gaps; accessible table fallback) | **Adapt** |
| `PdfViewer.tsx` and `SourcePdfDialog.tsx` (local PDF.js assets, byte-hash check, native `<dialog>`) | **Adapt** into the evidence viewer |
| `FundList`, `FundDetail`, `ConcentrationPanel`, `ResearchViews`, `Dated*`, `DateSelector` | **Research-only**. They are bound to the research contract: exactly 100 funds, fixed cutoffs, `production_status: "ABSTAINED"` |
| `lib/research-contract.ts`, `lib/dated-contract.ts` (strict Zod; `ListResponseSchema` has `.length(100)`) | **Research-only**. Reuse the runtime-validation pattern |
| `lib/research-api.ts`, `lib/dated-api.ts` (`fetchValidated`, Turkish errors) | **Adapt** |
| `lib/presentation.ts` (tr-TR number and date formats, reason labels) | **Adapt** |
| `lib/decimal-compare.ts`, `lib/chart-data.ts` | **Reuse as-is** |
| `lib/synthetic.ts`, `lib/dated-synthetic.ts` | Research-only. Keep the state-preview idea for design reviews |
| `next.config.ts` (security headers, rewrite, loopback guard) and the route-handler proxy | **Adapt** for container networking |

**i18n:**
- The next-intl client provider runs with locale `tr` and time zone Europe/Istanbul.
- `src/messages/tr.json` has only 14 keys, used in 2 components.
- The dated view's copy sits in `lib/dated-presentation.ts`: sentences fixed by the protocol, plus a denylist.
- Everything else is inline. More than 300 source lines contain Turkish text.

**Tests:**
- Vitest: 118 tests in 14 files.
  - contracts 25, API loaders 31, golden 4, dated copy and presentation 20, presentation 7;
  - concentration 8, proxy 9, PDF 5, chart 6, decimal 3.
- Playwright: 49 `test()` calls in 5 specs. `docs/notes/current-state.md` records 65 executed tests, because some are generated in loops over widths 390/768/1440 and preview states.
  - The API is mocked with `page.route` and invented data.
  - The tests need a production server on 127.0.0.1:3060 and the Chrome channel.

## 6. Visual layer: what Barış's design system replaces or keeps

**What exists today:**
- **Tokens** (`src/app/globals.css` `:root`):
  - text `#192a33`, `#465960`, `#596c72`;
  - surfaces `#fff`, `#f2f4f2`, `#edf4f2`;
  - borders `#d8e0dc`, `#a9bab2`;
  - accent named `--gold` but actually green: `#1b6559`, pressed `#164f46`, subtle `#e7f2ec`;
  - success `#216550`, warning `#80541c`, danger `#993c33`;
  - radius 6/8 px; motion 120 ms ease-out.
- **Base styles:** body background `#f7f8f5`; Arial/Helvetica/system-ui at 15 px, line height 1.5.
- **Missing:**
  - no dark mode and no font loading; `Stat`'s gold variant points to an undefined `--font-display`;
  - no match with the handoff's proposed `docs/handoff-v0.5/config/design_tokens.json` (accent `#1D4E75`).
- **Hard-coded values** outside the CSS: 38 hex colours, including the chart's `#1b6559`/`#718b9d`, and 37 inline `style={{…}}` objects, mostly in the dated view.
- **Layout:**
  - header with brand and data-mode label;
  - `main` up to 1,280 px wide with 30 px gutters (18 px on mobile);
  - page intro (eyebrow, 34 px h1, lead text) with a cutoff block on the right;
  - left-bordered notice banners, a row of stats, and a toolbar with search, two selects and a clear button;
  - a desktop table at least 1,120 px wide that scrolls sideways, switching to cards at 760 px and below;
  - detail pages in a two-column grid (1.8fr / 0.95fr) that becomes one column on mobile, with metric panels, `dl` key-value lists and collapsible evidence groups;
  - a footer with provenance disclaimers;
  - the dated view adds a GET form with a date picker and a warning banner.
- **Accessibility:**
  - `:focus-visible` outlines, `aria-live` result counts and `role=alert` errors;
  - 44 px touch targets in the dated view and a reduced-motion rule;
  - a table fallback for the chart and focus restored when the dialog closes.

**For Barış's system:**
- **Replace:**
  - token values, typography and colours, including the chart palette;
  - header and footer styling;
  - the Chip and Stat visual variants;
  - the page classes in `globals.css`.
- **Keep:**
  - the CSS-variable token architecture (rename to his token names);
  - the state set: loading, error, empty, stale, unavailable, mismatch;
  - the table-to-cards responsive pattern;
  - the accessible chart fallback;
  - the PDF evidence dialog;
  - the tr-TR formatters.
- **Slots his screens must provide:** the integrity rules require visible data-mode and origin labels, as-of or cutoff dates, source lists, and missing/stale states.

## 7. Gaps for a deploy-ready product

1. **Database schema and migrations.**
   - Today: only SQLite schemas (`fund_snapshots`/`collector_runs` and the 3-table evidence store) and file trees under `raw/`.
   - The handoff's `contracts/domain_tables.json` (25 tables) is B2C-shaped: watchlist, chat, notifications.
   - Needed: PostgreSQL tables for funds, category history (categories are current-only today), NAV prices, daily snapshots, KAP disclosures and PDF blobs, parsed headlines and holdings, detector versions, detector runs, signals, jobs, tenants, API keys and an audit log.
   - Store values as `NUMERIC`, because the code uses Decimal throughout. Choose a migration tool; versions to be resolved at setup.
2. **Ingestion scheduling.**
   - Today: command-line jobs triggered by OS schedulers.
   - Needed:
     - a worker container with a database job queue that claims jobs with leases and `SKIP LOCKED` (handoff ADR-004);
     - idempotent run records, retry policies, pacing per source (TEFAS 1.5 s, KAP 6 s) and a KAP disclosure poller;
     - an alert when a business day is missed.
3. **Detector service layer.**
   - Needed:
     - a registry with versioned configurations, and runs keyed by fund, as-of date, detector version and input watermark;
     - stored `TRIGGERED`/`NOT_TRIGGERED`/`ABSTAINED` results with reasons and evidence references;
     - a product policy for the rights gate.
4. **Scaling from 100 to about 2,000 funds.**
   - The 100-fund limit is hard-coded in many places:
     - `validate_universe(100)`, `DENOMINATOR = 100`, the health route's `record_count: 100`;
     - Zod's `.length(100)`, the `top100_funds.txt` allowlist and copy that says "100 fon".
   - Peers come only from the universe funds, and categories are today's.
   - KAP backfill at the documented "about 4 minutes per fund" comes to about 133 hours for 2,000 funds (an estimate, unverified at scale).
   - Data volume: about 2.5 million daily price rows. Fine for PostgreSQL, but not for whole-bundle re-verification on every read.
5. **Auth:** none; everything is loopback-only.
   - Needed: user sessions for the web UI and hashed API keys with scopes for B2B tenants.
6. **Configuration and secrets.**
   - Today: ad-hoc environment variables (`P50K_DATA_DIR`, `P50K_RESEARCH_BUNDLE`, `P50K_FRONTEND_ORIGIN`, `P50K_API_ORIGIN`/`API_PROXY_TARGET`, `P50K_DATED_INDEX`, `P50K_DATED_API_ORIGIN`) and hard-coded ports 3060/8767/8768.
   - Needed: a typed settings module, a root `.env.example`, and `tzdata` declared as a dependency.
7. **Dockerfiles and compose.**
   - Needed images and services:
     - one Python image built from `uv.lock` (`--frozen`) for both API and worker;
     - a Next.js image (`npm ci` already runs `prepare:pdfjs`);
     - PostgreSQL, a one-shot migration job, and a read-only mount for `raw/`.
   - Inside the containers, servers must bind 0.0.0.0 while the host publishes only on 127.0.0.1.
   - The three loopback guards must become configurable.
8. **Observability.**
   - Today: `logging.basicConfig` in the jobs and the `collector_runs` table. The health endpoint is expensive because it re-hashes the bundle.
   - Needed:
     - structured logs, a job-run ledger, cheap liveness and readiness endpoints;
     - data-freshness checks (latest as-of date per fund) and error reporting.
9. **B2B API surface:** none exists.
   - Proposed endpoints:
     - `/v1/funds`, `/v1/funds/{code}`, `/v1/funds/{code}/nav?from&to`, `/v1/funds/{code}/signals`;
     - `/v1/signals?date&detector&status`, `/v1/events`, plus CSV/bulk exports.
   - Also needed: OpenAPI docs, pagination, rate limits, usage metering, and data-mode labels on every response.
   - The handoff's `contracts/event.schema.json`, `evidence.schema.json` and `public_event.schema.json` are candidate payload shapes.

## 8. Collisions and decisions needed

1. **Development/test split and the 1,922 unopened price files.**
   - The project rule says to compute nothing on them until the split is decided, but the product needs all funds.
   - Options: approve the company split and keep the sealed-test companies out of the product; give up the sealed test; or keep the product to the 100 opened funds.
   - Who decides: **Safa (repository owner) with Mirza.**
2. **Keeping the demo intact.**
   - Editing registered files, switching branches, pulling, or touching `raw/snapshots/fund_snapshots.sqlite3` in the main checkout makes the demo answer 503.
   - Build the product in new modules, preferably in a separate worktree or clone.
   - Who decides: **Mirza.**
3. **Auth model.**
   - The handoff requires Google-only Supabase sign-in, and DEC-020 says "no service accounts". A localhost B2B product needs API keys and local sessions.
   - Who decides: **Mirza** (Safa for the customer model).
4. **Data rights for selling TEFAS, KAP and MKK data, or products built on it.** They have not been reviewed.
   - **Safa action:** a terms or legal check.
   - Until then, the data stays on localhost only (DEC-027).
5. **License of the Bilun-derived primitives** ("proprietary… all rights reserved").
   - **Safa** confirms product use, or **Barış's** components replace them.
6. **The insurance idea.**
   - Pricing a policy needs a calibrated event probability. The handoff rules say confidence is not a probability.
   - The repository has one labelled event cluster (the 17 September 2026 SPK order, 131 funds, `liquidated_funds.json`). It has no history of size or investor counts before 2026-10-09, apart from KAP data for 101 funds.
   - Insurance regulation and licensing were not checked (unverified).
   - Who decides: **Safa and the team.**
7. **Rights gate on the AN-FND-002/004 admission path** (APPROVED required).
   - Decide whether localhost product screens may show research screens with rights `UNKNOWN`.
   - Who decides: **the team.**
8. **Forward collection scope.** `--tefas-only` collects 1,071 funds. Collecting all ~2,133 roughly doubles the run time.
   - Who decides: **Mirza.**

## 9. Unverified

- the 65 executed browser tests;
- the cause of the 605-versus-663 test count difference;
- whether the systemd timer is installed on the owner's laptop;
- the KAP backfill estimate at scale;
- whether TEFAS has a bulk daily all-funds endpoint (not tested in `research/spikes/2026-10-06-tefas/REPORT.md`);
- base-image details for Docker;
- regulation of B2B data sales and of insurance products.

No web sources were used.

## Key absolute paths

- C:\Users\mirza\Desktop\Hackathon\project-50k\services\p50k\providers\tefas.py
- C:\Users\mirza\Desktop\Hackathon\project-50k\services\p50k\providers\kap_report.py
- C:\Users\mirza\Desktop\Hackathon\project-50k\services\p50k\jobs\fund_snapshots.py
- C:\Users\mirza\Desktop\Hackathon\project-50k\services\p50k\detectors\fund_flow.py
- C:\Users\mirza\Desktop\Hackathon\project-50k\research\events\2026-09-17-spk-liquidations\price_detectors\detectors.py
- C:\Users\mirza\Desktop\Hackathon\project-50k\services\p50k\research_reviews\concentration.py
- C:\Users\mirza\Desktop\Hackathon\project-50k\services\p50k\api\app.py
- C:\Users\mirza\Desktop\Hackathon\project-50k\tests\unit\registered_sources.lock.json
- C:\Users\mirza\Desktop\Hackathon\project-50k\frontend\src\app\globals.css
- C:\Users\mirza\Desktop\Hackathon\project-50k\frontend\next.config.ts
- C:\Users\mirza\Desktop\Hackathon\project-50k\frontend\src\components\FundChart.tsx
- C:\Users\mirza\Desktop\Hackathon\project-50k\frontend\src\components\PdfViewer.tsx
- C:\Users\mirza\Desktop\Hackathon\project-50k\docs\handoff-v0.5\contracts\domain_tables.json
- C:\Users\mirza\Desktop\Hackathon\project-50k\docs\handoff-v0.5\contracts\openapi.yaml
- C:\Users\mirza\.local\share\project-50k\fund_snapshots_forward.sqlite3