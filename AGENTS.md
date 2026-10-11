# Project 50K: instructions for coding agents

**Latest takeover checkpoint:** read `plans/2026-10-11-codex-handoff-prompt.md` (2026-10-11 10:40); earlier: `plans/2026-10-10-claude-resume-handoff.md`
in full. It separates the released app from unfinished date-context, chat-history
and monthly-report integration. Follow DEC-034's product-first pacing; do not
repeat broad Linux regressions or backup rehearsals for that unfinished slice.

The current product and hackathon demo scope is **Turkish investment funds and Turkish stocks**, set by [DEC-032](docs/decisions/DEC-032-b2b-evidence-data-api.md) on 2026-10-10. The first demonstrated case is the historical fund case; Mirza requires real stock support in the hackathon demo too. Current BIST 30 catalog, daily closes, source evidence and corporate-action observations are implemented in isolated modules under a new committed stock protocol. Stock anomaly classification/AI is not implemented; existing fund protocols remain immutable. Crypto, US equities and on-chain remain postponed. DEC-032 supersedes DEC-024's stock postponement; DEC-024's fund-first history and the frozen handoff remain preserved.

**Current direction (2026-10-10):**

- **[DEC-033](docs/decisions/DEC-033-nontechnical-product-experience.md).**
  - The product is for nontechnical users. Keep hashes, storage names, internal IDs, detector codes and status enums in audit/API records, not product screens.
  - Explain actual calculations, dated inputs, limits and the calculation-to-AI-to-human review process in plain language beside results.
  - Show the last usable price with its actual date when the latest entry is missing; preserve chart gaps and point-in-time rules.
  - Use verified company/manager logos. Never invent a brand or a missing financial value.
  - Stream server-validated chat paragraphs as generated. Explanations must answer the question, describe the evidence and cite its sources.
  - Rights-review status remains in operational documentation/API metadata; Mirza explicitly removed that warning from end-user screens. This does not authorize redistribution.
- **[DEC-032](docs/decisions/DEC-032-b2b-evidence-data-api.md).**
  - Sell evidence data and API access through an agent workflow to banks and financial institutions.
  - Insurance is permanently deferred; no insurance screens, policy workflows or insurer-review print view.
  - The historical fund case is first. Real BIST 30 data support is built; do not claim stock anomaly classification or stock AI.
  - Mirza's earlier alignment pause ended when he resumed, selected BIST 30 and requested parallel implementation of the supplied 22 Figma designs. No current pause is active.
  - Buyer class and revenue direction are decided; demand, pricing, partnerships and redistribution rights remain unvalidated.
- **[DEC-028](docs/decisions/DEC-028-deploy-ready-ai-native-build.md).**
  - Build a deploy-ready full-stack product that runs on localhost with real data: frontend, backend, PostgreSQL with its own email/password auth, and a worker, all in Docker.
  - Code freeze: Sunday 2026-10-11 13:00.
  - The product is **AI-native**. An LLM (OpenAI API) decides from deterministic detector evidence, a human can override every LLM decision, and users chat with the LLM in the UI.
  - Team: Mirza is the technical lead; Safa is business and owner; Barış is design.
- **[DEC-029](docs/decisions/DEC-029-open-all-funds.md).** Every downloaded fund is open for product use.
- **Specs.** The handoff's product requirements are guides, not hard rules. Raise important collisions instead of silently choosing. The integrity rules below stay binding.
- **[DEC-030](docs/decisions/DEC-030-blackswan-working-agreements.md) working agreements (2026-10-10).**
  - The product is called **BlackSwan**; Mirza supplied the Figma designs and logo, now implemented. See `docs/notes/blackswan-figma-completion.md` for verification and remaining limits.
  - **No placeholders** in the product: no lorem ipsum, fake values, "coming soon" screens, blank template rows, mock AI output or notes to the team. Messages for Mirza go in chat. Required integrity labels are real content, not placeholders.
  - **The $25 OpenAI budget is a target, not a hard cap.** Don't waste it; raise it only with a valid reason and Mirza's OK.
  - **The plan is confirmed by delegation.** Confirm items that serve the team's interest yourself; ask Mirza only about problematic ones, with clear options and a recommendation.
  - **Persistent reminders.** If Mirza misses something important (an unanswered question or unconfirmed information that affects everything), raise it again in every reply until he answers. Only for truly critical items.
- **Start here if you are Codex taking over:** `plans/2026-10-11-codex-handoff-prompt.md` (newest; specs in `plans/2026-10-11-sprint-briefs.md`). Older: `plans/2026-10-10-codex-handoff-prompt.md`.

