# Morning sprint briefs (2026-10-11)

The eight workstream briefs Claude wrote for the 2026-10-11 morning sprint. All three runs were cut off: session limits, then a network outage, then session limits again. Partial work is in the `product/build` WIP checkpoint. Each brief is a complete spec; follow `plans/2026-10-11-codex-handoff-prompt.md` for status and priorities.

```js
export const meta = {
  name: 'blackswan-morning-sprint-3',
  description: 'Eight parallel BlackSwan workstreams (panel, review, method, header/avatar/favicon, stocks, results, fund warnings, demo mode), each reviewed and fixed',
  phases: [
    { title: 'Build', detail: 'eight owners build in parallel in the app worktree' },
    { title: 'Review', detail: 'fresh reviewer per workstream' },
    { title: 'Fix', detail: 'apply critical and high findings' },
  ],
}

const APP = 'C:\\Users\\mirza\\Desktop\\Hackathon\\project-50k-app'
const SCRATCH = 'C:\\Users\\mirza\\AppData\\Local\\Temp\\claude\\c--Users-mirza-Desktop-Hackathon-project-50k\\fcb59ff2-d20e-4984-b01d-14d47f0bf736\\scratchpad'

const COMMON = `
You are one of eight parallel builders for BlackSwan (Project 50K) at a hackathon. Hard deadline: return your final report by 11:15 Istanbul time (run \`date\` in Bash to check; the machine clock is Istanbul time). Partial but working beats ambitious and broken.
- RESUMING: a previous attempt of all eight builders was cut off by a network outage around 10:05. Partial work is already in the worktree (\`git status --short\` and \`git diff\`; untracked files too). First inspect the files you own: keep what is correct, finish what is missing, fix what is half-written. Do not delete or rewrite other builders' partial work. Network can drop again: save your work in files as you go.

Where and how:
- Work ONLY in ${APP} (git branch product/build). Other builders edit other files in this same worktree right now: touch only the files you own (listed below). If you must touch a shared file, make the smallest possible edit and say so in your report.
- Do NOT commit, stash, reset, checkout or otherwise change git state. Do NOT build Docker images, run docker compose up/down/restart, or stop/start containers. Do NOT run Playwright test suites (port 3071 is temporarily a shared dev server on the REAL API). Never run \`npm run build\` on the host.
- Shared dev server: http://127.0.0.1:3071 serves this worktree's web code with hot reload against the REAL product API and REAL data. For visual checks run: \`node ${SCRATCH}\\shots\\snap.mjs <path> <out.png> [--panel] [--full] [--width=390] [--height=712] [--light]\` (logs in as the QA analyst; never prints credentials). Save screenshots under ${SCRATCH}\\shots\\<your-workstream>\\ and look at them with the Read tool. If a page errors mid-reload because another builder is editing, wait a few seconds and retry.
- READ-ONLY against the real product: never submit forms, never post reviews, never ask the Raportör a question, never request an investigation, never call POST endpoints on 127.0.0.1:8770 or via 3071. Read-only SQL against the real database is allowed for understanding data: \`MSYS_NO_PATHCONV=1 docker exec p50k-db-1 sh -c 'psql -U "$POSTGRES_USER" -d p50k -c "SELECT ..."'\` (SELECT only, never print secrets or env).
- Python unit tests without a database: from ${APP} run \`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/Scripts/python.exe -m unittest tests.unit.<module> -v\`. Database tests run in the smoke container against the disposable p50k_dev database: \`MSYS_NO_PATHCONV=1 P50K_DB_NAME=p50k_dev P50K_ANALYSIS_DATE=live docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm -e P50K_TEST_ENDPOINTS=true -e P50K_TEST_DATABASE=1 --volume ./tests:/app/tests:ro --volume ./services:/app/services:ro --volume ./db:/app/db:ro worker python -m unittest <modules>\` (run from ${APP} in Git Bash; only your own test modules unless told otherwise). Web: in ${APP}\\web run \`npm run typecheck\` and \`npx vitest run\`.
- Product rules (binding): natural Turkish (tr-TR) UI copy, English code/comments/docs. No placeholders, lorem ipsum, fake values, "coming soon", mock AI output or notes to the team in the product (DEC-030). No investment advice, no fraud/manipulation/wrongdoing wording, an anomaly is not wrongdoing, missing data is not "safe". No hindsight: the 12 September view must not use information published after its cutoff, except on pages explicitly labelled as after-the-fact evaluation. Never put real TEFAS/KAP/BIST values in git (tests use synthetic fixtures). Only these fund codes may be named in committed prose: THF, TP2, TLY, DFI, DOH, PRY, KHA, PNU. Never edit docs/handoff-v0.5/**, raw/**, PROTOCOL.md/PREREGISTRATION.md files, services/p50k/product/detector_pipeline.py or detector_math.py.
- Design gate: dark theme default plus light theme (data-theme on <html>), use the existing CSS tokens/variables in web/app/design.css and globals.css, accessible primitives, visible focus states, keyboard support, 390px mobile width without horizontal scroll, good contrast. No generic gradients, neon, nested card grids or decorative "AI" badges. Make it look polished and calm, consistent with the existing BlackSwan pages.
- Match the surrounding code style (the web code is compact TSX; Python follows existing modules). Keep changes tight and well tested.

Your final answer must be the structured report: what you built, every file you changed or created, the exact checks you ran with their results, screenshot paths you produced, anything unfinished, and precise integration steps for the integrator (commands, migrations, env vars, data imports).
`

const REPORT = {
  type: 'object',
  properties: {
    workstream: { type: 'string' },
    summary: { type: 'string' },
    files_changed: { type: 'array', items: { type: 'string' } },
    checks: { type: 'array', items: { type: 'object', properties: { command: { type: 'string' }, result: { type: 'string' } }, required: ['command', 'result'] } },
    screenshots: { type: 'array', items: { type: 'string' } },
    unfinished: { type: 'array', items: { type: 'string' } },
    integration_steps: { type: 'array', items: { type: 'string' } },
  },
  required: ['workstream', 'summary', 'files_changed', 'checks', 'screenshots', 'unfinished', 'integration_steps'],
}

const REVIEW = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['ship', 'fix_then_ship', 'do_not_ship'] },
    findings: { type: 'array', items: { type: 'object', properties: {
      severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] },
      file: { type: 'string' },
      problem: { type: 'string' },
      fix: { type: 'string' },
    }, required: ['severity', 'file', 'problem', 'fix'] } },
    notes: { type: 'string' },
  },
  required: ['verdict', 'findings', 'notes'],
}

