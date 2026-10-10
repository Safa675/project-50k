1. **Critical. §6 Chat (Streaming, Answer check), D6 bulk summaries, §9 "Never cut"**
   - **Problem:** The wording and cited-ID checks (§6 Decisions, step 3) apply only to decisions.
     - Chat answers stream token by token through the Next handler. The only chat check (numbers against that turn's tool output) therefore runs after the text is already on screen, and the plan does not say what happens when it fails.
     - Chat has no wording check and no citation check. Evidence chips are not tied to IDs that really exist.
     - The `gpt-6-luna` summaries for about 2,000 funds go through no validation, review or override at all.
     - The validator is on neither the cut list nor the "Never cut" list. With 19.5 hours of work in 14–16, it can be dropped without anyone deciding to.
   - **Failure:** A viewer asks "X fonu manipülasyon mu yaptı, çıkmalı mıyım?". The streamed answer mentions "manipülasyon izleri" and suggests reducing the position. All of it is shown before any check, which breaks DEC-028's no-fraud and no-advice rules. Separately, a luna summary on a fund page states a percentage it invented. Nothing checks it and nobody can override it.
   - **Fix (new first paragraph of §6):** "**One validator for all model text.** Decisions, chat answers, summaries and SPK extraction all pass the same server-side validator before anything is shown: schema; every cited ID exists in that packet or in that thread's tool results; numbers only as `{{ev:<id>.<field>}}` placeholders, chat included; the wording rules. Chat streams tool-progress events live but sends the answer text only after validation. A failed answer is replaced by a fixed Turkish 'kanıt yetersiz' text and is never shown with a warning. Evidence chips render only for IDs that the thread's tools returned. Summaries live in `ai.summaries` with the same provenance columns, checks, review queue and hide/override path."
   - **Fix (add to "Never cut"):** "the AI output validator and the fail-closed path; if the validator is not ready by M4, chat and summaries run with `P50K_AI_MODE=off`."

2. **Critical. §4 Sunday morning, T4.2, T5.2 (SPK bulletin extraction)**
   - **Problem:** "keyword filter, then LLM extraction" sends bulletin text to OpenAI.
     - SPK bulletins' sanctions sections (suç duyuruları, idari para cezaları, işlem yasakları) name natural persons. D7 excludes personal data, and the KVKK transfer-abroad question (gate G07) has not been reviewed.
     - The LLM would emit the fund codes and dates that become AN-FND-005 events, which the plan calls "the best insurance trigger". That contradicts D11's "the LLM never outputs a number".
     - Nothing says that AN-FND-005, trigger assessments or the replay read only human-confirmed events.
   - **Failure:** A 2024 bulletin page with a named individual's trading ban goes to OpenAI along with the fund table. The model misreads a code and creates a halt event on the wrong real fund. That event shows on the fund page and counts as MET before anyone confirms it.
   - **Fix (replace the §4 bullet):** "Turn SPK bulletins into candidate events with rules first: match codes against `ref.funds` and take dates from the bulletin's own metadata. If the LLM is used, it receives only the fund-related section, with the sanctions sections removed and person names redacted, and it returns character spans only. The server keeps a candidate only if each code exists in `ref.funds` and appears verbatim in the span. Candidates are stored as `CANDIDATE` with `extracted_by: rule|llm`. AN-FND-005, trigger assessments and the replay read only `CONFIRMED` events, which record who confirmed them and when."

3. **High. §6 Decisions step 2 and D11: no deterministic limit on which decisions the LLM may return**
   - **Problem:** The model chooses freely among all D11 values. Nothing blocks any of these:
     - `NOT_MATERIAL` for a fund whose detectors all abstained (most funds if D8 slips);
     - `MATERIAL` citing only the D5 age attribute;
     - a decision with no citations;
     - `MET` without a confirmed, in-scope SPK event.
   - **Failure:** An analyst presses "Yeniden değerlendir" on a fund in a category with no thresholds. The model returns `NOT_MATERIAL`, and the page shows "Yapay zekâ önerisi: önemli değil", which reads as safe. This breaks the "unknown is not safe" rule and DEC-028's "insufficient evidence is stated as such".
   - **Fix (new step 1b):** "The server computes `allowed_decisions` from the packet and sends it as the enum for that call:
     - no covering detector and no event → `INSUFFICIENT_EVIDENCE`, with no model call;
     - `NOT_MATERIAL` needs at least one covering detector;
     - `MATERIAL` and `DATA_ISSUE` must cite at least one `TRIGGERED` signal or data-quality event;
     - every decision cites at least one ID.

     The trigger itself is the deterministic `trigger_fired`, computed from `CONFIRMED` in-scope SPK events. The LLM's `MET`/`NOT_MET`/`UNDETERMINED` is shown beside it. `MET` must cite a confirmed event, and any disagreement goes to the review queue."

4. **High. §3 AI records, §6 Caching, §3 AI modes: decision provenance is missing and the cache key is too narrow**
   - **Problem:**
     - DEC-028 requires each decision to store the model, the prompt version and a timestamp. The plan stores only the rationale, evidence IDs and `decided_by`.
     - The cache is keyed only by the evidence-packet hash.
     - Development runs `mock` against the same database that holds the real data and drives the demo.
     - The placeholder source is unstated. If placeholders are filled from live tables, Sunday's rerun changes the numbers inside Saturday's rationales.
   - **Failure:** Saturday's mock runs cache canned decisions on real funds under packet hash H. On Sunday, live mode hits the cache for H and stores the mock text as a `gpt-6.1-sol` decision. The demo then shows fabricated AI output on real fund names, which DEC-027 rules out.
   - **Fix (§3, add):** "`ai.decisions` stores `model_id`, `prompt_version`, `schema_version`, `ai_mode`, `packet_sha256`, `call_id` and `created_at`, all NOT NULL. Packets are stored immutably in `ai.packets`, and placeholders are filled only from the decision's own packet."
   - **Fix (§6 Caching, replace the first bullet):** "an exact-request cache keyed by `ai_mode`, model ID, reasoning effort, prompt version, schema version and packet hash. `INVALID` outputs are never cached. A cache hit writes a new row with `cache_hit=true` and the original `call_id`."
   - **Fix (AI modes, add):** "Mock runs use a separate `p50k_dev` database. The real-data database rejects `ai_mode='mock'` rows, and T6.2 checks that it holds none."

5. **High. §3 AI records, §6 step 5: append-only is not enforced, and the effective decision ignores changed evidence**
   - **Problem:**
     - There is one database password, so every service probably shares one superuser role. Nothing stops `UPDATE ai.decisions SET status=…`, which is the obvious quick way to build accept/reject. That writes the override over the original, against DEC-028's "never in place of it".
     - The `effective_decisions` view is not tied to the evidence the reviewer saw.
     - "Reject" has no defined effective value.
     - Evidence rows can be rewritten by a rerun.
   - **Failure:** On Saturday an analyst overrides fund X to `NOT_MATERIAL`. On Sunday, T5.2 adds the SPK order to X's packet. The new AI run says `MATERIAL`, but the page keeps showing the stale human value with no warning. After a "reject", the rejected AI value still displays as the effective one.
   - **Fix (replace the §3 AI-records bullets):** "The migration role owns the tables. The app role `p50k_app` is not a superuser and has only INSERT and SELECT on `ai.decisions`, `ai.decision_reviews`, `ai.packets`, `det.evidence_items` and `ops.audit_log`. A BEFORE UPDATE OR DELETE trigger on these tables raises an error. Decision rows have no mutable status. Each review stores `decision_id`, `packet_sha256`, the user, the action, the reason and the time. The effective value is the latest human review for the current packet. If the packet has changed since that review, the page shows 'önceki kanıta göre insan kararı' and the fund returns to the queue. `reject` makes the effective value `UNDECIDED`."
   - **Fix (§8, add):** "Tests: an UPDATE as `p50k_app` fails; a rerun after an override leaves the effective value unchanged; a packet change sends the fund back to the queue."

6. **High. D7, D6, §6 chat tools: the data sent to OpenAI has no enforcement point, and the plan overstates what OpenAI keeps**
   - **Problem:**
     - D7 is a list, not a mechanism. Nothing keeps raw TEFAS size, units and investor counts out of `get_fund_profile`, or KAP-parsed allocation weights out of the AN-FND-004 packets.
     - D7's "event text" includes KAP disclosures from the KAP spike, and KAP is exactly the source whose data rights are unreviewed.
     - Users' chat text leaves the machine with no notice to them (DEC-028 says user secrets never go into external queries).
     - D6's "nothing stored at OpenAI" is false: abuse-monitoring logs are kept for up to 30 days, and there is no Zero Data Retention.
     - Live mode can start before Safa answers Q11, and no DEC record is planned.
   - **Failure:** Mirza approves D7 believing that nothing is retained and only derived values leave. On Sunday, chat sends TEFAS investor counts and KAP text for any fund a user asks about.
   - **Fix (D7 Default cell):** "Derived evidence only, enforced in one module, `p50k.product.ai.egress`. Every OpenAI input (packets, chat tool outputs, summaries, extraction) is built from typed models with a field allowlist: detector values and thresholds, signal states, dates, categories, public fund codes and names, SPK event metadata, and short SPK quotes. Excluded: raw prices, TEFAS size, units and investors, KAP text and values derived from PDFs, and personal data. A unit test serializes every tool output and packet model and fails on any field outside the allowlist. The chat panel tells users that questions go to OpenAI and must not contain personal information. `P50K_AI_MODE=live` starts only after D7 is recorded in DEC-030, with Safa's answer or a note that he has not answered."
   - **Fix (D6 Why cell):** replace "nothing stored at OpenAI" with "not stored for later retrieval (`store: false`); OpenAI keeps abuse-monitoring logs for up to 30 days".

7. **High. §6 steps 2–3: the number rule and the wording list both have holes**
   - **Problem:**
     - A "bare digit" check misses numbers written as words ("yüzde kırk", "iki katına").
     - It also rejects real identifiers (TP2, D3, AN-FND-005, 2026/61, "17 Eylül"). That pushes the team to loosen the regex in a hurry.
     - A placeholder can be placed in the wrong sentence, for example a threshold presented as the value.
     - The wording list covers only fraud and advice. It does not cover prediction, safety, SPK-motive, lead-time or accuracy wording, all of which the do-not-claim list forbids.
   - **Failure:** A rationale says "eşiğin iki katına çıktı… tasfiye edilebilir". It passes every check and puts an invented magnitude and a prediction on a real fund.
   - **Fix (step 2):** "Numbers, dates and identifiers appear only as placeholders (`{{ev:<id>.<field>}}`, `{{fund}}`, `{{det:<id>}}`), which the server renders with the field's label. Any digit, or any Turkish number or magnitude word (bir…dokuz, on…doksan, yüz, bin, milyon, milyar, yüzde, kat, yarı, çeyrek, buçuk), outside a placeholder fails validation."
   - **Fix (step 3):** "Word-boundary phrase lists for:
     - allegation: dolandırıcılık, manipülasyon, usulsüzlük, suistimal, hile, saadet zinciri, kara para;
     - advice: satın al, almalı, satmalı, tutmalı, öneririm, tavsiye, kaçının, uzak durun;
     - prediction and safety: tahmin, öngörü, tasfiye edilecek, tasfiye edilebilir, batabilir, güvenli, risksiz, sorun yok;
     - SPK motives: SPK'nın gerekçesi, SPK'nın amacı;
     - performance: doğruluk, isabet, önceden yakaladı, erken uyarı.

     A Turkish corpus of passing and failing sentences runs in the AI-layer tests."

8. **High. §3 Secrets, T1.1–T1.5, §8 CI: secrets and real data can end up in images, containers, logs and agent transcripts**
   - **Problem:**
     - `.dockerignore` omits `.env*`, `secrets/`, `backups/` (T6.3's `pg_dump` of all real data goes there), `.git/`, `.claude/` and the overnight output.
     - Compose's `secrets.environment` source is unverified on v5.5.1. Its usual fallback, `env_file: .env`, puts the OpenAI key into every container, including `web`.
     - No hook stops agents reading `.env`. `docker compose config` and `docker inspect` print the interpolated values, which puts the key into the agent transcript, off the machine.
     - T1.5's logs have no redaction rule, and the plan drops the runtime review's rule to store only the error class for failed jobs.
   - **Failure:** The backend Dockerfile runs `COPY . .` before `uv sync`. The image layers then contain `.env` and, after T6.3, the database dump. A later push of the "deploy-ready" image publishes both.
   - **Fix (replace the §3 Secrets bullets):** "`.dockerignore` denies everything (`**`) and re-allows only `pyproject.toml`, `uv.lock`, `services/`, `db/` and `web/` without `.env*`. Secrets are `file:` sources under the gitignored `secrets/`. The OpenAI key and the pepper are mounted only into `api` and `worker`. There is no `env_file:` and no secret build argument. Secrets are held as `SecretStr`. Logs redact `Authorization`, `Cookie`, `X-CSRF-Token` and `password`, and never log request bodies for auth or chat. `ops.jobs` stores only the error class. Agents never open `.env` or `secrets/`, use `docker compose config --no-interpolate`, and check for leaks with a script that prints only counts. CI uses `permissions: contents: read` and actions pinned by commit SHA."
   - **Fix (T6.1, add):** "Scan the image layers, `docker inspect` output and the logs for the key's prefix."

9. **Medium-high. §8 "Before every commit", D1, D9, T2.2, T6.2: the leak scan is blind in the worktree**
   - **Problem:**
     - The worktree has no `raw/`, so `leak_scan.py` exits 2 and skips the price-value and fund-name checks. Nothing in the plan treats exit 2 as a failure.
     - Its code check covers only non-target codes from the top-100 list, but the product now names about 2,133 funds.
     - Overnight prices and the names of funds that are in no snapshot database are outside its reference sets.
     - D9's "new directories" are not located, and only `/raw/` is gitignored.
     - `test-results/` and `playwright-report/` are not gitignored, and the scan skips binary files.
   - **Failure:** The real-data demo check leaves traces naming non-top-100 funds in `web/test-results/`. The scan exits 2, the commit goes through, and the M5 merge carries the files into `main`.
   - **Fix (replace the "Before every commit" bullet):** "Leak scan with `P50K_RAW_DIR=<main checkout>/raw`; exit 1 or 2 blocks the commit. The reference sets include every name in `ref.funds` and the overnight price files. All fund codes are checked in `tests/`, fixtures, seeds and `*.json`/`*.csv`."
   - **Fix (D9, add):** "All overnight output goes under `~/.local/share/project-50k/overnight-2026-10-10/`."
   - **Fix (T1.1, add):** "Gitignore and dockerignore `test-results/`, `playwright-report/`, `*.sqlite3` and `*.dump`. Real-data Playwright runs write their output outside the worktree."
   - **Fix (T2.2, add):** "The golden test reads `raw/` through `P50K_RAW_DIR` and reports itself skipped without it. No fixture is cut from real data."
   - **Fix (Barış's asks, add):** "Deck screenshots come from the synthetic seed or show only the eight targets."

10. **Medium-high. §7 A and B: story screens and the pitch line**
    - **Problem:**
      - The partner panel's "covered funds" and "exposure grouped by manager" require a policy book that does not exist. It would show invented TRY amounts next to real managers, against DEC-027's no-synthetic-data rule for the demo.
      - The replay's eligibility check does not say which data it may use. Size, units, investors and category are latest values only (snapshots from 2026-10-06 and 2026-10-09). Detector tiers shown for the ordered funds would imply "would have caught".
      - Showing "triggers fired" next to the LLM's `MET` reads as if we decide claims.
      - The present-tense pitch line implies partners we do not have.
      - B2B rows and CSV files carry none of `development_result`, `origin`, `rights_status` or `decided_by`.
    - **Failure:** A judge sees ordered funds marked "uygun değil" in a replay dated before the order and concludes that the detectors foresaw it.
    - **Fix (§7A Screens):**
      1. A trigger check, labelled `HISTORICAL_REPLAY`. It uses only observations with `available_at` before the cutoff. Eligibility uses contract terms only: holding on the trigger date, the waiting period, and the cut-off after any public SPK action. No detector tiers are shown.
      2. A partner panel built on a policy book labelled `SYNTHETIC` ("Örnek portföy — gerçek poliçe yoktur") that uses only the eight target funds or pseudonyms. It is recorded as a DEC-027 exception, or cut.

      Add to the §7A AI bullet: "The trigger is the deterministic `trigger_fired`. The LLM's assessment is labelled 'bilgi amaçlı; hasar kararı sigortacıya aittir'."
    - **Fix (pitch line):** "Designed so that a licensed insurer issues the policy and a bank distributes it; we would supply the trigger and evidence. No insurer or bank partnership exists."
    - **Fix (§7B, add):** "Every feed and CSV row carries `development_result`, `origin`, `rights_status=UNREVIEWED`, `decided_by` and the review state. The CSV header reads 'Geliştirme sonucu; veri hakları incelenmedi; yatırım tavsiyesi değildir'. Demo exports are not shared."

11. **Medium. §3 Login, §12 "localhost only", T6.2**
    - **Problem:**
      - DNS rebinding lets any web page reach loopback services, and the plan has no Host allowlist and no default-deny routing.
      - Behind the Next proxy, a per-IP login throttle sees one IP for everyone, so one lockout hits the whole team. Trusting `X-Forwarded-For` instead would let a direct caller on 8770 bypass the throttle.
      - The Origin check's behaviour when the header is missing is unstated.
      - Seed passwords may be committed.
      - Chat threads are not scoped to their owner.
      - There is no per-user chat cap, and no role is set for "Yeniden değerlendir", so the $20 cap can be spent before the pitch.
    - **Failure:** A route added without the session dependency is read through a rebinding page. Or a few mistyped passwords at 12:50 on Sunday lock every demo account.
    - **Fix (§3 Login, add):**
      - "`TrustedHostMiddleware` (127.0.0.1, localhost, api, web) on the API, and the same Host check in Next middleware.
      - A router-level session dependency with a public allowlist (login, health, landing). A test walks `app.routes` and expects 401 for every other route without a session.
      - Throttle per `lower(email)` and per IP, trusting `X-Forwarded-For` only from `web`.
      - Reject state-changing requests that have no `Origin`.
      - Seed passwords are generated at run time and printed once, never committed.
      - Chat threads are filtered by `user_id`.
      - 30 chat turns per user per day. 'Yeniden değerlendir' is analyst-only and deduplicated by packet hash.
      - $5 of the $20 cap is held for Sunday 11:00–13:00 and released by an admin."

12. **Medium. D8 and T2.1: the plan calls the recalibration "the same preregistered rule"**
    - **Problem:** Widening the peer set to all funds changes the D1/D2/D4 statistic, so this is a v2 rule with thresholds fixed after 17 September. `research-protocols.md` requires a versioned protocol for that, committed alone and with an "Already seen before writing this" list. The plan asks only for a dated note and uses the word "preregistered".
    - **Failure:** The deck says "önceden kayıtlı eşiklerimiz N fonu işaretledi", which is a validated-method claim that DEC-029 forbids. Or the minimum-peer rule is tuned after a first run.
    - **Fix (D8 Default cell):** "D1–D5 v2 with all-fund peers. Before any computation, commit alone a dated v2 protocol beside the frozen v1 files. It fixes the percentile, the cutoff, the peer definition with its survivorship caveat, the minimum peer count and the abstain rule. It includes an 'Already seen before writing this' list: the 17 September order and its 131 funds, and the v1 results. Results are labelled 'development result; thresholds fixed after the event' and are never called preregistered or validated."