## Read first, in this order

1. [docs/notes/current-state.md](docs/notes/current-state.md): where the project stands, what is decided and open, what to do next. Start here. Then [product direction](docs/notes/product-direction.md), the [open asks](docs/notes/team-asks.md) and the current plan in `plans/`.
2. [docs/notes/codex-context-2026-10-07.md](docs/notes/codex-context-2026-10-07.md): the detailed 2026-10-07 record. Its data-source facts, case study, evaluation rules and do-not-claim list (sections 5, 6, 7 and 11) still apply.
3. `docs/handoff-v0.5/AGENTS.md`: the shared integrity, auth, design and completion-report rules. They still apply except where later decisions, including DEC-024 and DEC-032, differ. Do not edit anything under `docs/handoff-v0.5/` (frozen; its `MANIFEST.json` hashes verify it).
4. `research/spikes/2026-10-06-tefas/REPORT.md`: what TEFAS and KAP actually return. Read it before touching a data adapter or a detector.
5. `docs/handoff-v0.5/docs/12_Anomaly_Catalog.md`: detector definitions. Use thresholds as written.

Your first reply should verify the repo state (run the tests listed below) and propose **one** vertical slice with requirement IDs, a file-change plan and acceptance tests. Implement only after the person you work with approves. Under DEC-027 the team and its agents make all repository writes; the owner only pulls.

## Rules that are easy to break

- **No real TEFAS or KAP values in git.** Their data rights are not reviewed. Raw files live under the repository-root, gitignored `raw/`; SQLite databases stay in `~/.local/share/project-50k/`. Legacy research paths are ignored compatibility symlinks. See [local data layout](docs/notes/local-raw-data-layout.md). Tests use synthetic values only. Before committing, check staged files for real values.
- **Missing stays missing.** TEFAS writes `0` for "no price": treat it as `None`. Never fill gaps with zeros or invent dated history. Fund NAV is daily, published-cadence data; no intraday candles.
- **Point in time.** Use a value only from the moment it was published: a TEFAS row dated D from about 11:05 on D, a KAP report from its publish time. Add a look-ahead test to any detector or replay code.
- **All downloaded funds are in scope (DEC-029), and there is no held-out test set.** Label every detector figure a development result; never present it as validated accuracy, recall or lead time. Commit a short dated note fixing the parameters before running a recalibration or a new detector.
- **AI rules (DEC-028).**
  - Detectors compute every score, threshold and trigger. The LLM never changes a number.
  - LLM decisions are stored with their evidence references, model and prompt version, and a human override is stored beside the original.
  - Chat tools are read-only and bounded, and the server validates their arguments.
  - Material claims cite evidence, and insufficient evidence is said plainly.
  - No buy/hold/sell or personalized advice, and no fraud or manipulation claims.
  - The OpenAI key stays server-side and gitignored. Mirza supplied the approved `secrets/openai_api_key` file, mounted into Docker; never read or print it in agent tools, chat, logs or Git.