const STREAMS = [
  {
    key: 'panel',
    title: 'Agent panel layout',
    prompt: `Workstream: agent panel layout (the mascot dock window).
Mirza: "the ai agent window is nice but visually problematic, the bottom part is too small". In his screenshot (viewport about 1480x712) the five-agent graph (TeamStage) takes most of the panel height and the working area below (Raportör tab: page note column plus chat; Sıra; Vaka akışı) gets only about 200px: the chat shows almost nothing.
Build:
1. Give the working area most of the height at every viewport size. Recommended: the panel may use up to about 92vh; the team graph gets a compact "strip" mode (one row of the six participants with status dots and the flow connectors, roughly 72-100px tall, still clickable to open each workspace) that is used automatically when the viewport height is under ~900px or a tab detail is open, plus a clear toggle to expand/collapse the full graph ("Ekibi genişlet" / "Ekibi daralt"), remembered per viewer in localStorage inside try/catch. At 712px height the chat must show at least ~320px of conversation with the input always visible; the note column scrolls on its own; Sıra and Vaka akışı lists get the space too.
2. Remove the visible "Retrospektif inceleme" text from the panel header and the /ekip page: show only the date (e.g. "12 Eylül 2026" under "İnceleme tarihi"). The text comes from web/lib/agents.ts (mode: 'Retrospektif inceleme') and is rendered in the panel header and web/app/ekip/page.tsx. Keep accessible labels sensible.
3. Keep it "visually incredibly appealing": smooth height/opacity transitions (respect prefers-reduced-motion), consistent spacing, no clipping, the Raportör card still visually distinct.
Check at 1440x900, 1480x712, 1280x720 and 390x844 via snap.mjs with --panel on /funds/THF and on /. Keep web/tests/agents.test.ts passing; if you change accessible names used by web/tests/browser/agents.spec.ts, update that spec's selectors (do not run it).
Files you own: web/components/agents/** (AgentDock, AgentTeamPanel, TeamStage, ReporterTab, ReporterConversation, AgentQueue, AgentWorkspace, agents.css, hooks.ts), web/lib/agents.ts, web/app/ekip/**, web/tests/agents.test.ts, web/tests/browser/agents.spec.ts. Do not edit DesignShell, DateContextControl, review, method, stocks or funds pages.`,
  },
  {
    key: 'review',
    title: 'Review queue page',
    prompt: `Workstream: the /review page (İnceleme kuyruğu), visual and UX redesign.
Today web/app/review/page.tsx renders every proposal as a fund-code link plus the shared DecisionPanel (web/components/DecisionPanel.tsx): label, "Yapay zekâ önerisi..." line, rationale, "Dayandığı gelişmeler", and a heavy three-field form (İnceleme işlemi select, Değiştirilen karar select, Gerekçe textarea, İncelemeyi kaydet) repeated for every item. It is a long, monotonous wall of forms.
Build a proper review queue:
- Page header with clear counts and filter tabs ("Bekleyen" / "İncelenen" or similar) using data you actually have.
- Each proposal as a calm, scannable card/row: fund code and fund name, the proposal as a badge (use the existing decision labels), who proposed it ("Ajan ekibinin Raportör önerisi" when team_proposal is true, otherwise "Yapay zekâ önerisi"), the rationale clamped to two lines with an expand control, evidence links, a link to the fund page and to the fund's decision section (/funds/CODE#karar).
- Actions as clear buttons: "Kabul et" (one step; reason optional), "Değiştir" (reveals the decision select and a required reason), "Reddet" (reveals a required reason). Keep the existing server contract exactly: POST /decisions/{decision_id}/reviews with {action: 'ACCEPT'|'OVERRIDE'|'REJECT', override_value, reason}; ACCEPT may have no reason, OVERRIDE/REJECT need a reason. Use the existing client helper post() from web/lib/client.ts (it sends the CSRF header). After success show an inline confirmation and refresh (router.refresh()) so the item moves to the reviewed state; show plain error messages on failure.
- Viewer role keeps the "İnceleme yetkisi gerekiyor" state. Empty state when nothing waits: a short sentence plus a link to the agent team (/ekip).
- Look at what GET /review returns (services/p50k/product/decision_routes.py and decisions.py decision_rows; the Decision type in DecisionPanel.tsx; team_proposal exists). Fund names or timestamps: prefer what the API already returns; add a field in decision_rows only if needed, with a Python unit/DB test.
- DecisionPanel is also used on fund pages (web/components/FundDecision.tsx). You may restyle or refactor it for consistency, but keep its behavior and the "Ajan ekibinin Raportör önerisi; insan tarafından değiştirilebilir." wording, and keep fund pages working.
- NEVER submit a review against the real API. Verify client logic with vitest (mock fetch) if you add non-trivial logic.
Check /review at 1440x900 and 390x844 (dark and --light).
Files you own: web/app/review/**, new web/components/review/** (and a CSS module), web/components/DecisionPanel.tsx, web/components/FundDecision.tsx, services/p50k/product/decisions.py and decision_routes.py (minimal), their tests. Do not edit design.css (use a CSS module), DesignShell, agents, method, stocks.`,
  },
  {
    key: 'method',
    title: 'Method page',
    prompt: `Workstream: the /method page (Yöntem), visual redesign.
web/app/method/page.tsx is a long text-heavy page with small cards (sections: İzlenen değişimler, Veriler nereden geliyor, Hesaplamadan insan incelemesine, Veri durumları, Ne yapmaz, Sınırlar). Make it scannable, attractive and accurate:
- A clear hero; a visual pipeline of how BlackSwan works that matches the real always-on agent team (DEC-035, see docs/decisions/DEC-035-agent-team-and-reporter.md): data sources -> Nöbetçi (rule-based scan, opens cases) -> Hipotezci and Şüpheci in parallel (possible explanations and counter-explanations) -> Doğrulayıcı (code-computed tests) -> Raportör (auditable report and decision proposal; the only agent users talk to) -> İnsan kararı (accept, change with a reason, or reject; the first proposal is kept). Make it visual (steps, connectors, icons from web/public/design/*.svg), not a paragraph.
- Sources section with accurate scope: TEFAS daily fund prices, KAP monthly/weekly portfolio reports and announcements, SPK bulletins, BIST 30 daily stock prices. For stocks write neutral, accurate text: daily prices are admitted from the time the source published or the time we captured them, whichever is documented; the current BIST 30 list is not historical membership. (Another builder is adding the official Borsa İstanbul daily bulletin as a dated source; do not claim more than that.)
- Keep every integrity statement and limit already on the page (development results, not validated success or early warning; fixed comparison limits set from data before 6 October 2025; no advice; an anomaly is not wrongdoing; missing data is not safe; AI cannot change numbers or thresholds), but present them clearly (e.g. a "Ne yapmaz" panel and a compact "Sınırlar" section). Do not invent facts or numbers.
- Keep MethodTabs and MethodExplanation if they still fit; the per-detector explanations come from web/lib/method-explanations.ts.
- Add a short link to the new after-the-fact results page at /sonuclar ("Geriye dönük sonuçlar") built by another builder; plain link, no claims about its numbers.
Check 1440x900 and 390x844 in dark and --light (snap.mjs --full).
Files you own: web/app/method/** (create web/app/method/method.module.css for styles), web/components/MethodExplanation.tsx, web/lib/method-explanations.ts. Avoid editing shared design.css; if an existing .bs-method rule fights you, override it from your module.`,
  },
  {
    key: 'header',
    title: 'Header date, avatar, favicon, nav',
    prompt: `Workstream: navbar date chip, profile picture, browser-tab icon and a nav link.
1. Remove the visible "Retrospektif inceleme" text from the navbar date control (web/components/DateContextControl.tsx): show only the date (e.g. "12 Eylül 2026"); keep a good aria-label ("İnceleme tarihi: 12 Eylül 2026"). Search web/app and web/components (except web/components/agents/** and web/app/ekip/**, owned by another builder) for any other visible "Retrospektif" tag and remove it as a visible label without changing behavior.
2. Profile picture for Mirza's account (mirza@blackswan.local, admin) instead of initials in the header:
   - Migration db/migrations/014_user_avatar.sql: add nullable auth.users.avatar_path TEXT with a strict CHECK (e.g. NULL or ^/avatars/[a-z0-9][a-z0-9-]{0,39}\\.(jpg|png|webp)$). Additive only; follow the conventions of existing migrations (look at 012/013 and tests/unit/test_product_migrations.py, which may assert the list of migrations).
   - API: the current-user response (/auth/me; find it in services/p50k/product/auth_routes.py / auth.py / models.py) returns avatar_path (null when unset). Add a CLI subcommand to services/p50k/product/auth_cli.py to set or clear a user's avatar path by email (admin-only operation through the CLI), consistent with the CLI's existing style.
   - Web: the header avatar (web/components/DesignShell.tsx, and the User type in web/lib/auth.ts) shows a round photo (object-fit: cover, same size as the initials circle) when avatar_path is set, falling back to initials if the image fails to load; decorative img with alt="" and an accessible name on the control.
   - Photo: source ${SCRATCH.replace('scratchpad', 'images')}\\3.jpg (Mirza's portrait, about 1142x1172, face centered upper-middle). Crop a square around the face and resize to 192x192 JPEG with the system ffmpeg (on PATH) into web/public/avatars/mirza.jpg; look at the result with Read. Keep user photos out of git: add web/public/avatars/*.jpg (and png/webp) to the repo .gitignore; the Docker build context still includes web/** (check .dockerignore) so the image ships.
   - Tests: Python test for the avatar field and the CLI (follow existing auth tests; DB tests via the smoke container command for your modules only), web unit test if you add logic.
   - Do NOT apply the migration to any database yourself and do not set the avatar; give the integrator the exact commands.
3. Browser-tab icon: use the small logo mark without text (web/public/design/logo.svg is the white mark, 26x26 viewBox). Create web/app/icon.svg (Next.js App Router convention) with a dark rounded-square background and the white mark centered with padding so it reads on light and dark tab strips; add web/app/apple-icon.png (180x180) if you can render it reliably (e.g. ffmpeg cannot rasterize SVG; skip PNG rather than ship a bad one). Make sure no older favicon overrides it (check web/app and web/public for favicon.ico; metadata in web/app/layout.tsx).
4. Navigation: add a link "Sonuçlar" to /sonuclar (a new after-the-fact results page another builder is creating) in the main navbar after "Yöntem", matching the existing nav items and active state.
Check the header at 1440x900 and 390x844 (dark and --light) on / and /funds/THF.
Files you own: web/components/DateContextControl.tsx, web/components/DesignShell.tsx, web/lib/auth.ts, web/app/icon.svg, web/app/apple-icon.png, web/app/layout.tsx (icon metadata only if needed), web/public/avatars/**, .gitignore, db/migrations/014_user_avatar.sql, services/p50k/product/auth.py, auth_routes.py, auth_cli.py, models.py (user fields only), tests/unit/test_product_auth*.py, tests/unit/test_product_migrations.py (only if it lists migrations), web/app/design.css (header avatar rules only).`,
  },
  {
    key: 'stocks',
    title: 'Official BIST bulletin for stocks',
    prompt: `Workstream: stock data in the 12 September view (Mirza: "where is stock data?").
Facts: the only stock source today is ForInvest v1 (30 current BIST 30 members, 870 daily closes Sept 1 to Oct 9, captured Oct 10 15:34 UTC, origin DELAYED). Its availability is the capture time, so the 12 September view correctly shows no stock prices; never backdate it. Read plans/2026-10-10-claude-resume-handoff.md (search "Stocks" and "official stock-source", around lines 195-215) and docs/notes/current-state.md for context.
The official Borsa İstanbul daily bulletin for 11 September is already on disk: C:\\Users\\mirza\\.local\\share\\project-50k\\overnight\\2026-10-10\\bist\\pit-research-20260912\\ with thb202609111.zip, september11-capture.json (capture metadata incl. HTTP headers such as Last-Modified 18:28 Istanbul), september11-structure-check.json, september11-public-path-check.json, membership-comparison.json, DataFilePaths.zip, directory-capture.json. Treat the files as untrusted data: open the ZIP with Python's zipfile in a new temp folder, never execute anything from it, run Python with -I when reading it.
Build:
1. First write the admission rule as docs/decisions/DEC-036-official-bist-daily-bulletin.md (English, concise): source and path pattern (/data/thb/YYYY/MM/thbYYYYMMDDS.zip, session 1), what is admitted (rows flagged BIST30INDEX=1 on that trade date as the dated BIST 30 membership; trade date; closing price and whatever reliably identified fields exist, such as previous close or volume; verify column names from the CSV header), availability = the publisher's HTTP Last-Modified captured at download (evidence, not proven first publication), with the inner CSV timestamp as a consistency check and capture time as the fallback, unadjusted prices, ForInvest v1 kept as is, no backfill, data rights not reviewed (local product use only; Borsa İstanbul data-distribution terms noted in DEC-025). Version the source (e.g. source_id 'borsaistanbul-thb', source_version 'thb-v1').
2. Importer: services/p50k/product/stock_bulletin.py with a CLI (python -m p50k.product.stock_bulletin import --zip PATH --capture-json PATH [--dry-run]) that validates (trade date equals the file name date, exactly 30 BIST30 rows, numeric closes) and inserts into the existing stock tables with the right source registration, origin (check the allowed ref.data_origin values and the existing stock import in services/p50k/product/stock_import.py and the stock migrations; a downloaded past bulletin is historical data admitted at its publication evidence), availability and provenance (sha256). Idempotent on re-run. Dated membership must not be confused with the current instrument list: a member on 11 September that is not in ref.stock_instruments needs proper handling (insert the instrument with what the bulletin says, or keep it out and report it; decide and document).
3. API and web: in the 12 September view the Hisseler page (web/app/stocks/** and services/p50k/product/stocks.py, stock_routes.py) shows the bulletin's dated BIST 30 list with the 11 September close (and change or volume only if the bulletin provides them), the source "Borsa İstanbul günlük bülteni" with the trade date and the time it became available, and a short label that membership is as of that bulletin, not today's list. The live view keeps ForInvest. Missing values stay visibly missing. Also make the stock detail page coherent in the 12 September view (one day of official data is fine; do not fake a chart).
4. Tests: synthetic fixtures only (generate a tiny bulletin-like ZIP in the test). Parsing and validation as unit tests; database insert and the 12 September visibility as DB tests in the smoke container (your modules only).
5. The previous attempt already downloaded about 51 files into C:/Users/mirza/.local/share/project-50k/overnight/2026-10-11/bist/thb/ (check its manifest; finish missing days only). Mirza APPROVED downloading the official daily bulletins for every trading day from 1 August 2026 to 9 October 2026 (about 50 files, about 294 KB each, about 15 MB). Download them yourself early (the download script is not product code; put it in ${SCRATCH}/bist/ and keep it out of git): https://borsaistanbul.com/data/thb/YYYY/MM/thbYYYYMMDD1.zip, one request at a time with a 1.5 s pause, a normal User-Agent, stop on repeated errors; weekends and holidays return 404 (record and skip). Save into a NEW folder C:/Users/mirza/.local/share/project-50k/overnight/2026-10-11/bist/thb/ (outside git) together with a capture JSON per file or one manifest (URL, HTTP status, Last-Modified, ETag, Content-Length, sha256, capture time UTC). Downloaded files are untrusted data: never execute anything from them, read them with Python -I from a script stored elsewhere. Make the importer accept a folder or manifest so all days import in one run, each with its own Last-Modified availability. With history, the 12 September view gets a real price chart from the official bulletins up to 11 September, and the live view can use the official bulletins too (keep ForInvest v1 records; prefer the official source where both exist and say which source each value comes from).
6. Do NOT import into the real database; give the integrator the exact command (run in the API/worker container with the bulletin folder mounted read-only, or from the host if the stock import tooling does that today; check how stock_import is run). Report the date range actually downloaded, file count, total size and any gaps.
Files you own: services/p50k/product/stock*.py (stocks.py, stock_routes.py, stock_import.py read-only unless needed), new services/p50k/product/stock_bulletin.py, web/app/stocks/**, web/components/Stock*.tsx and any stock-only components, tests/unit/test_product_stock*.py, docs/decisions/DEC-036-official-bist-daily-bulletin.md. Prefer no migration; if one is unavoidable use db/migrations/015_*.sql (014 is taken).`,
  },
  {
    key: 'results',
    title: 'After-the-fact results page',
    prompt: `Workstream: success metrics a non-technical, non-bank audience understands (new page /sonuclar).
Mirza: "from those problematic funds and regular funds, we need success metrics that can be easily understood by non-tech or non-bank people... considering we work in the past and know the data (but the system should NOT), how successful were we at detecting the anomalies at those funds, how many false positives or negatives, how many went missing".
Ground truth: SPK's liquidation decision of 17 September 2026 (Kurul Karar Organı 57/1707 and 57/1708; bulletin 2026/61). In the database these are obs.regulatory_events rows with event_type='SPK_LIQUIDATION_ORDER' and status='CONFIRMED' (131 rows; a CANDIDATE copy also exists, use CONFIRMED only, one per fund). research/events/2026-09-17-spk-liquidations/liquidated_funds.json documents the list. System output: the stored detector run for 12 September (analysis scope asof:2026-09-12; find it the way the agents code does, services/p50k/product/agents/store.py scope_run / det.run_inputs.as_of='2026-09-12' with the current detector version) in det.signals (fund_code, detector_id, state TRIGGERED / NOT_TRIGGERED / abstained...) over ref.funds. Earlier context: 2,133 funds scanned, 189 funds with any TRIGGERED signal, 69 with a price-behaviour trigger, THF/TP2/PRY/PNU D1 triggered. Also available: the agent team's cases and proposals (agents.cases, ai.decisions method='TEAM') for the same scope.
Build:
1. services/p50k/product/evaluation.py: a read-only, deterministic computation that never feeds back into detectors, agents or the 12 September analysis: universe = funds in the 12 September run; event funds = universe ∩ confirmed liquidation orders; flagged = funds with any TRIGGERED signal, excluding the regulatory-record detector (AN-FND-005) so the official list cannot count as its own detection; report caught (event and flagged), missed (event, not flagged), flagged outside the list (flagged, not event), quiet (neither); detection rate (caught / event funds), share of flags that were on the list, the flag rate among event funds vs among other funds (how many times more likely), split by detector family if cheap (price behaviour vs data quality). Also the first flag date if dated runs exist (optional; skip if not readily available). Exclude abstentions carefully: funds without enough data are not "quiet", report them as "not assessable".
2. Route GET /evaluation/retrospective (new services/p50k/product/evaluation_routes.py, registered in app.py like other routers; authenticated like other product reads) returning the numbers, the lists (fund code, name, which detectors fired, link target) and provenance (run id, run cutoff, ground-truth source, publication date).
3. Web page web/app/sonuclar/page.tsx (+ CSS module): plain Turkish for a non-technical audience. Headline numbers as big, readable tiles with one-sentence meanings, e.g. "SPK'nın 17 Eylül'de tasfiye kararı verdiği N fondan K tanesi, 12 Eylül taramasında incelemeye alınmıştı" (caught), "Kaçırılan" (missed), "Listede olmayan işaretli fon" (flagged outside the list) with the explanation that being flagged outside the list does not mean the flag was wrong, and the "kaç kat daha sık" comparison. A simple visual (e.g. a 2x2 grid or proportional bars) instead of jargon like precision/recall (you may show those terms small for bankers). Expandable lists of caught and missed funds linking to /funds/CODE.
4. Integrity framing (binding, must be visible but calm): this is an after-the-fact check that uses information published after 12 September; the system's detectors and agents never see the SPK list; the results are development results, not validated performance or a prediction, because some rules were written after studying this event (see docs/notes/codex-context-2026-10-07.md and the method page); a liquidation order or a flag is not a finding of wrongdoing. Show the provenance (run date, cutoff, source).
5. Tests: synthetic DB test (smoke container, your module only) seeding a tiny run, signals and confirmed/candidate events to verify every count, the AN-FND-005 exclusion and abstention handling; unit tests for pure helpers.
Before writing UI copy, compute the real numbers with read-only SQL so the page design fits reality (do not write real numbers into git). The real API will not have your endpoint until the integrator deploys; for visual checks render the page with the dev server if possible, otherwise give the integrator a screenshot plan.
Files you own: services/p50k/product/evaluation.py, evaluation_routes.py, a one-line router registration in services/p50k/product/app.py, web/app/sonuclar/**, tests/unit/test_product_evaluation*.py, docs/notes/retrospective-evaluation.md (short method note, no real numbers).`,
  },
  {
    key: 'fundalert',
    title: 'Fund page warning summary',
    prompt: `Workstream: what a user sees for one fund (warnings), for the demo.
Mirza needs to show the warnings a user sees for a fund (e.g. THF on /funds/THF in the 12 September view). Today the fund page has the price chart, "Raporlarda fonun görünümü", "Gelişmeler" items with small tags (e.g. "İnceleme gerektiren değişim"), "Fon bilgileri" and "İnceleme kararı" far below; the agent team's case lives in the dock panel. There is no clear, prominent summary.
Build a calm but clearly visible warning summary at the top of the fund page (under the title/price header, above the tabs):
- When the selected date's calculation has triggered findings for the fund: a card with a clear heading (e.g. "Bu fon incelemeye alındı" / "İnceleme sınırı aşıldı"), the list of triggered measurements in plain words (use the same Turkish labels as the developments list / DEFINITIONS in services/p50k/product/chat_language.py), the agent team's case status (Açık / İnceleniyor / Raporlandı) with the code-computed test highlights when available (for example the monthly-report change sentence the Doğrulayıcı stored, already server-rendered Turkish in agents.messages kind='test_result'), the current decision state (team proposal awaiting human review, or the human decision), and actions: "Vaka akışını aç" (open the dock on that case; there is an event AGENTS_OPEN in web/lib/agents.ts the dock listens to, and AgentTeamPanel has openCase), "İnsan kararına git" (#karar) and "Raportöre sor".
- When nothing is triggered: a quiet one-line state ("Seçili tarihteki hesaplamada inceleme sınırı aşılmadı") with the honest note that this is not an assurance; when there is no calculation for the date: say so.
- Wording rules: neutral, no "risk", no "tehlike", no fraud language, no advice; a warning is a reason to review, not a conclusion.
- Data: prefer existing endpoints. If you need a compact read endpoint, add GET /agents/funds/{code}/summary in services/p50k/product/agents/routes.py with a read-only service function in services/p50k/product/agents/service.py that reuses fund_signals/case/decision helpers there (scope from the request cookie like the other agent routes; number-free model concerns do not apply because nothing goes to a model), with a DB test in the smoke container (new test module of your own, e.g. tests/unit/test_product_fund_summary.py).
- Responsive (390px) and both themes; accessible (heading levels, role="status" only if it updates).
Check /funds/THF, /funds/TP2 and a fund with no triggers (e.g. pick one via read-only SQL) at 1440x900 and 390x844.
Files you own: web/app/funds/[code]/page.tsx (insert the summary; keep the rest), new web/components/FundAlert.tsx (+ CSS module), services/p50k/product/agents/routes.py and service.py (only the new read function and route), tests/unit/test_product_fund_summary.py. Another builder edits services/p50k/product/agents/config.py, runtime.py, sentinel.py and store.py right now; do not touch those. Another builder owns web/components/agents/**; only use exported events/helpers from web/lib/agents.ts without editing it (if you must add an export, keep it a tiny additive change and report it).`,
  },
  {
    key: 'demo',
    title: 'Demo mode with real work',
    prompt: `Workstream: demo mode for the agent team, with real work and no visible tag.
Mirza: "I need a demo mode (no apparent tag or anything) to be able to show the working of our product and the pipeline etc even if the agent team runs out of work".
Binding constraint: nothing fake. Do NOT replay stored activity as if it were happening now and do NOT fabricate agent messages; the integrity rules require non-live data to be labelled. So the demo mode keeps REAL work flowing, which needs no label because nothing is staged.
Today (services/p50k/product/agents/): the worker runs two agent threads; Nöbetçi scans about every 60s; background pace is about one case every 5 minutes (config case_gap_seconds); the daily budget bucket agents:YYYY-MM-DD caps spend at $3.00 (config); user requests jump the queue (priority 100); a request on an unreviewed reported case opens a new review round (service.request_investigation / open_user_case); failed model calls retry later (runtime.retry_later).
Build, all configured by environment variables read in AgentConfig.from_env (no UI tag):
Mirza on budget: "we don't need to do all the work, just some work that can be shown". So the demo mode must show some real work regularly within the existing $3/day cap, not burn through the queue.
1. P50K_AGENT_DEMO=1 (default off): background pace becomes a moderate gap (env P50K_AGENT_CASE_GAP_SECONDS overrides either mode; demo default about 120s) so the panel shows work every couple of minutes without exhausting the cap.
2. Budget: make the daily cap configurable (P50K_AGENT_DAILY_USD, keep $3.00 default; check whether a variable already exists in config.py and reuse it). Keep a small reserve so user requests still run when background work is near the cap (e.g. background work stops at cap minus a reserve such as $0.25; user-priority tasks may use the reserve). Do not change the actual cap value ($3.00 stays).
3. Never running out of work in demo mode: when the scope being worked has no queued AI task left, the sentinel/runtime opens a new real review round for the oldest reported case in that scope whose proposal no human has reviewed and whose last round finished more than N minutes ago (e.g. 30), at most one such round at a time, at background priority, reusing the existing reopen logic (store.close_case + service.open_user_case or a shared helper so the records are identical in shape; opened_by can stay 'user'? no: use a sentinel-opened case if the schema allows opened_by='sentinel' with a clear opening note such as "Nöbetçi, kuyrukta iş kalmadığı için raporlanmış bir vakayı yeniden incelemeye aldı." — honest text, not a demo tag). Only in demo mode.
4. Tests: unit tests for config parsing; DB tests (smoke container) for the pace, the reserve and the idle reopen. The agent DB suite is tests/unit/test_product_agents_database.py; you own it for this task. Before running it stop the smoke worker (\`docker stop p50k-smoke-worker-1\`) and start it again afterwards (\`docker start p50k-smoke-worker-1\`); this is the only container you may stop/start.
5. Append a short "Demo mode" addendum to docs/decisions/DEC-035-agent-team-and-reporter.md: real work only, what changes (pace, cap via env, idle re-review rounds), cost per hour estimate from the measured ~$0.045 per case.
Files you own: services/p50k/product/agents/config.py, runtime.py, sentinel.py, store.py, llm.py (budget reserve only if it lives there), tests/unit/test_product_agents.py, tests/unit/test_product_agents_database.py, docs/decisions/DEC-035-agent-team-and-reporter.md. Another builder adds a read-only function and route in agents/service.py and routes.py right now: if you need a helper in service.py, add it at the end of the file as a separate function and report it.`,
  },
]

