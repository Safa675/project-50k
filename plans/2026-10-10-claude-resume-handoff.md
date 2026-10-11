# Claude takeover: BlackSwan / Project 50K

Prepared for Mirza at approximately **2026-10-10 21:45 Europe/Istanbul**. Read this
whole file before acting. It preserves the released product and the unfinished
product work. Do not restart from the original hackathon handoff or discard the
working tree. Mirza requested this handoff because Codex usage is running out.

## 1. What Mirza wants now

You are taking over from Codex. Mirza is technical lead, Safa business/repository
owner, Barış designer. Reply in concise English. Do the work; do not repeatedly
ask permission for already-authorized implementation, Git, source downloads or
bounded OpenAI use. Parallelize independent work with separate file ownership.

Latest direction, in order:

1. BlackSwan sells evidence data and API access to banks/financial institutions.
   Insurance is permanently deferred. Turkish funds **and stocks** are required.
2. The product must feel complete to a nontechnical user, not like an MVP or
   research/debug console. No visible hashes, internal evidence IDs, detector
   codes, storage names, raw enums or meaningless `Değer: Veri yok / Eşik: Veri yok`.
   Mirza explicitly removed `Veri hakları incelenmedi` from end-user screens;
   rights remain unreviewed in operational documentation/API metadata.
3. Explain how conclusions are reached beside each result, in ordinary Turkish:
   inputs, dates, comparison, meaning, limits, then calculation → AI → human review.
4. Chat must be useful, streamed, persisted per asset, recoverable after returning
   or reloading, and support Enter to send / Shift+Enter for newline / IME input.
5. Fix illogical UX. `Tüm fonlar` must show the fund catalog, with `Gelişmeler` a
   separate results view. A genuinely within-threshold result is different from
   missing data or an analysis not yet run. Find existing data before showing
   `Dönemsel seri yok` or similarly empty states.
6. Default the analysis to **12 September 2026**, clearly shown in the navbar.
   Run the actual pipeline without later observations/events or tuning to known
   outcomes. Do not force the eight case funds to trigger. Mirza wants a genuine
   pre-event evidence view, not a hardcoded story.
7. Mirza authorized using more of the existing API budget for actual pipeline
   work. This means budgeted inference, not fine-tuning on later outcomes. The
   existing $25 target/internal bucket controls remain; no new accounts/hosting.
8. **Product first.** Mirza explicitly said to stop spending time on repeated
   Linux regressions/backups/meta work. Use focused data-isolation and product-flow
   checks. The handoff itself is expressly authorized; no new features should be
   started during handoff preparation.

No unanswered critical product approval blocks the current integration. All
original four takeover questions were answered: derived-only OpenAI scope,
all downloads immediately, app worktree, and closest fund identity confirmed.
Ten exact mapping checks were later authorized and completed. The old alignment
pause was explicitly resumed. Mirza delegates **all Git operations** to agents.

## 2. Read order and immutable boundaries

Read `AGENTS.md`, this file, `docs/notes/current-state.md`, then:

- `docs/decisions/DEC-031-derived-evidence-openai-egress.md`
- `docs/decisions/DEC-032-b2b-evidence-data-api.md`
- `docs/decisions/DEC-033-nontechnical-product-experience.md`
- `docs/decisions/DEC-034-product-depth-historical-context.md`
- `docs/notes/replay-2026-09-12-intent-2026-10-10.md`
- `docs/notes/replay-2026-09-12-result-2026-10-10.md`
- `docs/notes/blackswan-user-experience-completion.md`
- `plans/2026-10-10-product-build-plan.md`, `docs/notes/team-asks.md`.

The original `plans/2026-10-10-codex-handoff-prompt.md` and `docs/notes/product-direction.md`
provide history. Do not treat stale milestone text as a new pause or pending key.
Before provider work read `research/spikes/2026-10-06-tefas/REPORT.md`. Before any
math work read the existing protocol; this task does not authorize altering it.

NEVER edit `docs/handoff-v0.5/**`, frozen detectors/results, any committed
`PROTOCOL.md`/`PREREGISTRATION.md`, `raw/**`, registered-source paths, dated modules
or event `run.py` files. **Also do not edit** `services/p50k/product/detector_pipeline.py`
or `detector_math.py`: their bytes bind the real calibration. New wrappers/modules
are permitted. No recalibration occurred in this work. Never change a registered
negative result to match a known later outcome.

