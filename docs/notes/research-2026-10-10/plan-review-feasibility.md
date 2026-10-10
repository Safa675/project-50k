1. **§9 timeline and cut list: the effort numbers leave out much of the plan's own scope.**
   - **Problem:** The 19.5 h figure comes from the runtime review's narrower design. It leaves out the work this plan adds:
     - the D8 note and run (T2.1);
     - both spikes (T2.3, 1.5 h by §4's own figure);
     - AN-FND-002/004 plus K1's per-date flow note;
     - the AN-DQ guards and the 2026/61 event import;
     - the code for the overnight runners (see 3);
     - T5.2 (overnight import, SPK extraction and confirmation);
     - the T5.3 story screens and term sheet;
     - the T5.4 design and accessibility pass, and T6.4.

     By my estimate that is about 10–12 h more, so roughly 30 h against 14–16 h. The six cut items save only about 3–4 h. Neither spike's result is used before the freeze: no task imports SPK web-service data, and no job collects KAP events.
   - **Failure:** At Sun 10:00 chat or the story screens are half-built. The 10:00–13:00 window still has to hold tests, seed, docs, backup, merge and rehearsal.
   - **Fix:** Replace "Cut order if late" with: "Moved after the freeze now: T2.3, AN-FND-002/004 and K1, T5.2's SPK text extraction, T4.2 for 2005–2023, T4.3, B2B keys (OpenAPI page instead), partner panel, all-fund summaries, the CI compose job, the scheduler. Chat ships with search_funds, get_fund_profile, get_signals and get_decision. Feature freeze Sun 10:30; after that only fixes, backup and rehearsal. If M2 slips by more than 1 h, drop D8: uncovered categories ABSTAIN with 'no calibrated threshold for the category' (DEC-029 allows the frozen thresholds)."

2. **§9 M1 and Phase 1 order: 7.5 h of estimated work in 3.25 h, with the data import behind work that doesn't block anything yet.**
   - **Problem:**
     - M1 (13:45–17:00) holds compose 1.5 h, migrations 1.0, importers 2.0, queue with concurrency tests 1.5 and auth 1.5 (runtime review §10).
     - Login and the leased queue come before the importers, but only the importers block Phase 2.
     - T1.1's Dockerfiles run `uv sync --locked` before T1.3 updates the lock.
     - Anonymous Docker Hub pulls are rate-limited per IP, and the venue's IP is shared.
   - **Failure:** M1 lands around 21:00, the detectors around 23:30, and decisions and screens after 05:00. The overnight runners never get built.
   - **Fix:** "Phase 1 by Sat 17:30, in this order:
     - pre-pull the four pinned base images;
     - T1.1, then T1.3, then T1.4;
     - T1.2 (db, migrate, api, web skeleton, plus the proxy checks in 6);
     - T1.5;
     - T1.7, run once as a CLI: `docker compose run --rm worker python -m p50k.product.cli import-archive`.

     M1 is done when the archive row counts match. T1.6 moves to Phase 3, before T3.3. T1.8 moves to Phase 3 and carries only ai_decide jobs. The detectors run as a CLI in Phase 2."

3. **§4 Overnight, D9, T4.1–T4.3, T5.2: the overnight jobs have no build task, no place to run and no safe output path.**
   - **Problem:**
     - `C:\Users\mirza\Desktop\Hackathon\project-50k\services\p50k\providers\tefas.py` has no profile call (only snapshot, price_history and fund_list).
     - No SPK bulletin scraper exists.
     - `C:\Users\mirza\Desktop\Hackathon\project-50k\research\spikes\2026-10-06-tefas\kap_batch.py` hard-codes `KAP_DIR = raw/kap/reports`, has no output-directory option, and imports httpx, which is neither locked nor installed.
     - `C:\Users\mirza\Desktop\Hackathon\project-50k\services\p50k\jobs\fund_snapshots.py` defaults to `~/.local/share/project-50k/fund_snapshots.sqlite3` when `--db` is left out.
     - The 12-month price refresh overlaps the archive, and a COPY into a table keyed on (fund, date) aborts on the first duplicate.
   - **Failure:** Run from the main checkout, kap_batch writes into the load-bearing `raw/kap/reports/`, against D9's "new directories". Or nothing is built by 01:00. Or the Sunday 07:00 import fails on duplicates.
   - **Fix:** Add "T2.5 (C, by Sat 20:30): overnight runners, started on the host from the worktree's uv environment. All output goes under `C:\Users\mirza\.local\share\project-50k\overnight\2026-10-10\`, never under a checkout's raw/.
     - Prices: `p50k.jobs.price_history --periyod 12 --out <dir>\prices`.
     - All-fund snapshots: `p50k.jobs.fund_snapshots --db <dir>\snapshots.sqlite3` (always pass `--db`).
     - Profiles: a new fonProfilBilgiGetir call in `services/p50k/product/`.
     - SPK 2024–2026: index scrape and PDF download only.

     Each runner skips codes already written, so it can be restarted at 07:00, and each is dry-run on THF and TP2 first. T4.3 and SPK 2005–2023 move after the freeze. The T1.7 and T5.2 importers COPY into staging tables, then `INSERT … ON CONFLICT DO NOTHING`."

4. **§6 decisions and budget against M3 and T5.2: the paid decision pass runs before the final detector run.**
   - **Problem:**
     - Saturday's decisions are made on archive data. T5.2 reruns the detectors on refreshed prices, so every packet hash changes and the cache misses.
     - The $19.5 estimate assumes one pass of about 300 decisions (about $5.5). A second pass plus chat and testing goes past the $20 cap.
     - Saturday's overrides stay attached to superseded decisions.
     - No concurrency is set, so 300 medium-effort calls take hours.
   - **Failure:** At the pitch the budget guard blocks chat, and the queue shows unreviewed "Yapay zekâ önerisi" items instead of the override story.
   - **Fix:** "§6: AI stays in mock mode until T5.2 ends, plus at most 20 live decisions for prompt tuning (≤ $1). One live pass of at most 300 decisions starts after the final detector run, by Sun 08:30, with 6 concurrent ai_decide jobs. Demo overrides are made after that pass (T6.2). If D9 is declined, the pass runs right after M2."

5. **D8, §4 Funds and T2.1: half the funds have no category source on Saturday.**
   - **Problem:**
     - `C:\Users\mirza\Desktop\Hackathon\project-50k\research\events\2026-09-17-spk-liquidations\price_detectors\run.py` takes peers from the snapshot DB's `category` column.
     - Price files hold only the code and [date, price] rows (THF.json checked). So "forward snapshot rows plus the price-file list" gives categories only for the 1,071 TEFAS-traded funds, and about 950 or more priced funds have none until T4.1.
     - The only all-fund source on disk is the saved 2026-10-06 fonGetiriBazliBilgiGetir response in `C:\Users\mirza\Desktop\Hackathon\project-50k\raw\tefas\responses\`. Its 2,133 rows carry a different field, `fonTurAciklama`, and it is unverified whether that field matches the snapshot category.
     - The research rules require the note to be committed alone, with an "Already seen" list.
   - **Failure:** D8 switches taxonomy while claiming "the same preregistered rule". Or it reruns on Sunday with new thresholds, which invalidates Saturday's signals and decisions.
   - **Fix:** "T2.1: the note fixes one category source for every fund: the 2026-10-06 fund list's `fonTurAciklama`, stated as a change from the frozen run. It lists what was already seen (the frozen results and the 100-fund thresholds) and is committed alone before any all-fund percentile is computed. D8 runs once on Saturday; overnight data never recalibrates. §4 Funds: names, categories and tefasDurum come from that file."

6. **§6 streaming, D2 and T1.2: the proxy path (cookie, CSRF/Origin, SSE) is first exercised on Sunday.**
   - **Problem:**
     - The Next route handler must forward Cookie, Origin and X-CSRF-Token, return every Set-Cookie, and pass the stream through unbuffered.
     - Next's default compression can hold back a stream.
     - The `frontend/next.config.ts` loopback guard throws on `http://api:8000` if it is copied.
     - The standalone `server.js` binds to $HOSTNAME, which Docker sets to the container ID.
   - **Failure:** Login works with curl on 8770 but fails in the browser (missing Origin, or `localhost` vs `127.0.0.1`). Or chat answers arrive in one block, and this is found at Sun 09:00.
   - **Fix:** Add to T1.2: "Proxy check before M1, through 127.0.0.1:3070:
     - a dummy login sets `p50k_session`;
     - a CSRF POST passes the Origin check for both `http://127.0.0.1:3070` and `http://localhost:3070`;
     - `curl -N` receives a dummy SSE endpoint's 10 one-second events one at a time (`compress: false`, `Cache-Control: no-cache, no-transform`, no GZip on that API route);
     - `web/next.config.ts` uses an allowlist instead of the loopback guard;
     - `HOSTNAME=0.0.0.0`."

7. **§8 Web and T6.1: the Playwright synthetic seed goes into the real-data stack.**
   - **Problem:** The plan names no separate project, volume or ports for the smoke test. DEC-027 says the live demo shows no synthetic data.
   - **Failure:** At 12:00 Sunday synthetic funds and users enter the demo's volume and show in the fund list. Deleting them across the obs, det and ai foreign keys under time pressure puts real rows at risk. A second `up` also collides on 3070 and 8770.
   - **Fix:** "T6.1: run the smoke test as `docker compose -p p50k-smoke --profile test up`, with its own volume and host ports 3071 and 8771 (or none), then tear it down with `-v`. The demo project's volume never receives synthetic rows."

8. **§8 "clean start", T6.3 and D5: the database can be lost, and no backup exists yet.**
   - **Problem:**
     - The database will hold paid decisions, overrides and human confirmations that are expensive to rebuild.
     - `pg_dump` runs only after the 12:00 checks, and the restore is never rehearsed.
     - postgres:18 moved PGDATA to `/var/lib/postgresql/18/docker`. A volume at `/var/lib/postgresql/data` (as most examples have it) leaves the cluster in the image's anonymous volume.
   - **Failure:** A "clean start" run as `down -v`, or `down` then `up` with the wrong mount, empties the database at 12:15. The decisions cost another ~$5.5 and hours to redo, and the overrides are gone.
   - **Fix:**
     - "§8: clean start means `docker compose down` (never `-v`), then `up -d`."
     - "T1.2: the db volume mounts at `/var/lib/postgresql`."
     - "`pg_dump -Fc` moves to Sun 11:00, and a restore into `-p p50k-restore` is rehearsed before 12:00."
     - "T6.4 adds a cold-boot rehearsal: reboot, Docker Desktop, compose up, `start-demo.ps1 -Restart` from the dated-view clone, and a login to both demos."

9. **§3 Secrets, T1.1 and T1.3: the image recipe leaks secrets and misses the detector dependencies.**
   - **Problem:**
     - `.dockerignore` lists only raw/, .venv, node_modules and .next. The uv Docker guide's `ADD . /app` would copy `.env` (the OpenAI key), `secrets/` and later `backups/` (a real-data dump) into an image layer.
     - The project has `[tool.uv] package = false`, so the code needs PYTHONPATH.
     - `detectors.py` lives under `research/…/price_detectors/` and needs numpy from the `research` extra.
     - In the worktree the leak scan exits 2 and skips the value and name checks unless `P50K_RAW_DIR` is set.
   - **Failure:** The key and real data end up in image layers. The first detector job fails with "No module named numpy". Commits from the worktree skip the value and name checks without anyone noticing.
   - **Fix:** "T1.1:
     - `.dockerignore` also lists `.env`, `.env.*` (with `!.env.example`), `secrets/`, `backups/`, `.git` and `**/*.sqlite3`;
     - Dockerfiles COPY explicit paths only, including `price_detectors/detectors.py`;
     - set `ENV PYTHONPATH=/app/services`;
     - install `--extra api --extra research --extra product`;
     - run the leak scan with `P50K_RAW_DIR=C:\Users\mirza\Desktop\Hackathon\project-50k\raw`, and treat exit 2 as a failure."

10. **D1 and §3: the Windows bind mounts are underspecified.**
    - **Problem:**
      - SQLite locking over Docker Desktop's Windows share is unreliable.
      - Only the worker mounts raw/, but D2 copies the PDF viewer, which needs the API to serve KAP PDFs.
      - Host paths and `env_file: .env` in `compose.yaml` make CI's `compose config` fail, and break the file on any other machine.
    - **Failure:** The M1 import fails with "database is locked". The PDF button returns 404. CI is red on the first push.
    - **Fix:** "§3:
      - open both SQLite files as `file:…?mode=ro&immutable=1`, or copy them to a staging folder first;
      - put host binds in a gitignored `compose.override.yaml` (commit an example) and use `env_file: {path: .env, required: false}`;
      - D2 copies only the chart and formatters until 'KAP beyond metadata' is in scope."

11. **M5, T6.1 and T6.3: the first Linux run and the merge to main both fall in the freeze hour, and neither is defined.**
    - **Problem:**
      - The research suites have never run on Linux (`C:\Users\mirza\Desktop\Hackathon\project-50k\docs\notes\current-state.md`).
      - Inside a container, the worktree's `.git` is a file pointing at a Windows path, so the HEAD check in `C:\Users\mirza\Desktop\Hackathon\project-50k\tests\unit\test_registered_sources_lock.py` is skipped.
      - Git refuses to check out `main` in the worktree while the main checkout holds it. Merging in the main checkout rewrites a load-bearing working tree.
    - **Failure:** Unknown failures appear at 12:20. Someone merges in the main checkout an hour before the pitch.
    - **Fix:**
      - "M1: run the root and frozen suites in WSL2 from `git clone --branch product/build /mnt/c/Users/mirza/Desktop/Hackathon/project-50k ~/p50k-linux` and save the failing test names as the baseline. T6.1 passes when no name is new."
      - "T6.3: in the worktree, `git switch -c freeze-merge origin/main`, then `git merge --no-ff product/build`. Confirm that `git diff --name-only origin/main..freeze-merge` touches no registered path. After Mirza's OK, push `freeze-merge:main`, or merge a PR with a merge commit if branch protection requires it. Tag that commit. Do not pull into the main checkout until K4."

12. **Phase 0, §4 and §11: several human steps have no owner or time slot.**
    - **Problem:**
      - T0.2 puts the key into a worktree that T1.1 has not created yet.
      - The 131-fund mapping check and the Sunday SPK confirmations have no owner or time.
      - "Keep the machine on" leaves out sleep, Windows Update restarts and Docker Desktop autostart. A restart kills the overnight jobs and the 3060/8767/8768 demo processes.
      - D7's "Safa should agree" has no rule for live calls made before he answers.
      - The term sheet depends on Safa's asks 2–4, which have no deadline.
      - Barış's tokens have no cut-off.
    - **Failure:** Live calls go out with the D7 gate still open. At 07:00 the machine has rebooted and the jobs are dead. At 23:00 there is still no story pick.
    - **Fix:**
      - "T1.1 runs first, then T0.2."
      - "T1.7a (M, by 17:00): check the one closest-name mapping and 10 exact matches."
      - "T4.0 (M): AC power, sleep set to Never, Windows Update paused until Monday, Docker Desktop starts at login, a 07:00 log check."
      - "D7: AI stays in mock mode until Mirza answers."
      - "T0.5: Safa answers asks 2–4 with the story pick. With no pick by 23:00, build story B."
      - "T3.2 builds only the materiality decision type."
      - "T0.6: tokens as values by Sat 23:00, otherwise ship the current tokens."