# Sunday product release — 2026-10-11

## Final user additions, deployed before 12:30

DEC-037 records the additional authorization. Migration015 adds persistent, audited admin team pause/resume.
No new scans, claims or agent calls start while paused; admitted work finishes. Queues/messages/decisions remain
intact and the worker heartbeat keeps advancing. Real production stays running; only smoke was paused in tests.

`/results` is canonical, with query-preserving permanent `/sonuclar` redirect. Review is in the analyst/admin navbar,
shows manager logos and explicit provenance, and prioritizes live TEAM proposals before the 100-record limit.
Fund-side source cards align at the top, use their full content width and show already eligible monthly data.

New metrics show baseline assessed coverage and the eight case funds. The separately labelled monthly experiment
uses the fixed, pre-analysis `100ddfb` protocol: both reported size and units must double or halve in the same
direction over consecutive eligible months. Its real result:101 assessed / 2,133,3 flags,2 later-listed; KHA adds one to the
price baseline, giving a separate 24/131 and 5/8 union. Original 23/131, 4/8 and all detector thresholds/results remain
unchanged. This is development evidence with narrow coverage, not validated performance; it does not enter agent input.

Additional exact checks:

- `test_product_agent_control_database test_product_agent_control test_product_agent_connection_budget test_product_agents`
  on smoke: 25 tests passed, no skips, 1.223 s (includes3DBcontroltests).
- `test_product_kap_experiment test_product_kap_experiment_database` on smoke: 8 passed, no skips, 1.337 s.
- Review limit/current-packet regression: 2 passed, no skips, 1.078 s; targeted results/review Vitest: 15 passed.
- Current full web units: 12 files / 73 passed; Docker API/web build passed.
- Opt-in `P50K_CONTROL_SMOKE=1` browser control test: 1 passed, 8.4 s; actual PAUSE/RESUME, normal CSRF/auth,
  heartbeat advanced while paused, API healthy, composer visible and chat>=320px. Finally resumed `p50k_dev`.
- Final 52-view production audit:zero HTTP/overflow/raw-ID/JavaScript issues. Compiled THF/AAL: 6 views and 334.5 px chat,
  plus 10 focused results/review API/redirect/theme/width checks, passed. No real reviews or paid test chats.

Final screenshots and verdict JSON are retained outside Git at
`C:/Users/mirza/AppData/Local/Temp/p50k-release-20261011-final/`. Earlier ignored QA images were cleaned by a test
runner; the final audit regenerated them outside that cleanup path. Original market data/history/assets remain intact.

The final merge guard allows only the **newly added** experimental protocol, byte-equal to its preregistration commit;
every previously committed protected file remains blocked. No existing protocol is edited and no calibration changed.

### Fund inventory measured at 12:17

The catalog/analysis cohort is 2,133 funds. Stored daily observations total 1,755,010 across 2,131 funds (7 October
2021–9 October 2026); rows include source missing values and the September view admits only eligible history.
KAP metadata: 12,111 records across 945 funds; 1,259 locally indexed PDF records; 1,255 parsed period records across 101 funds.
The later SPK liquidation-order cohort is 131 funds, a subset; 8 are the primary case funds. September-eligible parsed
monthly coverage is 101 funds. No eligible historical TEFAS snapshot supplies September investor counts.

Product PostgreSQL size: 1,159,624,383 bytes (~1.16 GB). Raw files: 989,128,315 bytes; overnight folders: 157,053,752 bytes.
Folder sizes overlap/caches and include stocks; they are not a unique-fund-data total. No real fund values were
copied into this aggregate inventory or Git. All original files and database rows remain preserved.

This supersedes the unfinished status in the 10:40 Claude handoff, while preserving that handoff and its detailed
sprint briefs. The first release commit is `569c2db`; the final method spacing correction and this record follow it.
Mirza's completion deadline remains **12:30 Istanbul**, before the **13:00 code freeze**.

Requirement references for these delivered slices: **UR-075/076/077** (disclosure, visual design, responsive use),
**FR-018/019/020/109** (timestamps, source freshness, idempotent ingestion, time-bounded replay), and
**DEC-028/030/031/033/034/035/036** (full stack, product/egress agreements, product experience, dated work, agents,
official stock admission). These references do not claim completion of the entire frozen multi-market catalog.

## Delivered product slices

1. **Connection accounting.** Proven unsent DNS/connect errors settle zero. Timeouts and uncertain read/write/protocol
   failures retain the maximum reservation. Cause and context chains are checked conservatively. Connection failures
   get one call per attempt, then five/ten minute backoff, with the existing three-attempt ceiling. Old uncertain
   reservations were not rewritten. Today's compensated cap remains USD 5.25.