No real TEFAS/KAP values in Git. Only the eight approved case fund codes may be
named as flagged in committed prose: THF, TP2, TLY, DFI, DOH, PRY, KHA, PNU.
Other source data/results stay in ignored/external storage. Tests use synthetic
data. Missing stays missing; publication time gates use. LF/UTF-8 is mandatory.

Never read/print secret contents, `.env`, credentials, or full Docker config/env.
Runtime clients may consume mounted secret files normally. The OpenAI key exists
at `C:\Users\mirza\Desktop\Hackathon\project-50k-app\secrets\openai_api_key`.
Do not ask Mirza for it again. OpenAI sends only approved derived evidence, never
raw NAV/KAP text/AUM/units/investor counts/private review information. `store:false`.
No advice, fraud allegations, validated accuracy or proven prediction claims.

## 3. Exact repository and runtime state

**Build here:** `C:\Users\mirza\Desktop\Hackathon\project-50k-app`, branch
`product/build`. This is a linked worktree of the same `Safa675/project-50k` repo.

- Main: `C:\Users\mirza\Desktop\Hackathon\project-50k`, branch `main`.
  Main and remote main last verified **`9a2a993`**. Never switch its branch.
- Integration: `C:\Users\mirza\AppData\Local\Temp\p50k-phase1-merge-20261010`,
  branch `product/phase1-merge`, also `9a2a993` before this handoff.
- Last released app source: **`84438f7`**; verification/docs commit **`e65c8e6`**.
  Latest in-progress work is being checkpointed on `product/build` with this
  handoff. Run `git log -3 --oneline` to obtain its exact checkpoint hash.
  **Do not infer that a newer branch commit has been deployed or merged.**

Running at handoff:

| Runtime | Address / scope | State |
|---|---|---|
| Real product web | http://127.0.0.1:3070 | Healthy, last released image, current/live view |
| Real product API | http://127.0.0.1:8770 | Healthy, live AI, 11 migrations |
| Product PostgreSQL | loopback 5433; DB `p50k` | Preserve volume |
| Smoke web/API | 3071 / 8771; DB `p50k_dev` | Healthy older images; **DB already has migration 012** |
| Dev preview | http://127.0.0.1:3000 | Node PID 28080; source edits visible, synthetic API 8771 |
| Frozen fallback | 3060 / 8767 / 8768 | PIDs 27116 / 19280 / 32216, unchanged |

Fallback runs from `project-50k-dated`; it hashes main's registered files. Never
stop it or build into its served `.next`. Do not run host `npm run build` in the
app while port 3000 serves its `.next`; build Docker images instead. Do not touch
unrelated Solvequill containers/ports or other repositories.

No known download or paid job is running. Last read-only job check: two
`SUCCEEDED`, zero `READY`/`RUNNING`; zero reserved AI balance. Agents have finished
or hit Codex usage limits. Do not wait for them. One short final targeted check
may have finished during handoff; its exact result is appended below.

## 4. Released product already works

Do not rebuild these from scratch:

- Next.js/React product in **`web/`**, FastAPI `services/p50k/product/`, PostgreSQL,
  owner/app DB roles, own email/password login, session+CSRF, worker and Docker.
- Catalog/detail/NAV charts, immutable 8-result fund evidence, human overrides,
  bounded live AI proposals and chat, protected API docs, institutional workflow.
- All **22 Figma frames** implemented (10 base states +12 contextual variants),
  exact logo/icons/tokens/font. Full node links/map are in
  `docs/notes/figma-implementation-2026-10-10.md`; Figma access was resolved.
  Current Codex tools lost the Figma connector during usage transition; local
  assets/code/docs preserve it, so no Figma access is needed for current fixes.
- Watchlists, notifications/preferences/read state, evidence feedback persist.
- Plain-language method disclosures, dated last usable price, technical text
  removed, stock chart visibility fixed. Timestamp timezone hydration bug fixed.
- 87 genuine local brand assets: 30 stock issuers, 57 managers, covering
  2,113/2,133 funds. Twenty entries show their actual code where source branding
  was unavailable. Provenance is `web/public/asset-logos/provenance.json`.
- Validated paragraph streaming: model output is incrementally parsed and checked,
  paragraph audit saved before display, then final answer consistency checked.
  No fake typing delay. Migration 011 is on real product.
- Last full released checks: 16 browser passed; 21 web units passed; 831 Linux
  passes/73 skips, frozen 9+88 passed. Do **not rerun broad Linux suites now**.

