# Project 50K: instructions for coding agents

The current scope is **Turkish investment funds (TEFAS) only**, set by [DEC-024](docs/decisions/DEC-024-turkish-funds-first.md) on 2026-10-06. BIST, crypto, US equities and on-chain are postponed, not dropped. DEC-024 overrides every statement in `docs/handoff-v0.5/` that calls the four-market/on-chain target binding.

## Read first, in this order

1. [docs/notes/codex-context-2026-10-07.md](docs/notes/codex-context-2026-10-07.md): where the project stands, what is decided and open, what to do next. Start here.
2. `docs/handoff-v0.5/AGENTS.md`: the shared integrity, auth, design and completion-report rules. They still apply except where DEC-024 differs. Do not edit anything under `docs/handoff-v0.5/` (frozen; its `MANIFEST.json` hashes verify it).
3. `research/spikes/2026-10-06-tefas/REPORT.md`: what TEFAS and KAP actually return. Read it before touching a data adapter or a detector.
4. `docs/handoff-v0.5/docs/12_Anomaly_Catalog.md`: detector definitions. Use thresholds as written.

Your first reply should verify the repo state (run the tests listed below) and propose **one** vertical slice with requirement IDs, a file-change plan and acceptance tests. Implement only after the owner approves.

## Rules that are easy to break

- **No real TEFAS or KAP values in git.** Their data rights are not reviewed. Raw data lives in gitignored `raw/` folders and in `~/.local/share/project-50k/`. Tests use synthetic values only. Before committing, check staged files for real values.
- **Missing stays missing.** TEFAS writes `0` for "no price": treat it as `None`. Never fill gaps with zeros or invent dated history. Fund NAV is daily, published-cadence data; no intraday candles.
- **Point in time.** Use a value only from the moment it was published: a TEFAS row dated D from about 11:05 on D, a KAP report from its publish time. Add a look-ahead test to any detector or replay code.
- **Do not tune detectors on the funds you evaluate them on.** The owner's development/test split is still undecided. Until it is, **do not compute detector output, thresholds or any other statistic on the 1,922 downloaded price files outside `research/events/2026-09-17-spk-liquidations/top100_funds.txt`.** Read section 7 of the context file.
- **Do not edit the pre-registered detectors** (`research/events/2026-09-17-spk-liquidations/price_detectors/detectors.py`, `PREREGISTRATION.md`). Write a v2 beside them.
- **Naming.** Committed files name only the eight liquidated top-100 funds. Never name other funds as flagged or suspicious. An anomaly is not fraud, and SPK's reasons for its order are not in our files.
- **Pacing.** TEFAS: 1.5 s between requests. KAP: 6 s (a 1.5 s pace got us cut off after about 180 requests).
- **No external actions without the owner's say-so:** spending, creating accounts (Google OAuth, Supabase, LLM keys, email, hosting), deploying, installing the systemd timer in `ops/systemd/`, contacting third parties. The TRY 5,000 ceiling is not authorization to spend.
- The untracked `docs/notes/2026-10-06-market-research-brief.md` belongs to no change. Leave it alone.

## Commands

Python 3.13 (`~/miniforge3/bin/python3`). From the repo root:

```sh
PYTHONPATH=services python -m unittest discover -s tests -t . -v                              # 81 unit tests, standard library only
(cd research/events/2026-09-17-spk-liquidations/price_detectors && python -m unittest test_detectors -v)   # 9 detector tests, needs numpy
(cd docs/handoff-v0.5 && python -m unittest discover -s tests -v)                           # 88 offline reference tests
```

## Layout

| Path | Content |
|---|---|
| `services/p50k/` | Backend package: `providers/` (TEFAS client, KAP report reader, retry and circuit breaker, disk cache), `jobs/` (fund snapshots, price history), `series.py` |
| `tests/unit/` | Unit tests for `services/p50k/` |
| `research/spikes/` | Provider spikes with the field-by-field data report |
| `research/events/2026-09-17-spk-liquidations/` | The SPK liquidation case study: notes, fund lists, pre-registered price detectors and results |
| `docs/decisions/`, `docs/notes/` | Owner decisions and working notes. Record new decisions here |
| `ops/systemd/` | Daily snapshot timer files (not installed) |
| `docs/handoff-v0.5/` | Frozen v0.5 handoff: requirements, anomaly catalog, contracts, reference harness |

## Working style

- Code, commit messages, docs and prompts in English. Replies to the owner in simple, short Turkish.
- Small vertical slices with tests. Before editing, list ambiguities that could cause an irreversible or unsafe choice.
- Match the surrounding code: `from __future__ import annotations`, type hints, `Decimal` for prices, `None` for unknown, atomic file writes, `unittest` (not pytest).
- End every task with the handoff's completion report: requirement IDs, changed files, the exact tests run and their output, what is untested, the data mode, limitations, and the next recommended task. Never report a test as passed that you did not run.
- `gh pr edit` fails here with a "Projects (classic)" error. Edit PR descriptions with `gh api -X PATCH repos/Safa675/project-50k/pulls/N -F body=@file`.
