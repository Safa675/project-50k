# Project 50K: runtime and AI integration design

**Bottom line:** the design below needs about 19.5 hours of work, but only about 14–16 working hours remain before the 13:00 Sunday freeze. Two things decide whether it lands: agreeing the cut list in section 10, and a Mirza/Safa decision on what real data may be sent to OpenAI (collision 4).

This was a read-only review at about 12:45 (Istanbul) on 2026-10-10, against `main` at `36cffaf`; nothing was installed, started or written. Web sources were accessed 2026-10-10 and are listed at the end. All hour and dollar figures are estimates.

## 1. What exists today
The repository root is `C:\Users\mirza\Desktop\Hackathon\project-50k`.
- **Backend** (`C:\Users\mirza\Desktop\Hackathon\project-50k\pyproject.toml`, `C:\Users\mirza\Desktop\Hackathon\project-50k\uv.lock`):
  - Python ≥3.13; the local `.venv` runs 3.13.15.
  - Locked: fastapi 0.143.0, uvicorn 0.54.0, pydantic 2.14.0.
  - There is no database driver, OpenAI SDK or password library.
- **Frontend** (`C:\Users\mirza\Desktop\Hackathon\project-50k\frontend\package.json`):
  - next 16.4.0 is npm's `latest` and needs node ≥20.9.0; react is 19.3.0.
  - It builds with `next build --webpack`, and `postinstall` runs `prepare:pdfjs`.
- **API proxy** (`C:\Users\mirza\Desktop\Hackathon\project-50k\frontend\next.config.ts`): it throws unless the API origin is loopback HTTP, and it rewrites `/api/research/*` to the API.
- **Launcher** (`C:\Users\mirza\Desktop\Hackathon\project-50k\ops\local\run_app.py`): starts Uvicorn and Next on 127.0.0.1 from a sealed bundle. There is no database.
- **Data:**
  - 2,022 price files in `raw\tefas\prices`;
  - 1,871 files under `raw\kap`;
  - forward snapshots in SQLite (`C:\Users\mirza\Desktop\Hackathon\project-50k\services\p50k\jobs\fund_snapshots.py`).
- **Missing:** Docker files, `.dockerignore` and `.github\`. `.gitignore` covers `.env*` but not `secrets/` or `backups/`.
- **Machine:**
  - Docker 29.8.0, Compose v5.5.1, Node 24.14.1, uv 0.12.17 and WSL2 Ubuntu.
  - Ports 3060, 8767 and 8768 are listening (the demo); 3070, 8770 and 5433 are free.
  - The GPU is not needed.
- **Decisions:** DEC-028 (stack, AI rules, $25) and DEC-029 (all funds open; development results only) are committed.

## 2. Collisions to settle before coding
1. **The running demo.** The main checkout is load-bearing (`C:\Users\mirza\Desktop\Hackathon\project-50k\docs\notes\current-state.md`). Build in a third clone, with a copy of `raw/` or a read-only mount of it.
2. **Absolute Windows paths.** Sealed bundles store them, so the research API cannot run in Linux containers. The product loads `raw/` into PostgreSQL instead, and the research app stays outside Compose.
3. **The `next.config.ts` guard.** It rejects `http://api:8000`, and rewrites are fixed at build time. Add product proxy route handlers that read an allowlisted API address at runtime, and leave the research rewrite untouched.
4. **Real data sent to OpenAI.** Data rights are unreviewed (DEC-027; `C:\Users\mirza\Desktop\Hackathon\project-50k\docs\notes\product-direction.md`). Handoff doc 17 §3 says to honour "retention and model-processing rights". Mirza or Safa must decide. My proposal:
   - send only detector evidence, dates, categories and public identifiers;
   - send no raw price series and no PDFs;
   - set `store: false` on every OpenAI call.