Live quality history: chat v4 had 3/3 valid useful answers, first paragraph
2.518–2.827s, total4.279–4.824s. Materiality v3 had 8/8 first-attempt valid,
readable supported outcomes across eight categories, cost$0.049235. This is a
small development sample, not measured predictive accuracy. New scoped/blinded
versions in pending work have not yet had their live historical pass.

## 5. Real data, replay facts and source gaps

External input root:
`C:\Users\mirza\.local\share\project-50k\overnight\2026-10-10\`.
All authorized downloads completed: 2,133 snapshot rows; 2,134 profile files
(one failed, five empty); 2,129 price files including reused smoke files (four
failed); 194 SPK PDFs; 1,071-fund KAP list cohort finished. Preserve source gaps.
TEFAS pace1.5s; KAP pace6s, one stream per host. New downloads only external
overnight paths, not `raw/` modifications or Git.

Product totals before the historical run: 2,133 funds, 1,755,010 price rows,
3,304 snapshots, 12,111 KAP document entries, 1,255 parsed KAP series, one fixed
calibration. 131 identity-confirmed events have unknown publication times;
they remain ineligible to trigger. Existing live detector run
`4dcee718-6c5b-4506-b251-2ed563260b60` had17,064 signals.

**The new September12 run has actually executed and is in the real database.**

- Run `23d372f2-dfa0-43ac-97a8-ee6d92fe7e26`, origin `HISTORICAL_REPLAY`.
- Cutoff `2026-09-12T23:59:59+03:00`; last observation day Sept11.
- 2,133 funds /17,064 results /35.67s. Same existing one calibration:
  `all-funds-v2-e8cf9c22c8ba3d47`, calibration data before2025-10-06.
- THF, TP2, PRY, PNU: **D1 triggered**. TLY, DFI, DOH, KHA: **no price trigger**.
  PNU D2 abstains; all eight regulatory checks abstain; all eight data-quality
  checks do not trigger at this earlier date.
- Whole universe69 price-behavior-triggered funds (65 outside case eight);
  189 any-triggered funds (185 outside eight). Not a verified false-positive rate.
- All audits: zero future observations/references/events, no unknown-time trigger,
  no D5 warning. Full aggregate/target table in replay result note.
- Private run details: `%TEMP%\blackswan-replay-20260912-e292e93cb5064de99b745349878ef326\`
  (`preflight.json`, `run-result.json`, `aggregate-summary.json`,25.5MB
  `per-fund-evidence.private.json`). Keep out of Git.
- Honest limits: protocol designed after event; Oct6/current category/catalog;
  retrospective revisions unverified; NAV publication11:05 assumption. Do not
  present it as proven blind prediction. Historical AI now blinds fund identity
  and separates conversations, but no LLM pretraining-hindsight guarantee exists.

**Monthly data found and wired in pending code:** all eight targets have usable
pre-Sept12 KAP units/total-value reports. THF11monthly, TP2 11monthly (Oct2025–
Aug2026), TLY12(10monthly+2weekly), DFI13(11+2), DOH12(10+2), PRY12monthly,
KHA11monthly, PNU6monthly. THF/TP2 August reports published Sept2 11:02:16
Istanbul. All admitted by publication time; no new PDF download needed.
Investor-count history is **not** in KAP or TEFAS historical endpoints: only
undated/current TEFAS snapshots. Do not invent it. Weekly report end dates and
reported-value currency are not established; show table/unknown appropriately.

**Stocks:** existing immutable ForInvest v1 contains30 current BIST30 members,
870 daily closes (29 each, Sept1–Oct9), five corporate-action observations,
capturedOct10 15:34:41UTC; adjustments unverified. Capture-only availability means
these records are correctly excluded in September mode. Do not backdate them.

**New official stock-source discovery, NOT IMPLEMENTED/IMPORTED:**
`https://borsaistanbul.com/data/thb/2026/09/thb202609111.zip`
is the official Sept11 daily bulletin. Download200,293981bytes,
SHA256 `77c8e0150349c4e69865306a9d444dc4bc1dcb30ec1b53b9ee68d3978f76acf6`.
HTTP Last-Modified Sept11 15:28:06UTC (18:28Istanbul); innerCSV timestamp18:25:28.
11,010 rows all trade dateSept11, exactly30 `BIST30INDEX=1` rows (EQT/MSPOTEQT),
all have closing prices. Historical membership overlaps current list29/30.
Files under external `bist/pit-research-20260912/`: `thb202609111.zip`,
`september11-capture.json`, `september11-structure-check.json`,
`september11-public-path-check.json`, `membership-comparison.json`,
`DataFilePaths.zip`, `directory-capture.json`.
Official path pattern from directory ZIP: `/data/thb/YYYY/AA/thbYYYYAAGGS.zip`.
Session1 worked, session2 returned404. A **new separately recorded versioned
protocol/admission rule** is needed before import; publisher modification time
is evidence, not independently proven first-publication time. Preserve v1.
This is a concrete route to historical stock coverage without pretending the
current membership was historical. Do not start it until current integration is
stable; Mirza halted new feature starts for this handoff only.

