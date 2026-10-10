# Project 50K

Investment intelligence for Turkish retail investors. When something notable happens to a fund you follow, see why it might matter, with its sources. No buy/sell advice and no claim to predict markets.

**Current phase: Turkish investment funds only** ([DEC-024](docs/decisions/DEC-024-turkish-funds-first.md)). BIST, crypto, US equities and on-chain are postponed, not dropped.

"Project 50K" is the working codename. İzvanta is a naming proposal only.

## Status

The repository includes immutable top-100 archive bundles, a private read-only
research API and a Turkish app for the selected 100 funds. The owner approved
the list/detail design on 2026-10-08. The app requires the owner's local
raw archive. The frozen registry's
284 requirement statuses remain `NOT_IMPLEMENTED`; this prototype provides
partial research coverage rather than production acceptance. No fraud accuracy,
historical alert validity or customer validation has been established.

## Local fund-research app

The first view is fixed at `2026-09-16T23:59:59+03:00` (Europe/Istanbul).
The app keeps all 100 selected funds, separates D1 peer-return context from the
July-to-August estimated-flow screen, and displays missing/stale evidence.
This is `HISTORICAL_REPLAY` / `EXPLORATORY_ARCHIVE` research with unknown rights
and historical source-version availability. Production decisions stay
`ABSTAINED`. It does not enable arbitrary dates or a public event/auth contract.
An optional dated view ([DEC-026](docs/decisions/DEC-026-dated-d1-research-view.md))
shows the D1 screen alone at 12 preregistered dates from its own sealed index
and loopback API; see [ops/local/README.md](ops/local/README.md).

Install the locked dependencies explicitly, from the repository root:

```sh
uv sync --locked --extra api --extra api-test --extra research --python /home/safa/miniforge3/bin/python3
npm ci --prefix frontend
```

The frontend install prepares locally served PDF.js assets from the pinned
package. The launcher checks their presence; the viewer needs no CDN connection.

A fresh Git clone has no private data. The inputs are the selected codes in
`research/events/2026-09-17-spk-liquidations/top100_funds.txt`, their
`raw/tefas/prices/` and `raw/kap/series/` files, original selected KAP report
lists/PDFs under `raw/kap/reports/`, and the existing
`~/.local/share/project-50k/fund_snapshots.sqlite3`. Missing fund inputs remain
visible; no current downloads replace the archived versions. The 1,922 unopened
fund price files are excluded. Bilun's source and health data are not runtime
dependencies.

Create the private sealed bundle explicitly after the protocol and calculation
source are committed. The command verifies committed source hashes, never
downloads, and prints its exact ignored output directory:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/bin/python research/events/2026-09-17-spk-liquidations/fund_review_app/run.py
```

Start the exact bundle printed by that command; replace `<fingerprint>` below:

```sh
.venv/bin/python ops/local/run_app.py --bundle raw/research/fund-review-app/<fingerprint>
```

Open `http://127.0.0.1:3060`. The separate API listens on
`http://127.0.0.1:8767/research/v1/health`. Both processes bind to loopback;
Ctrl+C stops the processes started by the launcher. Startup performs no data
collection, detector calibration, dependency installation or database migration.
The main route shows the actual sealed bundle. Search and category/finding
filters persist when opening a fund and returning to the list. Fund detail
shows separate calculations, a common-baseline chart with explicit gaps,
recorded publication dates and original manifest-backed PDFs.
The separate `/preview` route uses explicitly labelled synthetic design data.

See [local launcher options](ops/local/README.md), the
[bounded protocol](research/events/2026-09-17-spk-liquidations/fund_review_app/PROTOCOL.md),
the [app plan](plans/2026-10-08-top100-fund-research-app.md) and
[executed verification](docs/notes/top100-fund-app-completion.md).

## Layout

