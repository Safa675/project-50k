# Project 50K: instructions for coding agents

The current scope is **Turkish investment funds (TEFAS) only**, set by [DEC-024](docs/decisions/DEC-024-turkish-funds-first.md) on 2026-10-06. BIST, crypto, US equities and on-chain are postponed, not dropped. DEC-024 overrides every statement in `docs/handoff-v0.5/` that calls the four-market/on-chain target binding.

## Read first, in this order

1. [docs/notes/current-state.md](docs/notes/current-state.md): where the project stands, what is decided and open, what to do next. Start here.
2. [docs/notes/codex-context-2026-10-07.md](docs/notes/codex-context-2026-10-07.md): the detailed 2026-10-07 record. Its data-source facts, case study, evaluation rules and do-not-claim list (sections 5, 6, 7 and 11) still apply.
3. `docs/handoff-v0.5/AGENTS.md`: the shared integrity, auth, design and completion-report rules. They still apply except where DEC-024 differs. Do not edit anything under `docs/handoff-v0.5/` (frozen; its `MANIFEST.json` hashes verify it).
4. `research/spikes/2026-10-06-tefas/REPORT.md`: what TEFAS and KAP actually return. Read it before touching a data adapter or a detector.
5. `docs/handoff-v0.5/docs/12_Anomaly_Catalog.md`: detector definitions. Use thresholds as written.

Your first reply should verify the repo state (run the tests listed below) and propose **one** vertical slice with requirement IDs, a file-change plan and acceptance tests. Implement only after the person you work with approves. Under DEC-027 the team and its agents make all repository writes; the owner only pulls.

## Rules that are easy to break

- **No real TEFAS or KAP values in git.** Their data rights are not reviewed. Raw files live under the repository-root, gitignored `raw/`; SQLite databases stay in `~/.local/share/project-50k/`. Legacy research paths are ignored compatibility symlinks. See [local data layout](docs/notes/local-raw-data-layout.md). Tests use synthetic values only. Before committing, check staged files for real values.
- **Missing stays missing.** TEFAS writes `0` for "no price": treat it as `None`. Never fill gaps with zeros or invent dated history. Fund NAV is daily, published-cadence data; no intraday candles.
- **Point in time.** Use a value only from the moment it was published: a TEFAS row dated D from about 11:05 on D, a KAP report from its publish time. Add a look-ahead test to any detector or replay code.
- **Do not tune detectors on the funds you evaluate them on.** The owner's development/test split is still undecided. Until it is, **do not compute detector output, thresholds or any other statistic on the 1,922 downloaded price files outside `research/events/2026-09-17-spk-liquidations/top100_funds.txt`.** Read section 7 of the context file.
- **Do not edit the pre-registered detectors** (`research/events/2026-09-17-spk-liquidations/price_detectors/detectors.py`, `PREREGISTRATION.md`, `results.json`) or any committed `PROTOCOL.md` or `PREREGISTRATION.md` under `research/events/` (for example in `fund_futures_divergence/` and `fund_holdings_divergence/`). Write a v2 or a new versioned protocol beside them.
- **Sealed bundles re-hash their registered files on every load.** Editing one (listed in `tests/unit/registered_sources.lock.json`, plus the `dated_*.py` modules and the event's `run.py` runners) makes the running app answer 503 until every affected bundle is resealed. Add new modules beside them instead.
- **Naming.** Committed files name only the eight liquidated top-100 funds. Never name other funds as flagged or suspicious. An anomaly is not fraud, and SPK's reasons for its order are not in our files.
- **Pacing.** TEFAS: 1.5 s between requests. KAP: 6 s (a 1.5 s pace got us cut off after about 180 requests).
- **No external actions without the owner's say-so:** spending, creating accounts (Google OAuth, Supabase, LLM keys, email, hosting), deploying, installing the systemd timer in `ops/systemd/`, contacting third parties. The TRY 5,000 ceiling is not authorization to spend.
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

- Code, commit messages, docs and prompts in English. Reply in the language of the person you work with; the owner prefers simple, short Turkish.
- Small vertical slices with tests. Before editing, list ambiguities that could cause an irreversible or unsafe choice.
- Match the surrounding code: `from __future__ import annotations`, type hints, `Decimal` for prices, `None` for unknown, atomic file writes, `unittest` (not pytest).
- End every task with the handoff's completion report: requirement IDs, changed files, the exact tests run and their output, what is untested, the data mode, limitations, and the next recommended task. Never report a test as passed that you did not run.
- `gh pr edit` fails here with a "Projects (classic)" error. Edit PR descriptions with `gh api -X PATCH repos/Safa675/project-50k/pulls/N -F body=@file`.