5. **Handoff auth.** Doc 14 assumed Supabase row-level security and Google sign-in. DEC-028 drops both, so every permission check moves into the API. Keep doc 14's server-side session checks, admin by membership, and revocation tests.
6. **Insurance triggers.** A payout trigger must be computed deterministically. The LLM's "appears met" verdict (DEC-028) is advice to a human, who must confirm it. SEDDK and SPK licensing questions are open; this design makes no legal claims.
7. **Leaks into images.** Without a `.dockerignore`, building from the repository root sends `raw/` to the Docker daemon. Add it, and gitignore `secrets/` and `backups/`, before the first build.
8. **OpenAI stores responses by default.** Set `store: false` and keep conversation history in PostgreSQL instead of using `previous_response_id`.

## 3. Architecture
```
Browser (tr-TR) ─127.0.0.1:3070─► [web] Next 16.4 standalone
                                    pages + proxy /api/p/* (cookie, CSRF, SSE pass-through)
B2B client ─127.0.0.1:8770─┐          │ http://api:8000
                           ▼          ▼
                   [api] FastAPI + Uvicorn ───────────► OpenAI Responses API
                     auth, funds, signals, decisions,     (streamed chat, store:false)
                     chat with read-only tools
                           │ psycopg pool
[migrate] ─SQL─► [db] PostgreSQL 18.6 ◄─ [worker] job queue (SKIP LOCKED + leases),
                     volume pgdata          scheduler, importers, D1–D5, evidence,
                                            AI decisions ─► OpenAI
                                              ▲ read-only: raw/, forward SQLite
```
- Every host port binds to 127.0.0.1 (DEC-027).
- Calls to TEFAS and OpenAI happen outside database transactions (doc 14).
- With AI switched off, the deterministic pages still work.

## 4. Compose services (one `compose.yaml`)
| Service | Image | Command and notes | Host port |
|---|---|---|---|
| `db` | `postgres:18.6-trixie` | Mount the volume at `/var/lib/postgresql`; version 18 moved `PGDATA` to `/var/lib/postgresql/18/docker`. Uses `POSTGRES_PASSWORD_FILE` and a `pg_isready` healthcheck | none; the `dev` profile adds 127.0.0.1:5433 |
| `migrate` | backend | `python -m p50k.db.migrate`; runs once, after `db` is healthy | – |
| `api` | backend | `uvicorn p50k.product.app:create_app --factory --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers`; starts after `migrate` succeeds | 127.0.0.1:8770 |
| `worker` | backend | `python -m p50k.worker`; `raw/` and the forward SQLite mounted read-only | – |
| `web` | frontend | `node server.js` with `HOSTNAME=0.0.0.0` and `PORT=3000` | 127.0.0.1:3070 |
| `test` | backend, `test` stage | `test` profile (section 9) | – |
| TLS proxy | not chosen | `vps` profile, for later; needs `P50K_COOKIE_SECURE=true` and `--forwarded-allow-ips` | 80/443 |

- **Backend image:**
  - Base `python:3.13-slim-trixie`. Copy uv in with `COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /bin/`, matching the local uv (0.13.0 is the latest release).
  - Set `UV_COMPILE_BYTECODE=1` and `UV_LINK_MODE=copy`.
  - Install dependencies in their own layer with `uv sync --locked --no-install-project`, then run `uv sync --locked --no-dev --no-editable`, as the uv Docker guide shows.
  - Run as a non-root user. Write the healthchecks in Python, because slim images have no curl.
  - New `product` extra: `openai==3.28.0`, `psycopg[binary,pool]` (psycopg 3.3.6, psycopg-pool 3.3.3) and `argon2-cffi==25.1.0`.
- **Web image:**
  - Base `node:24-trixie-slim`. Copy `scripts/` in before `npm ci`, because `postinstall` needs it.
  - Set `output: 'standalone'`. Copy `.next/static` and `public` (the pdf.js files) into the standalone folder yourself, as the Next.js docs require.
  - Building inside Linux avoids the Windows symlink problem the same docs mention.