| Path | Content |
|---|---|
| `docs/decisions/` | Owner decisions made after the handoff, starting with DEC-024 |
| `docs/notes/` | Working notes, such as what to reuse from bist-quant |
| `docs/handoff-v0.5/` | The v0.5 research handoff, unchanged: requirements, anomaly catalog, contracts, research, reports and an offline reference harness |
| `research/spikes/` | Provider spikes with live samples, starting with [TEFAS / borsapy](research/spikes/2026-10-06-tefas/REPORT.md) |
| `services/p50k/` | Backend package: TEFAS client, KAP report and holdings readers, retry and circuit breaker, snapshot and price-history jobs, evidence store, sealed research bundles and the read-only APIs |
| `frontend/` | Next.js app in Turkish: the fixed-date view, `/dates` and synthetic `/preview` scaffolds |
| `research/events/` | The SPK liquidation case study, preregistered detectors and the protocols and runners of the sealed views |
| `tests/unit/` | Unit tests for `services/p50k/`, the runners and the launchers |
| `ops/local/` | Loopback launchers for the local apps |
| `ops/systemd/`, `ops/windows/` | Daily fund snapshot schedule for Linux (not installed by default) and Windows |
| `.claude/` | Claude Code skills, hooks and path rules ([agent tooling](docs/notes/agent-tooling.md)) |

The handoff is kept as a frozen snapshot so its `MANIFEST.json` hashes keep verifying. Record changes as new files in `docs/decisions/` or `docs/notes/` instead of editing it.

## Start here

1. [Current state](docs/notes/current-state.md): what exists, what is decided and open, what comes next
2. [DEC-024: Turkish funds first](docs/decisions/DEC-024-turkish-funds-first.md) and the later records in [docs/decisions/](docs/decisions/)
3. [Handoff START_HERE](docs/handoff-v0.5/START_HERE.md)
4. [Anomaly catalog](docs/handoff-v0.5/docs/12_Anomaly_Catalog.md)
5. [Release gates](docs/handoff-v0.5/docs/25_Release_Gates_and_Open_Decisions.md)
6. [bist-quant reuse notes](docs/notes/bist-quant-reuse.md)

## Local checks

Core service checks keep standard-library imports. Research regression checks
need the pinned NumPy and PyMuPDF extra; API checks require the locked API/test extras. Missing optional
dependencies are explicit skips, not successful API/D1 verification. With all
extras installed, from the repo root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/bin/python -m unittest discover -s tests -t . -v
```

On Windows use `.venv/Scripts/python.exe`. The suite there has known platform
failures; [/p50k-verify](.claude/skills/p50k-verify/SKILL.md) lists them and a
diagnostic variant. `.gitattributes` keeps every checkout on LF line endings,
which the sealed bundles and the handoff manifest require.

The handoff's offline reference tests:

```sh
cd docs/handoff-v0.5
python -m unittest discover -s tests -v
```

Frontend checks, from `frontend/`:

```sh
npm run typecheck
npm test
NEXT_TELEMETRY_DISABLED=1 npm run build
npm run test:browser
```

Browser tests use authored synthetic responses; actual private-bundle verification
is recorded separately and is not a detector performance measurement.

## Daily fund snapshots

TEFAS serves only today's fund size, units outstanding and investor count, so their history is built by saving them every business day. A missed day can't be fetched later.

```sh
PYTHONPATH=services python -m p50k.jobs.fund_snapshots --tefas-only
```

It takes one to several hours for the 1,071 funds traded on TEFAS, depending on TEFAS response times, and stores rows in `~/.local/share/project-50k/fund_snapshots.sqlite3`, outside git. To run it every weekday evening, see [ops/systemd](ops/systemd/README.md) (Linux) or [ops/windows](ops/windows/README.md). Sealed fixed-date bundles re-read the default database, so on a machine that holds them collect into a separate file with `--db` (see the warning in [ops/systemd](ops/systemd/README.md)). The team's Windows machine collects into `fund_snapshots_forward.sqlite3`, which no sealed bundle reads ([DEC-027](docs/decisions/DEC-027-event-weekend-operations.md)).