## 6. Pending code already written (not deployed)

All changes are in the app worktree. `git show --stat` on the handoff checkpoint
or `git status` before checkpoint gives exact paths. Preserve them.

### Selected date and actual run queue — root-owned

- `analysis_context.py`: ContextVar-scoped `current_cutoff(settings=None)`,
  `analysis_scope_key` (`live` or`asof:YYYY-MM-DD`), `historical_mode`,
  `use_analysis_date`, `data_origins`, `public_context`. Real auth/budget clocks
  are not changed. Date range2025-10-06..real today. Invalid cookies reset safely.
- `context_routes.py`: public GET `/context`; authenticated/CSRF POST `/context`
  `{date:'YYYY-MM-DD'|'live'}` sets HttpOnly`p50k_as_of` cookie30days.
  Response date/cutoff/mode/scope/today/timezone/analysis_status.
- `Settings.analysis_date` default `live`; **compose.yaml now defaults
  P50K_ANALYSIS_DATE to2026-09-12**. Smoke must explicitly set`live` unless seeded
  for historical tests. This Compose change has NOT been applied to running apps.
- `analysis_jobs.py`: dedup actual fixed-calculation jobs for chosen date, bounded
  queue3. `/context` returns ready/queued/running/failed/not_started/unavailable.
  Worker now handles `analysis_replay` plus `ai_decide`; same frozen math.
- Routes/queries/chat/decisions/watchlist now use selected cutoff and replay origin;
  exact-day checks prevent silently substituting another historical run.
  `/signals` adds literal bounded q/category filtering. Historical fund status is
  hidden because it came from the later current catalog.
- AI evaluate now accepts bucket`batch` and max_calls=1; queue payload saves date
  scope and batch bucket, worker restores it. New materiality prompt version
  `materiality-v4-scoped-evidence`, anonymous historical input. **No historical AI
  batch has run** and no extra budget was spent on this unfinished turn.
- Workflow was partly adapted to historical run/proposal counts. See remaining
  integration gaps below; do not assume every date-boundary path is complete.

### Persistent chat — agent-owned, tests below

- Migration **012_chat_analysis_scope.sql is already applied to p50k_dev**,
  NOT realp50k. Treat its bytes as immutable. Existing threads default `live`.
- Owner+fund+scope latest/list/history, automatic reuse, explicitnew conversation,
  bounded pagination (60 messages/page, 20 threads/page), failed questions retained,
  only validated assistant responses restored, no cross-user/fund/date access.
- GET `/chat/threads?fund_code=...&limit=20&offset=...`; GET `/chat/{id}` supports
  `before_message_id`. Stream first emits `thread` with ID+scope; parser updated.
- ChatPanel restores history and thread selector, retrieves older messages,
  Enter-to-send/Shift+Enter/IME guards, clears/aborts on date change. It accepts
  `analysisScopeKey`, wired from server User context on fund/detail pages.
- Prompt`chat-v5-scoped-history`; historical questions/recentquestions and packet
  hide fund identity; only get_signals/get_decision tools, model FUND maps back
  internally. `chat_tools.load_context` is cutoff/origin-bound.
- **Stock chat is not implemented**; persisted conversations currently fund-only.

### Catalog / navbar / data-rich fund pages — agent-owned

- Default`/funds` and`Tüm fonlar` = complete paginated catalog50/page.
  `/funds?view=developments` = separate actual results feed25/page. q/category and
  view survive tabs/pagination; changed filters reset offset. No hardcoded target flags.
- Navbar `DateContextControl`: SSRdate thenGET/context, date/live selection,
  pending-job polling2s, explicit retrospective date, real system date distinct,
  `blackswan-analysis-change` event clears chat, full reload on date change.
- Hisseler now primary nav. States distinguish computed normal, absent input and
  unexamined. Empty periodic fauxcards removed from main flow.