const results = await pipeline(
  STREAMS,
  (s) => agent(`${COMMON}\n\n${s.prompt}`, { label: `build:${s.key}`, phase: 'Build', schema: REPORT }),
  (report, s) => report ? agent(`You are a fresh, skeptical reviewer for the BlackSwan workstream "${s.title}". The builder's report:\n${JSON.stringify(report, null, 1)}\n\nThe builder's brief was:\n${s.prompt}\n\n${COMMON}\n\nReview ONLY this workstream's changes in ${APP} (git diff for the files in the report; new files with Read). Hunt for: bugs and runtime errors (including server/client component mistakes, hydration, null data, Turkish characters), integrity-rule violations (placeholders, fake values, misleading or alarmist copy, advice or wrongdoing wording, hindsight in the 12 September view, real data in git), broken behavior of existing features, accessibility and keyboard problems, mobile 390px overflow, light-theme contrast, missing or weak tests, and conflicts with files owned by other workstreams. Take your own screenshots with snap.mjs (read-only) where UI changed. You do not edit files. Return concrete findings with severity and an exact fix. Finish within 8 minutes.`, { label: `review:${s.key}`, phase: 'Review', schema: REVIEW }).then(review => ({ report, review })) : null,
  (pair, s) => {
    if (!pair) return null
    const urgent = (pair.review?.findings || []).filter(f => f.severity === 'critical' || f.severity === 'high' || f.severity === 'medium')
    if (!urgent.length) return { ...pair, fix: null }
    return agent(`You are the fixer for the BlackSwan workstream "${s.title}". Apply these review findings (all critical and high; medium ones when cheap and safe), then re-run the relevant checks (typecheck, vitest, the workstream's Python tests) and re-take the affected screenshots.\n\nFindings:\n${JSON.stringify(urgent, null, 1)}\n\nOriginal builder report:\n${JSON.stringify(pair.report, null, 1)}\n\nBrief:\n${s.prompt}\n\n${COMMON}\n\nHard stop 11:35 Istanbul time. Report what you fixed, what you skipped and why, and the final check results.`, { label: `fix:${s.key}`, phase: 'Fix', schema: REPORT }).then(fix => ({ ...pair, fix }))
  },
)
return results.map((item, index) => ({ workstream: STREAMS[index].key, ...(item || { failed: true }) }))

```
