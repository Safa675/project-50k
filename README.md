# Project 50K

Investment intelligence for Turkish retail investors. When something notable happens to a fund you follow, see why it might matter, with its sources. No buy/sell advice and no claim to predict markets.

**Current phase: Turkish investment funds only** ([DEC-024](docs/decisions/DEC-024-turkish-funds-first.md)). BIST, crypto, US equities and on-chain are postponed, not dropped.

"Project 50K" is the working codename. İzvanta is a naming proposal only.

## Status

Planning and research only. There is no application yet, and all 284 requirements are `NOT_IMPLEMENTED`. Thresholds are provisional, detector frequencies are unknown, and no customer validation has been done.

## Layout

| Path | Content |
|---|---|
| `docs/decisions/` | Owner decisions made after the handoff, starting with DEC-024 |
| `docs/notes/` | Working notes, such as what to reuse from bist-quant |
| `docs/handoff-v0.5/` | The v0.5 research handoff, unchanged: requirements, anomaly catalog, contracts, research, reports and an offline reference harness |
| `research/spikes/` | Provider spikes with live samples, starting with [TEFAS / borsapy](research/spikes/2026-10-06-tefas/REPORT.md) |
| `services/p50k/` | Backend package. So far: provider retry and circuit breaker, a JSON disk cache and series math (ported from bist-quant), a TEFAS client and the daily fund snapshot job |
| `tests/unit/` | Unit tests for `services/p50k/` |
| `ops/systemd/` | Timer files for running the daily fund snapshot job (not installed by default) |

The handoff is kept as a frozen snapshot so its `MANIFEST.json` hashes keep verifying. Record changes as new files in `docs/decisions/` or `docs/notes/` instead of editing it.

## Start here

1. [DEC-024: Turkish funds first](docs/decisions/DEC-024-turkish-funds-first.md)
2. [Handoff START_HERE](docs/handoff-v0.5/START_HERE.md)
3. [Anomaly catalog](docs/handoff-v0.5/docs/12_Anomaly_Catalog.md)
4. [Release gates](docs/handoff-v0.5/docs/25_Release_Gates_and_Open_Decisions.md)
5. [bist-quant reuse notes](docs/notes/bist-quant-reuse.md)

## Local checks

Both test suites need only the Python standard library. From the repo root:

```sh
PYTHONPATH=services python -m unittest discover -s tests -t . -v
```

The handoff's offline reference tests:

```sh
cd docs/handoff-v0.5
python -m unittest discover -s tests -v
```

## Daily fund snapshots

TEFAS serves only today's fund size, units outstanding and investor count, so their history is built by saving them every business day. A missed day can't be fetched later.

```sh
PYTHONPATH=services python -m p50k.jobs.fund_snapshots --tefas-only
```

It takes about an hour for the 1,071 funds traded on TEFAS and stores rows in `~/.local/share/project-50k/fund_snapshots.sqlite3`, outside git. To run it every weekday evening, see [ops/systemd](ops/systemd/README.md).
