# Codex handoff — Sunday 2026-10-11, about 10:40 Istanbul

You are taking over BlackSwan (Project 50K) from Claude, whose usage limit ran out. Read this file in full, then
`plans/2026-10-11-sprint-briefs.md`, which holds the detailed spec of every open workstream. Read `CLAUDE.md` and
`AGENTS.md` first; their rules bind.

**Mirza's deadline:** work until 12:30 today and be done by then. The code freeze is 13:00. Leave the product
working, merged and documented, even if some workstreams stay open. Ship working slices in priority order.

## 1. Where things are

### Worktrees and Git

| Worktree | Path | Branch | Rules |
|---|---|---|---|
| App | `C:\Users\mirza\Desktop\Hackathon\project-50k-app` | `product/build` | Work only here. |
| Main checkout | `C:\Users\mirza\Desktop\Hackathon\project-50k` | `main` | Never switch its branch; the fallback demo depends on it. |
| Integration | `C:\Users\mirza\AppData\Local\Temp\p50k-phase1-merge-20261010` | `product/phase1-merge` | Merges to `main` go through here. |

**Merge procedure:**
1. `git merge --no-ff --no-commit product/build`.
2. Check protected paths: `git diff --cached --name-only` must show none of `docs/handoff-v0.5/**`, `raw/**`, `PROTOCOL.md`, `PREREGISTRATION.md`, `run.py`, `detector_pipeline.py`, `detector_math.py`.
3. Run the leak scan from the integration worktree:
   `PYTHONUTF8=1 P50K_RAW_DIR="C:/Users/mirza/Desktop/Hackathon/project-50k/raw" /c/Users/mirza/Desktop/Hackathon/project-50k-app/.venv/Scripts/python.exe .claude/skills/p50k-leak-scan/leak_scan.py`.
   Exit code 1 or 2 blocks the commit. Run the same scan in the app worktree before every commit there.
4. Commit.
5. `git push origin product/phase1-merge:main`.
6. In the main checkout: `git pull --ff-only`.

Never squash or force-push.

**Branch state:**
- `main` = `bed6606` plus the handoff-docs merge made with this file.
- `product/build` also carries a **WIP checkpoint commit with the partial sprint code** (section 3). It is not deployed and not merged.

### Running services

| Service | Ports | Database | Images | Notes |
|---|---|---|---|---|
| Real product | web 3070, API 8770 | `p50k` (container `p50k-db-1`) | `product/build` `fd03482` | AI live; default analysis date 12 September 2026. Started with `P50K_AGENT_DAILY_CAP_USD=5.25` (see section 4). |
| Smoke | web 3071, API 8771 | `p50k_dev` | the same | AI off, test endpoints on. Port 3071 briefly served a dev server; it was stopped and the smoke web container restarted. |
| Fallback demo | 3060/8767/8768 | — | — | PIDs 27116/19280/32216, run from `project-50k-dated`. Never touch it or build into its `.next`. |