- **Serving:** FastAPI's docs recommend `fastapi run`, which wraps Uvicorn, and accept `--workers` for a single-server Compose setup. Uvicorn is already locked, so call it directly. With several worker processes, keep rate limits, caches and budgets in PostgreSQL rather than in memory.
- **Secrets:**
  - The gitignored `.env` (DEC-028) holds `OPENAI_API_KEY`, `POSTGRES_PASSWORD` and `P50K_KEY_PEPPER`.
  - Compose `secrets:` with an `environment:` source mounts them as files under `/run/secrets/`; the app reads the `*_FILE` variables.
  - Commit only `.env.example`, and check with `docker inspect` that no key shows in the container environment.
- **Backups:** run `pg_dump` into the gitignored `backups/` before the freeze.

## 5. Database schema outline
| Schema | Tables |
|---|---|
| `ref` | `funds` (code, name, category, first_price_date, status); `sources` (url, `rights_status` defaulting to `UNREVIEWED`) |
| `obs` | `fund_prices` (fund, date, price as `numeric`, total_value, units, investors, origin, effective_at, available_at, ingested_at, file_sha256); `fund_snapshots`; `kap_documents`; `ingest_runs` |
| `det` | `detector_versions` (params, code_sha256); `detector_runs` (as_of, input_watermark); `signals` (fund, detector, value, threshold, fired, coverage, `development_result`); `evidence_items` (uuid, payload, content_sha256, origin, availability times) |
| `ai` | `decisions` (fund, as_of, decision, rationale_tr, evidence_ids, model, effort, prompt and packet hashes, validation, status); `decision_reviews`, append-only; view `effective_decisions`; `chat_threads`; `chat_messages`; `calls` (tokens including cached and reasoning, cost_usd); `budget`; `cache` |
| `auth` | `users` (unique `lower(email)`, password_hash, role); `sessions` (token_sha256, csrf_token, expiry times, revoked_at); `login_attempts` |
| `b2b` | `organizations`; `api_keys` (prefix, secret_hmac, scopes, expiry, revoked_at); `usage` |
| `ops` | `jobs`; `schedules`; `schema_migrations`; `audit_log`, append-only |

## 6. Migrations and the worker
**Use plain SQL migrations, not Alembic.**
- Alembic 1.20.0 depends on SQLAlchemy 2.1.4, and its automatic migration generation needs ORM models, which we do not have.
- Store migrations as `db/migrations/NNNN_*.sql`.
- A runner of roughly 60 lines:
  - takes `pg_advisory_lock`;
  - applies each file in its own transaction;
  - records a checksum;
  - refuses a file changed after it was applied;
  - only moves forward.

**The worker** is one process with a psycopg pool and no Redis. It claims jobs like this:
```sql
WITH next AS (
  SELECT id FROM ops.jobs
  WHERE (state='queued' AND run_after<=now())
     OR (state='running' AND lease_until<now())      -- expired lease
  ORDER BY priority, run_after, id
  FOR UPDATE SKIP LOCKED LIMIT $1)
UPDATE ops.jobs j SET state='running', lease_owner=$2,
  lease_until=now()+$3::interval, attempts=attempts+1
FROM next WHERE j.id=next.id RETURNING j.*;
```
- **Ownership:** heartbeat, completion and failure updates all require `lease_owner=$2`.
- **Retries:** after `max_attempts` a job becomes `dead`. Before that it is requeued with exponential backoff and jitter. Store the error class, never secrets or prompts.
- **Duplicates:** a `unique_key` with `ON CONFLICT DO NOTHING`.
- **Scheduler:** ticks under `pg_try_advisory_lock`; `LISTEN/NOTIFY` wakes the worker, with a 2-second polling fallback.
- **Job types:** `import_archive`, `import_snapshots`, `run_detectors(as_of)`, `build_evidence`, `ai_decide` and `ai_summarize`. `run_detectors` imports the frozen D1–D5 code without editing it.
- **Tests:** two workers at once, recovery after a worker is killed, and duplicate enqueues.
- **Forward SQLite:** read it only after the Windows collector has finished, and read-only. SQLite locking across the Docker bind mount is a risk.