2. **Account/header.** Migration `014_user_avatar.sql` is applied to both databases. The owner CLI set
   `mirza@blackswan.local` to `/avatars/mirza.jpg`; the photo is ignored by Git but included in the web image. Tab/apple
   icons, the Sonuçlar link, a plain 12 September date chip and complete mobile navigation are shipped.
3. **Fund summary.** Fund pages show the selected calculation's measurements, the actual agent case, stored notable
   tests and the human decision/proposal state. Missing, uncovered and untriggered results remain distinct. The case
   link opens the correct case; the summary is read-only and model-free.
4. **After-the-fact results.** `/sonuclar` compares the stored 12 September run with 131 confirmed later SPK orders.
   It explicitly states that the list never enters that scan or the agents, results are development results, D1 was
   informed by studying THF/TP2, and flags do not establish wrongdoing. Price results: 23 listed funds flagged,
   108 not flagged (106 assessed and two unassessable), 46 flagged outside the list; 156 funds unassessable overall.
   A missing official list produces an unavailable state rather than invented zero-event results.
5. **Agent workspace and supplied art.** Six static SVGs from Mirza's `blackswan-maskotlar-svg.zip` are inspected and
   used in the dock, team and method. The dock is 96 px on desktop/84 px on mobile; it can be dragged, remembers its
   position per viewer, clamps on resize, and supports arrows/Home. The panel follows the anchor inside the viewport.
   The improved expanded parallel workflow is the default, with a saved collapse control. At 1480×712 the real
   expanded panel has a 334.5 px conversation and a fully visible input. Workspace padding/lists and plain provenance
   labels replace technical validation notes; actual failed/skipped work stays visible.
6. **Review.** `/review` has counts, pending/reviewed filters, named fund cards, readable rationale, evidence links and
   accept/change/reject actions. Change/reject require reasons. Original proposals stay immutable. No human review was
   submitted to the real database during verification.
7. **Official stock history.** DEC-036 bulk import validated all 50 official archives before admission, then imported
   1,500 daily closes for 3 August–9 October. There are no missing closes or capture-time fallbacks in this batch.
   The 12 September cutoff admits 30 bulletins/900 closes, with 11 September's dated membership. Historical lists
   fail closed rather than falling back to current membership. ForInvest v1 remains captured on 10 October; it is
   never backdated. Official prices are unadjusted and carry their source/availability explanation.
8. **Method and login.** `/method` shows the actual five-role parallel flow, source/date trail, code measurements,
   explanation and preserved human decision. All source-time/development/no-advice limits remain. Its first-section
   CSS reset no longer clips the workflow heading. `/login` uses the supplied BlackSwan mark, larger wordmark,
   themed form, readable fields and mobile layout without changing CSRF/auth behavior.
9. **Real-work demo mode.** `P50K_AGENT_DEMO=1` defaults to one background case about every 120 seconds; an explicit
   gap overrides it. The existing daily cap variable remains authoritative; background calls leave USD 0.25 for
   user-priority work through an atomic reservation gate. An idle scope can open one genuinely new review round for
   an unreviewed report older than 30 minutes on the exact same run. Nothing is replayed or copied as fresh output.
   Packet-scoped review locks protect human decisions across newer AI proposals on unchanged evidence. A user
   promotion wakes a background budget wait, including promotion during a claimed task.

## Actual checks

These are focused product checks, not a new broad Linux regression. Database checks ran only on `p50k_dev`.

| Command/module group | Actual result |
|---|---|
| `python -m unittest tests.unit.test_product_agent_demo tests.unit.test_product_agent_connection_budget tests.unit.test_product_agents tests.unit.test_product_agents_database -v` in the smoke worker, mounted current services/tests | 36 passed, no skips, 20.951 s |
| Final locked completion promotion regression, same worker | 1 passed, no skips, 0.174 s |
| `test_product_auth` with app-role credentials and mounted pepper in smoke | 15 passed, including five DB tests |
| `test_product_stock_bulletin test_product_stocks` in owner smoke container | 28 passed, including nine DB tests |
| `test_product_decisions test_product_evaluation test_product_evaluation_database` in smoke | 14 passed, including six DB tests |
| `test_product_fund_summary` in smoke | 6 passed, including three DB tests |
| `npm test` in `web/` | 11 files, 64 tests passed |
| `npm run typecheck` in `web/` | Passed |
| `docker compose -f compose.yaml build api web`, then web-only builds for final UI corrections | Passed; no host production build |
| `npx playwright test tests/browser/agents.spec.ts --grep 'expanded team\|mascot drags\|bottom sheet' --output C:/Users/mirza/AppData/Local/Temp/p50k-synthetic-browser-final` | 3 passed, 5.8 s; synthetic chat/agent responses only |
| Real 13-page audit, 1440/390 px × dark/light | 52 views returned 200, all selected dates 12 September; zero final overflow, raw-ID matches or JS errors |
| Focused method header measurement, 1440/390 px | 28/20 px top padding; title/kicker inside card; no overflow |