- New `fund_series_routes.py` registered in app: bounded authenticated GET
  `/funds/{code}/series?cutoff=&limit=60&offset=`. Decimal strings, dated monthly/
  weekly values, source link, exact publication cutoff/revision handling and
  specific source/parser/publication coverage. No values are sent to OpenAI.
- `FundReportSeries.tsx`: actual monthly size/unit charts with missing-period
  breaks; weekly table because the exact end date is unknown; no currency guess. Legitimate
  reported zero remains zero. Realdata tested all eight case funds read-only.

## 7. What remains immediately — highest priority

1. Inspect current checkpoint/diff and run only focused integration checks. Do not
   launch blanket Linux regression/backup work. Preserve currently healthy release.
2. Complete selected-date end-to-end boundaries. Check these explicit review gaps:
   - `/workflow` run selection does not yet enforce exact chosen historical day;
     other primary selectors do. Avoid older-run substitution while a date job waits.
   - Date-job enqueue does not yet retry a failed idempotent job; UI truthfully
     avoids claiming it can. Decide small safe retry behavior if needed.
   - Verify ContextVar survives POST+StreamingResponse iteration/threadpool; older
     scope must never reappear after a date change. All date-setting paths require
     auth+CSRF; never trust a client-supplied thread scope.
   - Explicit cutoff overrides are rejected if later than selected historical day;
     earlier explicit queries may need origin/date selection review.
   - Prevent any current proposal/event/status/stock action from leaking into
     historical pages, chat tools/history, watchlist, notifications or workflow.
   - Exact historical stock coverage is intentionally absent under currentv1;
     use new BIST source via a separately recorded v2 rather than changing v1.
   - `analysis_status` checks the actual persisted replay date/version. Verify
     queue claims/dedup/lease and worker job payload scope with one synthetic case.
3. Build API/web Docker images after sources are coherent, apply/verify migration012
   in smoke (already applied), set smokeanalysisdate`live`, and test catalog/date/
   monthlyseries/chat-history+Enter flows. New tests exist in
   `web/tests/browser/catalog-flow.spec.ts` and `chat-history.spec.ts`.
   Historicalbrowser tests need a synthetic historicalrun; do not substitute real
   data in test fixtures. Existing tests assuming old defaultfeed may need updates.
4. Run a small genuine historical AI pass through batch budget, anonymous model
   input, fixed evidence and originalhuman review preservation. Use all outcomes
   honestly. Tuning quota is not a normal product gate. Existing batch bucket $5
   exists; actual overall cost ~$0.30 leaves plenty within the approved target. No need to
   train on labels or include later scandal names in prompts.
5. Roll out new images on3070/8770 with live AI and default Sept 12 only after focused
   checks. Verify THF Sept 11 price / D1 signal, its pre-Sept 12 monthly reports, restored chat,
   navbar date, current mode stockprices, and coherent catalog/results tabs.
6. Finish historical stock source v2 as a separate next slice if requested continuation
   allows; source alreadyfound. Realstockanomalyclassification/AI, optional
   challengercommittee and bankproductionintegrations remain unimplemented.

Useful commands from app worktree (PowerShell; never print secret values):

```powershell
# Product-only focused build
docker compose -f compose.yaml build api web

# Smoke settings — explicit live because compose default is now September12
$env:P50K_DB_NAME='p50k_dev'; $env:P50K_ANALYSIS_DATE='live'
$env:P50K_API_PORT='8771'; $env:P50K_WEB_PORT='3071'
$env:P50K_AI_MODE='off'; $env:P50K_TEST_ENDPOINTS='true'
docker compose -p p50k-smoke -f compose.yaml up -d --no-build --wait --wait-timeout 60

# Real rollout: use a fresh shell or clear smoke-only environment overrides first
$env:P50K_DB_NAME='p50k'; $env:P50K_ANALYSIS_DATE='2026-09-12'
$env:P50K_API_PORT='8770'; $env:P50K_WEB_PORT='3070'
$env:P50K_AI_MODE='live'; $env:P50K_TEST_ENDPOINTS='false'
docker compose -f compose.yaml -f compose.override.yaml -f compose.dev.yaml -f compose.ai.yaml up -d --no-build --wait --wait-timeout 60
```

The local override/dev/ai files are ignored machine configuration; do not dump
them or Docker resolved environment. No `down -v`. Re-seed synthetic browser data
after database tests if they inserted latest/future fixtures:
`docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm --volume ./secrets/auth_pepper:/run/secrets/auth_pepper:ro migrate python -m p50k.product.smoke_seed`
with the smoke env above. The stock synthetic fixture comes from `stock_import` seed;
check CLI before use. Chrome is installed; Playwright uses channel`chrome`.