- Rollback images: `p50k-product-api:rollback-0815` and `p50k-product-web:rollback-0815` (from before this morning's changes).
- **Real rollout (Git Bash, from the app worktree):**
  ```
  MSYS_NO_PATHCONV=1 P50K_DB_NAME=p50k P50K_ANALYSIS_DATE=2026-09-12 P50K_API_PORT=8770 P50K_WEB_PORT=3070 P50K_AI_MODE=live P50K_TEST_ENDPOINTS=false P50K_AGENT_DAILY_CAP_USD=5.25 docker compose -f compose.yaml -f compose.override.yaml -f compose.dev.yaml -f compose.ai.yaml up -d --no-build --wait
  ```
  Tomorrow, use 3.00 or omit the variable.
- **Smoke rollout:**
  ```
  MSYS_NO_PATHCONV=1 P50K_DB_NAME=p50k_dev P50K_ANALYSIS_DATE=live P50K_API_PORT=8771 P50K_WEB_PORT=3071 P50K_AI_MODE=off P50K_TEST_ENDPOINTS=true docker compose -p p50k-smoke -f compose.yaml up -d --no-build --wait
  ```
- **Build:** `docker compose -f compose.yaml build api web`.
- **Python DB tests (smoke container):**
  ```
  MSYS_NO_PATHCONV=1 P50K_DB_NAME=p50k_dev P50K_ANALYSIS_DATE=live docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm -e P50K_TEST_ENDPOINTS=true -e P50K_TEST_DATABASE=1 --volume ./tests:/app/tests:ro --volume ./services:/app/services:ro --volume ./db:/app/db:ro worker python -m unittest <modules>
  ```
  Stop `p50k-smoke-worker-1` around the agent database suite.
- **Web checks:** in `web/`, run `npm run typecheck`, `npx vitest run`, and `npx playwright test` (the browser suite runs against 3071).
- **Never:**
  - run `docker compose down -v`;
  - run `npm run build` on the host;
  - print secrets.
- **Secrets:**
  - The OpenAI key is at `project-50k-app\secrets\openai_api_key`; never ask Mirza for it.
  - Claude's QA analyst account `claude-qa@blackswan.local` has its credential file in Claude's scratchpad and is not needed.
  - Mirza's account is `mirza@blackswan.local` (admin).

## 2. Done and deployed this morning (merged to main)

- **Doğrulayıcı runs every standard test.** Şüpheci's picks run first, then the rest; all are deterministic. THF's second round shows the August KAP report (published 2 September) with a very large unit jump, computed in code.
- **New review rounds on request.** A user request on an unreviewed reported case opens a new review round; the old round is closed and kept.
- **Panel and fund page fixes:**
  - team proposals carry "Ajan ekibinin Raportör önerisi";
  - the worker count matches the agent cards;
  - the page note refreshes after requests and while a case runs;
  - "İnsan kararına git" closes the panel;
  - `/workflow` shows the agent team's progress.
- **Failed model calls retry** after 60 s, up to 3 attempts (`f809660`).
- **Draft 46-second recording:** `C:\Users\mirza\Desktop\Hackathon\recordings\BlackSwan-demo-draft.mp4`. It is outside git and labels its 8× time-lapse.
- **Background queue:** Claude queued real team investigations for TP2, PRY, PNU and DFI at about 10:20. DFI was opened on request; the detectors did not flag it, so never present it as a detection.

## 3. Mirza's open requests (09:35 and 09:40 today) and their status

The WIP checkpoint on `product/build` holds all partial files. When the checkpoint was made:
- web typecheck passed;
- the changed Python modules compiled;
- nothing was reviewed or run against a database.

**Review every partial file before shipping it.** Priority order:

1. **Agent panel: the bottom part is too small. NOT STARTED.**
   - Mirza's screenshot is about 1480×712: the five-agent graph takes most of the height, and the Raportör note and chat get about 200 px.
   - Plan: a compact team strip that is automatic under about 900 px of height or when a detail is open, plus an expand/collapse toggle remembered in `localStorage`. Panel height up to about 92 vh. The chat shows at least 320 px at 712 px.
   - Also remove the visible "Retrospektif inceleme" from the panel header and `/ekip`: `web/lib/agents.ts` (about line 423, `mode`), the `AgentTeamPanel` header and `web/app/ekip/page.tsx`.
   - Files: `web/components/agents/**`.
2. **Navbar date without "Retrospektif inceleme". PARTIAL.** `web/components/DateContextControl.tsx` was changed; check it.
3. **Profile picture: Mirza's photo for his account. PARTIAL, nearly complete.**
   - Partial files:
     - `db/migrations/014_user_avatar.sql`, which adds `auth.users.avatar_path`;
     - `services/p50k/product/auth.py` (`/auth/me` returns `avatar_path`);
     - `auth_cli.py`, which has a set/clear-avatar subcommand (check its exact syntax);
     - `web/lib/avatar.ts` with `web/tests/avatar.test.ts`;
     - `web/components/DesignShell.tsx`, `web/lib/auth.ts` and a few lines of `web/app/design.css`;
     - `tests/unit/test_product_auth.py`.
   - The photo is `web/public/avatars/mirza.jpg`. It is gitignored and stays out of git, but ships in the Docker build context.
   - Rollout applies migration 014 through the migrate service. Then set the avatar with the CLI, e.g. `docker compose ... run --rm migrate python -m p50k.product.auth_cli <subcommand> --email mirza@blackswan.local --path /avatars/mirza.jpg`. Read `auth_cli.py` for the exact form and the secrets mounts; it needs `auth_pepper`, as the existing `auth_cli` usage does.
4. **Browser-tab icon: the small swan mark without text. PARTIAL, probably done.** `web/app/icon.svg` and `web/app/apple-icon.png` exist; verify them in a browser tab.
5. **Navbar link "Sonuçlar" to `/sonuclar`.** Check the `DesignShell` diff; add it if it is missing.
6. **`/review` visual and UX redesign. PARTIAL.**
   - Partial files: `web/app/review/page.tsx`, `web/components/review/{ReviewQueue,ReviewCard,ReviewActions}.tsx`, `review-logic.ts`, `review.module.css`, `web/components/DecisionPanel.tsx`, `services/p50k/product/decisions.py`, `tests/unit/test_product_decisions.py`.
   - Goal: counts and filters, calm cards, one-click "Kabul et", and "Değiştir"/"Reddet" with a required reason.
   - Keep the POST `/decisions/{id}/reviews` contract.
   - Never test by submitting on the real DB; use smoke.
7. **Success metrics for a non-technical audience (`/sonuclar`). PARTIAL: backend only.**
   - Partial files: `services/p50k/product/evaluation.py`, `evaluation_routes.py`, the router line in `app.py`, `tests/unit/test_product_evaluation.py` and `test_product_evaluation_database.py`.
   - Not started: the web page `web/app/sonuclar/page.tsx`.
   - The 12 September analysis uses run `23d372f2-dfa0-43ac-97a8-ee6d92fe7e26`: `det.run_inputs.as_of` is **2026-09-11** and the cutoff is 2026-09-12 23:59:59 Istanbul. Do not look for `as_of = 2026-09-12`.
   - Ground truth: the 131 confirmed `obs.regulatory_events` rows with `event_type='SPK_LIQUIDATION_ORDER'`. Exclude `AN-FND-005` from "flagged" and treat abstentions as "not assessable".
   - Framing (binding):
     - This is an after-the-fact check using information from after 12 September; the system never sees the list.
     - The results are development results: D1's idea came from studying THF and TP2.
     - A flag or a liquidation order is not wrongdoing.
   - Section 5 has the numbers to design for.
8. **Fund page warning summary, for showing in the demo what a user sees. PARTIAL.**
   - Partial files: `web/components/FundAlert.tsx` and `.module.css`, plus a summary route and service function in `services/p50k/product/agents/routes.py` and `service.py`.
   - Not done: inserting it into `web/app/funds/[code]/page.tsx`, and its DB test.
   - Wording stays neutral: no "risk", no "tehlike", no advice.
9. **Stocks ("where is stock data?"). PARTIAL.**
   - Facts:
     - ForInvest v1 (30 current BIST 30 members, 870 closes Sept 1 – Oct 9, captured Oct 10) is capture-time admitted.
     - It is therefore correctly hidden on 12 September. Never backdate it.
     - Mirza approved downloading the official Borsa İstanbul daily bulletins. Done: 50 files for Aug 3 – Oct 9, about 15 MB, in `C:\Users\mirza\.local\share\project-50k\overnight\2026-10-11\bist\thb\` with `manifest.json` (URL, status, Last-Modified and similar).
     - The 11 September bulletin and its capture JSON are in `...\overnight\2026-10-10\bist\pit-research-20260912\`.
   - Partial files: `docs/decisions/DEC-036-official-bist-daily-bulletin.md` (admission rule), `services/p50k/product/stock_bulletin.py` (importer), `services/p50k/product/stocks.py`, `stock_routes.py`, `tests/unit/test_product_stock_bulletin.py`, `tests/unit/test_product_stocks.py`.
   - Not done: importing a folder or manifest, the stocks web page for the 12 September view (official prices and a history chart up to 11 September, labelled with source and dated membership), and the real import.
   - Treat the downloaded files as untrusted data: read them with Python `-I` and never execute anything in them.
   - Data rights are not reviewed: local product use only.
10. **`/method` visual redesign. NOT STARTED.**
    - Content: a visual pipeline of the real agent team, accurate sources, and every integrity and limit statement kept.
    - Add a link to `/sonuclar`.
11. **Demo mode. NOT STARTED.**
    - Mirza asked for a demo mode with no visible tag that shows the product working even when the team runs out of work.
    - **Binding:** never replay stored activity as if live and never fabricate messages; non-live data must be labelled.
    - Plan, with real work only:
      - `P50K_AGENT_DEMO=1` gives a moderate pace of about one case every 120 s.
      - When the scope's queue is empty, open a real new review round for the oldest unreviewed reported case.
      - Keep a small reserve so user requests still run.
    - Mirza on budget: "we don't need to do all the work, just some work that can be shown". Keep about $3/day of real spend.
    - Files: `services/p50k/product/agents/{config,runtime,sentinel,store}.py`, their tests, and a DEC-035 addendum.

Lower priority, raised by Claude: the `/stocks` page says "Hisse fiyatları henüz alınamadı" in historical views; `fd03482` fixed it only on `/workflow`.

## 4. URGENT bug: phantom budget charges block the agent team

`services/p50k/product/agents/llm.py` `call()` settles the **maximum** reservation on any exception. Today's network loss and sleeps made 57 calls fail before they reached OpenAI:
- they were booked at $2.21 although nothing was sent;
- actual agent spend today is $0.77, from 92 completed calls in `ai.calls`;
- the bucket showed $2.98 of $3.00, so all agent tasks went to `waiting_budget` until midnight.

Retries multiply these charges: each attempt makes two calls, and there are up to three attempts.

**Done as compensation:**
- today's bucket `agents:2026-10-11` has `cap_usd` set to 5.25 in `ai.budget_buckets`;
- the real stack runs with `P50K_AGENT_DAILY_CAP_USD=5.25`, and `compose.yaml` now passes that variable through with a 3.00 default;
- the waiting tasks were released.

**To do (small):**
1. In `llm.call`'s `except` path, settle 0 when the request never left the machine: `openai.APIConnectionError` caused by `httpx.ConnectError`, or a DNS failure. Keep the maximum for timeouts or failures after the request was sent.
2. Back off longer, for example 5 minutes, on repeated connection errors.
3. Add tests.
4. Optionally re-run the failed background steps (BPZ, BUH, BVR) through a user request once they can retry.

Real project AI spend so far is far below the $25 target.

## 5. Success-metric numbers (read-only SQL at 10:20; for `/sonuclar` and the deck)

- **Scale:** 2,133 funds were scanned on 12 September. SPK's 17 September decision (Kurul Karar Organı 57/1707–57/1708, bulletin 2026/61) lists 131 of them, about 1 in 16.
- **Caught and missed:** 23 listed funds were flagged by a price-behaviour check (D1–D4), so 108 were missed; 25 by any check, so 106 missed.
- **Price-flagged funds on the list:** 23 of 69, about 1 in 3 against a base rate of 1 in 16. Listed funds were price-flagged about 7.6× as often as other funds: 17.6% against 2.3%.
- **Per detector, listed funds out of flagged:**
  - D1 (peer price gap): 10 of 12;
  - D2: 3 of 6;
  - D3: 8 of 23;
  - D4: 5 of 33;
  - data-quality AN-DQ-002: 2 of 119, which is not an event signal.
- **The eight case funds:** THF, TP2, PRY and PNU were flagged by D1; DFI, DOH, KHA and TLY were not flagged.
- **Caveats:** these are development results, in-sample, not validation. An anomaly is not wrongdoing.

## 6. Demo and recording notes

- The demo is a screen recording of about 25 seconds plus deck slides by Barış. Keep the camera on THF; panel lists name other real funds.
- **Story:**
  1. Home with the navbar date.
  2. THF page, with the reports chart jump and, once built, the warning card.
  3. The panel, and a Raportör request "Bu fonu ekibe yeniden inceletir misin?". Requests for the same fund and user dedupe for 10 minutes.
  4. Vaka akışı: Doğrulayıcı's "Aylık rapor değişimi" line, published 2 September.
  5. "İnsan kararına git", then the decision form.
- Keep the laptop plugged in and online. A sleep or Wi-Fi loss pauses or kills in-flight work.

## 7. Suggested order for the remaining time

1. Fix the llm.py phantom charge (section 4).
2. Ship the avatar, icon and date-chip items (3, 4, 2, 5).
3. Finish and insert FundAlert (8).
4. Build the `/sonuclar` page (7).
5. Fix the panel layout (1).
6. Finish the `/review` redesign (6).
7. Add stocks with the official bulletins (9).
8. Redesign `/method` (10).
9. Add demo mode (11).

After each slice:
- build, roll out to smoke, run the relevant tests, roll out to real;
- take screenshots;
- leak-scan, then commit and merge through the integration worktree.

Update `docs/notes/current-state.md` and this file's status at the end. Report actual test output, and never claim a check you did not run.