The initial page audit found a THF hydration failure in the monthly report chart: the SVG title had multiple React
children. It now uses one string. The diagnostic page and repeated production audit are clean. Initial synthetic
agent browser checks failed on outdated live-scope fixtures and animation-time geometry; the fixture now matches
the September view and geometry assertions wait for the transition. The final three checks passed.

Screenshots and browser logs are ignored, under `web/test-results/sunday-final/` and
`web/test-results/sunday20261011/`; earlier results/review screenshots remain in `web/test-results/results-review/`.
No screenshots, real price rows, private photos or downloaded archives are committed.

## Runtime and exact continuation

- **Real:** web `http://127.0.0.1:3070`, API 8770, DB `p50k`, live AI, default `2026-09-12`, demo enabled.
- **Smoke:** web 3071, API 8771, DB `p50k_dev`, AI off, test endpoints on, default `2026-09-12`.
  Tests that need a live analysis context set it explicitly in their one-off process; they do not change this default.
- **Fallback:** 3060/8767/8768 untouched. No sealed module/protocol/detector/raw path changed. No volume deletion.
- **Git:** edits remain in `project-50k-app` / `product/build`; integration uses the existing temporary worktree on
  `product/phase1-merge`. Merge with `--no-ff --no-commit`, protected-path check, leak scan, commit, push
  `product/phase1-merge:main`, then protected-path-checked `git pull --ff-only` in the main checkout. No branch switch,
  squash or force push. See the latest status in `current-state.md` for landed heads.

Real rollout from PowerShell in the app worktree (never print Docker's expanded secret configuration):

```powershell
$env:P50K_DB_NAME='p50k'
$env:P50K_ANALYSIS_DATE='2026-09-12'
$env:P50K_API_PORT='8770'
$env:P50K_WEB_PORT='3070'
$env:P50K_AI_MODE='live'
$env:P50K_TEST_ENDPOINTS='false'
$env:P50K_AGENT_DAILY_CAP_USD='3.00'
$env:P50K_AGENT_DEMO='1'
docker compose -f compose.yaml -f compose.override.yaml -f compose.dev.yaml -f compose.ai.yaml up -d --no-build --wait
```

Today's existing bucket retains its authorized 5.25 cap (created using the handoff's 5.25 environment). The final
runtime now uses `P50K_AGENT_DAILY_CAP_USD=3.00`, so tomorrow's new bucket returns to 3.00 without a manual action;
bucket creation never rewrites an existing cap. Today's 5.25 compensates previously booked uncertain failures.
Environment values are explicit for each rollout; never accidentally point real AI
at the smoke DB. The supplied OpenAI key remains in `secrets/openai_api_key`; never ask for it, read it in tools or print
it. Budget reserves/task priorities and the real operating clock are separate from the selected evidence date.

Official archive folder: `C:/Users/mirza/.local/share/project-50k/overnight/2026-10-11/bist/thb/`. Batch validation used
Python `-I`; archives were parsed as untrusted data and never executed. Import run `26ea0169-630f-4a43-8ec7-fef4cd3aee1c`
completed on the real DB. The original files, ForInvest rows, fund history and previous AI decisions remain preserved.

## Limits and remaining work

- Stock prices/history and dated membership work; stock anomaly classifiers/stock AI do not exist. Do not claim them.
- The results page is an after-the-fact development comparison, not held-out validation, proven accuracy or an early
  warning performance estimate. The SPK list never becomes an agent input.
- Data remains local. Commercial redistribution rights, pricing, demand and partnerships are unvalidated. Insurance
  stays permanently deferred; all earlier source/integrity constraints remain binding.
- Background work stops near its budget limit; users can use the protected reserve within the real cap. An idle
  mode cannot manufacture activity or override a human review. No new paid foreground AI request was made solely
  for these UI checks; the live worker continues normal authorized work.
- Full browser regression and every interactive action on every asset were not rerun. Real reviews were deliberately
  not tested by submitting them; synthetic DB and mock-POST tests cover the new review contract.
- The next recommended task is recording the polished THF flow and the results/stock screens, then scoped stock
  detector design after the freeze. Do not add new detectors or recalibrate the frozen fund ones during this release.

## Changed-file manifest

Current paths shipped since the last deployed `fd03482` (including preserved handoff records):