## 8. Tests, budget, backups, Git and final operational reminders

Current unfinished slice checks actually completed:

- Root final handoff `npm run typecheck`: exit0; `npm test`: **30 passed / 6 files**.
- Replay: five targeted causal/calibration checks passed; real database audit above.
- KAPseries: nine tests passed, zero skips including real isolated PostgreSQL;
  all eight case funds read-only real coverage verified.
- Chat agent: 19 targetedPython tests passed, zero skips, then pagination case added;
  final root check result appended below. Frontend history/stream: 12 tests passed.
- Root intermediate 47 selected Python checks:35 executed passes, 12 DB skips.
  Do not report skipped database checks as passes.
- Catalog manual flow and 390px mobile checks passed against synthetic dev; new date/status/history
  and monthly API **not yet integrated in built images**. No final browser pass claimed.
- Synthetic migration failure tests renamed to013 after allocating 012; no migration
  byte change. No new stock protocol/import or historical paid batch has been run.

At 21:41 Istanbul, real runtime:11 migrations, 32 paid calls, total conservative booked cost
**USD0.2995650**,zero reserved, 2 SUCCEEDED jobs and no active jobs. This differs from the
20:59 release checkpointUSD0.267445 because subsequent actual use occurred.
Do not assume old budget counts; inspect ledgers read-only when needed.

Latestverifiedbackup predates this new historical run:
`backups/p50k-20261010T180646Z-c6a0b94390324035849de26df9ea8875.dump`,
SHA `71c3ec93fb8926265be29931a7d05392ca2e5df9f7c7122c7f01e3b0d5618c19`,
39 tables / 11 migrations,34,419,956bytes. Preserve the product DB volume and external archives;
do not restore an older backup over it. The backup script TCP readiness race is already fixed.
No new backup was requested for this product slice; Mirza wantsproduct work.

**Before every commit, including merge commits**, run:

```powershell
$env:PYTHONUTF8='1'
$env:P50K_RAW_DIR='C:\Users\mirza\Desktop\Hackathon\project-50k\raw'
.venv/Scripts/python.exe .claude/skills/p50k-leak-scan/leak_scan.py
```

Exit 1/2 blocks. The scanner prints positions/counts, not real values. Check protected-path diffs
before merging/pulling main: lockfile paths +frozen handoff/raw/dated modules/event
protocols/runners +calibrated detector pipeline/math. Merge via the integration worktree
with `--no-ff --no-commit`, scan, commit, push `product/phase1-merge:main`,then safely
fast-forward main without switching branches. Never squash/force-push. The WIP checkpoint is not a release;
do not blindly merge it into main before integration.

PowerShell 5.1: use `Get-Content -Encoding utf8 -LiteralPath` for bracket paths.
Use apply_patch for Turkish text; PowerShell stdin Unicode can corrupt it. `rg` before grep.
Do not repurpose $HOME. No recursive filesystem moves/deletes. System timezone can be
UTC inside Docker; render dates explicitly Europe/Istanbul (prior hydration bug).

Feature freeze Sun 2026-10-11 10:30,code freeze 13:00Istanbul remain the historical schedule;
the latest user request prioritizes a full product experience. Do not use the timeline to silently
drop requested functionality or invent missing data. Keep concise progress updates
focused on product outcomes, tell Mirza actual blockers, and record material decisions.

## 9. Handoff checkpoint status

This handoff and all pending source files are being saved together on product/build.
Main/running images remain the previous verifiedrelease. The final Codex message will
name the checkpoint commit and whether push succeeded. If a checkpoint is not committed,
the files still remain intact; inspect git status before any action. No tool/agent promise
should be assumed running after this handoff.

Final immediate check completed during handoff:

```text
P50K_DB_NAME=p50k_dev P50K_ANALYSIS_DATE=live
docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm -e P50K_TEST_ENDPOINTS=true -e P50K_TEST_DATABASE=1 --volume ./tests:/app/tests:ro --volume ./services:/app/services:ro worker python -m unittest tests.unit.test_product_chat tests.unit.test_product_fund_series -q
Ran 29 tests in 9.709s; OK; zero skips
```

This includes the newly added history pagination tests. The command finished;
no corresponding one-off container or process is left running. The test data
remains only in `p50k_dev`. No new feature or production rollout occurred during
handoff preparation.