## 7. Sign-in and API keys
- **Passwords:** Argon2id through `argon2-cffi` 25.1.0's `PasswordHasher`, re-hashed at login when parameters change. Not bcrypt, because bcrypt only reads the first 72 bytes of a password.
- **Sessions, not JWT:** session tokens are stored on the server, so they can be revoked at once (doc 14 notes JWT's limits here).
  - The token is 32 random bytes in the `p50k_session` cookie (`HttpOnly`, `SameSite=Lax`, `Secure` behind TLS). Only its SHA-256 hash is stored.
  - Sessions expire after 12 hours, or after 2 hours idle.
  - A new token is issued at login; tokens are revoked at logout and on password change.
- **CSRF:** require an `X-CSRF-Token` header on state-changing requests, and check the `Origin` header.
- **Roles:** `viewer`, `analyst` (may override AI decisions) and `admin`, checked on the server for every route.
- **Accounts:** no self-signup and no email. `python -m p50k.cli create-user` reads the password from stdin. Failed logins are throttled.
- **B2B keys:**
  - Format `p50k_<prefix>_<32-byte secret>`, shown once.
  - Store the prefix and HMAC-SHA256(pepper, secret), and compare with `hmac.compare_digest`. A fast keyed hash is safe for long random keys.
  - Keys carry scopes, expiry, revocation, per-minute usage counts and an audit trail.
  - The read-only `/b2b/v1/{funds,signals,decisions,exports}` endpoints label every response with `origin`, `development_result` and `rights_status`.

## 8. AI integration
**Recommended models** (prices from OpenAI's pricing page, in $ per 1M tokens: input / cached input / output):

| Use | Primary | Fallback |
|---|---|---|
| Tool-using chat and decisions | `gpt-6.1-sol` (2.00 / 0.10 / 10.00); reasoning effort low for chat, medium for decisions | `gpt-6-luna` |
| Bulk summaries | `gpt-6-luna` (0.10 / 0.01 / 0.50); effort `none` or `low` | `gpt-5.4-nano` (0.20 / 0.02 / 1.25) |
| Do not use | `gpt-6-astra` (10.00 / 1.00 / 50.00) | |

- **Use the Responses API.** OpenAI recommends it for new projects, and `gpt-6.1-sol` has no tool calling through Chat Completions.
- **Model features:** both models list streaming, structured outputs, function calling and prompt caching.
- **Rate limits:** the model pages show "Build tier" limits; this account's tier is unverified.
- **SDK:**
  - `openai` 3.28.0, released 2026-10-09; it needs Python ≥3.10.
  - Its README shows `client.responses.create(...)` and `stream=True`.
  - Request structured output with `text.format` set to a strict `json_schema`. Function tools are strict by default. Validate every result again with Pydantic.
- **Configuration:** model IDs and prices live in environment variables and config, so they can change without code changes.

**Decision records with human override:**
1. **Evidence packet.** The worker builds one per fund and date, then hashes it. It holds each detector's value, threshold, coverage and fired flag with their evidence IDs, plus KAP metadata.
2. **Model output.** The LLM returns strict JSON:
   - `decision`: `MATERIAL`, `NOT_MATERIAL` or `INSUFFICIENT_EVIDENCE`; or, for the insurance version, `APPEARS_MET`, `NOT_MET` or `UNCLEAR` against a deterministic trigger;
   - `cited_evidence_ids`, `rationale_tr` and `missing_evidence_tr`;
   - no scores.
3. **Server checks.** The server verifies:
   - the schema;
   - that every cited ID is in the packet;
   - that numbers appear only as `{{ev:<id>.<field>}}` placeholders, which the server fills in, so any bare digit fails;
   - that the Turkish text contains no advice or fraud wording.

   One retry is allowed. After that the record is marked `INVALID` and a template text is shown instead.
4. **Storage and review.**
   - The record is stored as `AI_PROPOSED` with the model, effort, hashes and call ID, and shown as "Yapay zekâ önerisi".
   - Analysts accept it, override it (with a required reason) or reject it. Reviews are append-only.
   - The UI and B2B API show `decided_by: ai|human`.
   - Chat never writes decisions; a "yeniden değerlendir" button queues a new `ai_decide` job.

**Chat:**
- **Tools:** `search_funds`, `get_fund_profile`, `get_signals`, `get_return_summary` (computed on the server), `list_flagged_funds`, `get_decision`, `get_methodology` and `get_kap_documents` (metadata only).
  - Each has a strict schema, fixed SQL and role checks, and returns at most 4 KB with evidence IDs.
  - There is no web search, raw SQL, URL fetching or write access.
- **Limits per turn:** at most 3 model calls, 6 tool calls and 45 seconds (doc 17). The model sees the last 8 messages, and tool output is marked as untrusted data.
- **Streaming:**
  - FastAPI's `StreamingResponse` sends server-sent events: our own `delta`, `tool`, `done` and `error` events, mapped from OpenAI's `response.output_text.delta`, `response.function_call_arguments.delta` and `response.completed`.
  - The Next route handler passes the stream through with `no-transform`. The browser reads it with `fetch`, because the request is a POST.
  - Test for buffering on day one.
- **Answer check:** every number in an answer must match a number from that turn's tool results; otherwise the UI shows a warning. `[ev:…]` markers render as evidence chips.

**Staying within $25:**
- **OpenAI limit:** set a $25 hard limit on the OpenAI project, plus alerts. When reached it returns 429 `project_spend_limit_exceeded`, but OpenAI says enforcement is "not instantaneous", so our own cap is $20.
- **Reservation before each call:** one conditional `UPDATE ai.budget … WHERE spent+reserved+$x <= soft_cap` reserves the worst-case cost; the real cost from `usage` is settled afterwards. Over the cap, the AI panels say so and the rest of the product keeps working.
- **Caching:**
  - An exact-request cache, keyed by model, effort, prompt, schema and packet hash, makes reruns free.
  - Decisions are redone only when the evidence packet changes.
  - A fixed instruction and tool prefix gets OpenAI's cheaper cached-input price.
- **Modes:** `P50K_AI_MODE=off|mock|live`. Development and CI use `mock`.

| Item | Assumption | Estimate |
|---|---|---|
| Summaries for all 2,022 funds (luna) | 2.5k tokens in, 0.5k out | ≈$1 per run |
| Decisions (sol) | up to 300 fund-dates; 6k in (half cached), 1.2k out | ≈$5.5 |
| Chat (sol) | 300 turns × about 2.5 calls | ≈$8 |
| Live testing and reserve | | ≈$5 |
| **Total** | | **≈$19.5** |

**OpenAI data handling:**
- API data is not used for training by default.
- Abuse-monitoring logs are kept for up to 30 days.
- Zero Data Retention needs OpenAI's approval.
- Data-residency options exist; this account's eligibility is unverified.

## 9. Linux tests and CI
- **Test container:** the slim backend image plus `git` and time-zone data (a missing `tzdata` is one of the known Windows failures).
  - It runs `uv sync --locked --extra api --extra api-test --extra research`, then the root suite and the two frozen suites (commands in `/p50k-verify`).
  - `.gitattributes` forces LF line endings, and `.dockerignore` keeps `raw/` out.
  - Fallback: clone into WSL2 and run the same commands.
  - The root suite has never been run on Linux at `33c6064`, so treat every failing test name as a finding.
- **GitHub Actions** (`.github/workflows/ci.yml`; read-only token, no secrets, AI in `mock` mode). Jobs:
  - `python`: a `postgres:18.6` service container; `actions/checkout` v7.0.1 and `astral-sh/setup-uv` v10.3.0, both pinned by commit SHA;
  - `frontend`: `actions/setup-node` v7.1.0 with Node 24, then `npm ci`, typecheck, vitest and build;
  - `compose`: `docker compose config -q`, then `docker compose build`;
  - `leak-scan`: fails if a fund code outside the allowlist appears.
- Branch protection is Safa's setting.

## 10. Effort (Mirza with coding agents; about 14–16 working hours left)
| Slice | Hours | Priority |
|---|---|---|
| Third clone, `.dockerignore`, env files, Dockerfiles, compose | 1.5 | Must |
| SQL migrations and runner | 1.0 | Must |
| Importers (2,022 price files, snapshots, KAP metadata) | 2.0 | Must |
| D1–D5 over all funds, writing signals and evidence | 1.5 | Must |
| Worker and concurrency tests | 1.5 | Must |
| Auth, CLI and login screen | 1.5 | Must |
| AI layer, decisions and override | 2.5 | Must |
| Chat (tools, streaming, proxy, panel) | 2.5 | Must |
| Fund list and detail, decision screens, admin (reusing existing components; Barış designs) | 2.5 | Must |
| B2B keys and endpoints | 1.0 | Should |
| Test container and CI | 1.0 | Should |
| End-to-end smoke test and completion note | 1.0 | Must |
| **Total** | **19.5** (17.5 Must) | |

**This does not fit.** Agree the cuts now, in this order:
- B2B keys (show the OpenAPI page instead);
- the CI `compose` job;
- the scheduler (queue jobs from the CLI instead);
- KAP beyond metadata;
- summaries for all funds.

**Checkpoints:**
- data and detectors in PostgreSQL by about 19:00 Saturday;
- decisions and auth by about 01:00;
- chat and UI by 10:00 Sunday;
- freeze checks from 12:00.

## 11. Risks
| Risk | Mitigation |
|---|---|
| Running out of time | Agreed cut list; build the demo path first |
| Breaking the live demo | Third clone; ports 3070, 8770 and 5433; never build in the dated clone |
| Data rights when sending data to OpenAI | Decide first; send minimal packets; `store: false` |
| Overspending or a runaway loop | Hard limit, $20 internal cap, reservations, per-turn limits, mock mode |
| Invented numbers or advice wording | Placeholders, ID and number checks, wording blocklist, human override |
| New model IDs or rate tier | IDs in env, fallback chain, one-call smoke test |
| Next buffering the chat stream | Pass-through handler, tested early |
| Private data in images or git | `.dockerignore`, gitignore, leak scan, CI without data |
| Bugs in our own auth | Standard building blocks, tests, localhost only |
| Development results read as accuracy | `development_result` labels (DEC-029) |

## Sources (accessed 2026-10-10)
- **OpenAI:**
  - models: https://developers.openai.com/api/docs/models, plus `/models/gpt-6.1-sol` and `/models/gpt-6-luna`;
  - pricing: https://developers.openai.com/api/docs/pricing;
  - Responses migration: https://developers.openai.com/api/docs/guides/migrate-to-responses;
  - data controls: https://developers.openai.com/api/docs/guides/your-data;
  - spend limits: https://developers.openai.com/api/docs/guides/spend-limits (read only through a search-result summary);
  - SDK: https://pypi.org/project/openai/.
- **Package versions:** PyPI JSON at `https://pypi.org/pypi/<name>/json` for alembic, SQLAlchemy, psycopg, psycopg-pool, argon2-cffi, pwdlib, bcrypt, fastapi and uvicorn; npm at https://registry.npmjs.org/next/latest.
- **PostgreSQL:**
  - versions: https://www.postgresql.org/support/versioning/ (18.6 is current; Docker Hub shows 19 at beta4);
  - image notes: https://github.com/docker-library/docs/blob/master/postgres/content.md;
  - Docker Hub tags for postgres, python and node.
- **Next.js:** https://nextjs.org/docs/app/api-reference/config/next-config-js/output
- **FastAPI:** https://fastapi.tiangolo.com/deployment/docker/
- **uv:** https://docs.astral.sh/uv/guides/integration/docker/
- **GitHub Actions:** releases API for actions/checkout, actions/setup-node, astral-sh/setup-uv and astral-sh/uv.

**Still unverified:**
- Compose's `secrets.environment` source on v5.5.1;
- the names of the prompt-caching parameters;
- this account's rate tier and data-residency eligibility;
- the Batch API completion window (Batch halves prices, but its window may run past the freeze);
- the GitHub Actions minutes available to a private repository;
- the choice of TLS proxy;
- every cost and hour estimate.