```text
.gitignore
AGENTS.md
CLAUDE.md
compose.yaml
db/migrations/014_user_avatar.sql
db/migrations/015_agent_control.sql
docs/decisions/DEC-036-official-bist-daily-bulletin.md
docs/decisions/DEC-037-team-control-and-monthly-development-experiment.md
docs/notes/current-state.md
docs/notes/product-direction.md
docs/notes/retrospective-evaluation.md
docs/notes/sunday-product-release-2026-10-11.md
docs/notes/team-asks.md
plans/2026-10-11-codex-handoff-prompt.md
plans/2026-10-11-sprint-briefs.md
research/events/2026-09-17-spk-liquidations/kap_monthly_scale_v1/PROTOCOL.md
services/p50k/product/agents/config.py
services/p50k/product/agents/control.py
services/p50k/product/agents/llm.py
services/p50k/product/agents/roles.py
services/p50k/product/agents/routes.py
services/p50k/product/agents/runtime.py
services/p50k/product/agents/sentinel.py
services/p50k/product/agents/service.py
services/p50k/product/agents/store.py
services/p50k/product/ai_client.py
services/p50k/product/app.py
services/p50k/product/auth.py
services/p50k/product/auth_cli.py
services/p50k/product/decisions.py
services/p50k/product/evaluation.py
services/p50k/product/evaluation_routes.py
services/p50k/product/kap_experiment.py
services/p50k/product/stock_bulletin.py
services/p50k/product/stock_routes.py
services/p50k/product/stocks.py
tests/unit/test_product_agent_connection_budget.py
tests/unit/test_product_agent_control.py
tests/unit/test_product_agent_control_database.py
tests/unit/test_product_agent_demo.py
tests/unit/test_product_agents.py
tests/unit/test_product_auth.py
tests/unit/test_product_decisions.py
tests/unit/test_product_evaluation.py
tests/unit/test_product_evaluation_database.py
tests/unit/test_product_fund_summary.py
tests/unit/test_product_kap_experiment.py
tests/unit/test_product_kap_experiment_database.py
tests/unit/test_product_stock_bulletin.py
tests/unit/test_product_stocks.py
web/app/apple-icon.png
web/app/design.css
web/app/funds/[code]/page.tsx
web/app/icon.svg
web/app/login/login.module.css
web/app/login/page.tsx
web/app/method/method.module.css
web/app/method/page.tsx
web/app/results/ResultsReport.tsx
web/app/results/layout.tsx
web/app/results/page.tsx
web/app/results/results-logic.ts
web/app/results/results.module.css
web/app/review/page.tsx
web/app/sonuclar/layout.tsx
web/app/sonuclar/page.tsx
web/app/stocks/[symbol]/page.tsx
web/app/stocks/page.tsx
web/components/DateContextControl.tsx
web/components/DecisionPanel.tsx
web/components/DesignShell.tsx
web/components/FundAlert.module.css
web/components/FundAlert.tsx
web/components/FundReportSeries.tsx
web/components/Funds.module.css
web/components/KapExperiment.module.css
web/components/KapExperiment.tsx
web/components/StockChart.tsx
web/components/agents/AgentDock.tsx
web/components/agents/AgentTeamPanel.tsx
web/components/agents/AgentWorkspace.tsx
web/components/agents/Mascot.tsx
web/components/agents/ReporterTab.tsx
web/components/agents/RoleGlyph.tsx
web/components/agents/TeamPage.tsx
web/components/agents/TeamStage.tsx
web/components/agents/agents.css
web/components/agents/dock-position.ts
web/components/agents/useDockPosition.ts
web/components/review/ReviewActions.tsx
web/components/review/ReviewCard.tsx
web/components/review/ReviewQueue.tsx
web/components/review/review-logic.ts
web/components/review/review.module.css
web/lib/agents.ts
web/lib/auth.ts
web/lib/avatar.ts
web/lib/stock-chart.ts
web/public/agent-logos/blackswan-dogrulayici.svg
web/public/agent-logos/blackswan-hipotezci.svg
web/public/agent-logos/blackswan-nobetci.svg
web/public/agent-logos/blackswan-raportor.svg
web/public/agent-logos/blackswan-supheci.svg
web/public/agent-logos/blackswan.svg
web/tests/agent-control.test.ts
web/tests/agents.test.ts
web/tests/avatar.test.ts
web/tests/browser/agent-control.spec.ts
web/tests/browser/agent-fixtures.ts
web/tests/browser/agents.spec.ts
web/tests/browser/session.spec.ts
web/tests/dock-position.test.ts
web/tests/results.test.ts
web/tests/review.test.ts
web/tests/stock-chart.test.ts
```