- **Do not edit the pre-registered detectors** (`research/events/2026-09-17-spk-liquidations/price_detectors/detectors.py`, `PREREGISTRATION.md`, `results.json`) or any committed `PROTOCOL.md` or `PREREGISTRATION.md` under `research/events/` (for example in `fund_futures_divergence/` and `fund_holdings_divergence/`). Write a v2 or a new versioned protocol beside them.
- **Sealed bundles re-hash their registered files on every load.** Editing one (listed in `tests/unit/registered_sources.lock.json`, plus the `dated_*.py` modules and the event's `run.py` runners) makes the running app answer 503 until every affected bundle is resealed. Add new modules beside them instead.
- **Naming.** Committed files name only the eight liquidated top-100 funds. Never name other funds as flagged or suspicious. An anomaly is not fraud, and SPK's reasons for its order are not in our files.
- **Pacing.** TEFAS: 1.5 s between requests. KAP: 6 s (a 1.5 s pace got us cut off after about 180 requests).
- **No external actions without explicit authorization from Mirza or Safa:** spending, creating accounts (Google OAuth, Supabase, email, hosting), deploying, installing the systemd timer in `ops/systemd/`, contacting third parties. DEC-028 authorizes the OpenAI API key that Mirza provides, with a $25 limit. The TRY 5,000 ceiling is not authorization to spend.
- **Line endings.** `.gitattributes` forces LF; sealed bundles, runner registration and the handoff `MANIFEST.json` hash LF bytes. On Windows, never re-save tracked files with CRLF.
- **Claude Code hooks** in `.claude/` block most of these mistakes for Claude Code sessions only; other agents must follow the rules by hand. See [agent tooling](docs/notes/agent-tooling.md).
- **The local demo depends on two checkouts.** On the team's Windows machine the demo runs from the dated-view clone, but its fixed bundle re-hashes the main checkout's registered files and snapshot database on every load. While it runs, do not switch branches or change those files in the main checkout, and do not run `npm run build` in the clone whose `.next` the demo serves. See `docs/notes/current-state.md`.
- **Dated D1 view and merging.** DEC-026 and `fund_review_dated/PROTOCOL.md` govern the dated view (frozen once a real date index is sealed). Per DEC-027 the owner only pulls; merge with merge commits only, never squash or force-push, so protocol commits stay in `main`'s history.

## Commands

Install the locked environment with `uv sync --locked --extra api --extra api-test --extra research` and `npm ci --prefix frontend`. `PY` is `.venv/bin/python` (Windows: `.venv/Scripts/python.exe`). From the repo root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services $PY -m unittest discover -s tests -t . -v   # 605 tests at 33c6064; missing extras are skips, not passes
(cd research/events/2026-09-17-spk-liquidations/price_detectors && ../../../../$PY -m unittest test_detectors -v)   # 9 frozen detector tests
(cd docs/handoff-v0.5 && ../../$PY -m unittest discover -s tests -v)                     # 88 offline reference tests
(cd frontend && npm run typecheck && npm test && NEXT_TELEMETRY_DISABLED=1 npm run build)  # never in a checkout whose .next a running demo serves; browser tests: npm run test:browser
```

On Windows the root suite has known platform failures (tzdata, CRLF fixtures, console encoding, SQLite locks, `SO_REUSEADDR`); `.claude/skills/p50k-verify/SKILL.md` lists them and the diagnostic variant. Compare failing test names, not only counts.

## Layout

| Path | Content |
|---|---|
| `services/p50k/` | Backend package: `providers/` (TEFAS client, KAP report reader, holdings parsers, retry and circuit breaker, disk cache), `jobs/` (fund snapshots, price history), `evidence_store.py`, `replay.py`, `research_reviews/` (sealed research bundles), `api/` (read-only FastAPI apps) |
| `frontend/` | Next.js App Router app in Turkish: the fixed-date view, `/dates` and synthetic `/preview` scaffolds |
| `ops/local/` | Loopback launchers for the fixed-date and dated apps |
| `tests/unit/` | Unit tests for `services/p50k/` |
| `research/spikes/` | Provider spikes with the field-by-field data report |
| `research/events/2026-09-17-spk-liquidations/` | The SPK liquidation case study: notes, fund lists, pre-registered price detectors and results, and the protocols and runners of the sealed research views |
| `raw/` | Local-only, gitignored data: `tefas/prices`, `tefas/responses`, `tefas/logs`, `tefas/price-detectors`, `kap/reports`, `kap/series`, `spk`, and sealed outputs in `research/`. Absent from a fresh clone |
| `docs/decisions/`, `docs/notes/` | Owner decisions and working notes. Record new decisions here |
| `ops/systemd/`, `ops/windows/` | Daily snapshot timer (Linux, not installed) and the Windows scheduled-task script |
| `plans/` | Implementation plans and session prompts |
| `.claude/` | Claude Code skills, hooks and path rules ([agent tooling](docs/notes/agent-tooling.md)) |
| `docs/handoff-v0.5/` | Frozen v0.5 handoff: requirements, anomaly catalog, contracts, reference harness |

## Working style

- Code, commit messages, docs and prompts in English. Reply in the language of the person you work with: Mirza wants concise English; Safa prefers simple, short Turkish.
- When you need a decision or an action from Mirza, Safa, Barış or the team, add it to `docs/notes/team-asks.md` and say so in your reply.
- Small vertical slices with tests. Before editing, list ambiguities that could cause an irreversible or unsafe choice.
- Match the surrounding code: `from __future__ import annotations`, type hints, `Decimal` for prices, `None` for unknown, atomic file writes, `unittest` (not pytest).
- End every task with the handoff's completion report: requirement IDs, changed files, the exact tests run and their output, what is untested, the data mode, limitations, and the next recommended task. Never report a test as passed that you did not run.
- `gh pr edit` fails here with a "Projects (classic)" error. Edit PR descriptions with `gh api -X PATCH repos/Safa675/project-50k/pulls/N -F body=@file`.
