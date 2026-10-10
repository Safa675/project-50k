# Dated D1 view: completion and verification

Recorded 2026-10-10 (Europe/Istanbul) on the team's Windows 11 machine, in an LF clone
(`core.autocrlf=false`), with Python 3.14.3 and the locked extras from `uv.lock`, Node 24.14.1 and Chrome 155.
Slice: [DEC-026](../decisions/DEC-026-dated-d1-research-view.md) and
`research/events/2026-09-17-spk-liquidations/fund_review_dated/PROTOCOL.md`.
Operating decisions: [DEC-027](../decisions/DEC-027-event-weekend-operations.md).

## Delivered

- The protocol was committed alone in `d8e445b`, before any dated runtime (`1ec1123`) or real output.
- The frozen D1 screen at 12 preregistered dates is served from sealed per-date bundles behind a sealed date
  index. It runs on a separate loopback API (`/research-dated/v1`, port 8768) and new `/dates` pages.
- Estimated flow and concentration are not calculated in the dated view. The fixed-date app and every file bound
  into its sealed bundles are byte-identical.
- Design readings and the layout reviews are in [fund-review-dated-design.md](fund-review-dated-design.md).

Partial requirement contributions:

- **Core:** NFR-038.
- **Partial, with limits:** FR-109 (recorded-date filter only), FR-108 (immutable and provenance-dated; not
  rights-cleared), NFR-015 (new route parameters only).
- **Also contributed to:** DR-007, FR-018, FR-019, FR-032, FR-036, FR-037, FR-073, FR-078, FR-111, NFR-023,
  NFR-024, NFR-035, NFR-037, NFR-052, NFR-067, NFR-068, UR-027 and UR-035.
- **Not claimed:** FR-110, UR-078/079/080, NFR-080, NFR-005 and NFR-078.

All 284 requirement statuses stay NOT_IMPLEMENTED. G01, G03, G09 and G10 stay open.

## Sealing (private outputs, not in git)

Inputs were copied byte for byte from this machine's archive and hash-verified:

- the 100 opened price files;
- the snapshot database (names and categories);
- the `bundle.json` of the v1 base bundle `40c049033226…`.

That v1 bundle was first verified in place, with ports chosen to avoid the running demo:

```sh
.venv\Scripts\python.exe ops/local/run_app.py --bundle <archive>/raw/research/fund-review-app/40c049033226… --api-port 8797 --frontend-port 3097 --check
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv\Scripts\python.exe research/events/2026-09-17-spk-liquidations/fund_review_dated/run.py \
    --v1-bundle raw/research/fund-review-app/40c049033226… --snapshot-db raw/snapshots/fund_snapshots.sqlite3
.venv\Scripts\python.exe ops/local/run_dated_app.py --index raw/research/fund-review-dated/index/6623c78d… --check
```

Results:

- The `--check` exited 0.
- The runner took 31 s. Its v1-equivalence audit returned `D1_AND_CHART_EQUAL` for all 100 funds at 2026-09-16.
- Grid:
  - 2025-10-31, 2025-11-28, 2025-12-31;
  - 2026-01-30, 2026-02-27, 2026-03-31, 2026-04-30;
  - 2026-05-26 (holidays in the archive calendar);
  - 2026-06-30, 2026-07-31, 2026-08-31;
  - 2026-09-16.
- Index `6623c78d0bcce753086eae2b73c18bd91fa8b0240284100dece80935d7b50b14`.
- The dated `--check` exited 0. It verified the index, all 12 bundles, the response contract for every date, and
  the protocol commit's ancestry and digest.

Per-date coverage over the 100 records. These are descriptive counts of development data, with the same stored
thresholds at every date; they are not detection performance or lead times:

| Date | Eligible crossing | Eligible no crossing | Stale | Unavailable | No price yet |
|---|---|---|---|---|---|
| 2025-10-31 to 2026-02-27 | 2 | 68 | 0 | 30 | 1 |
| 2026-03-31 to 2026-05-26 | 3 | 67 | 0 | 30 | 0 |
| 2026-06-30, 2026-07-31 | 4 | 67 | 0 | 29 | 0 |
| 2026-08-31 | 3 | 68 | 0 | 29 | 0 |
| 2026-09-16 | 3 | 67 | 1 | 29 | 0 |

At 2026-09-16 these equal the fixed view's figures: 70 fresh assessable, 1 stale, 29 unavailable.

## Verification actually run

Python, from the repository root:

- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/Scripts/python.exe -m unittest discover -s tests -t . -v`
  ran 605 tests: `FAILED (failures=43, errors=33, skipped=1)`. These are exactly the Windows platform failures of
  the pre-slice baseline at `8d6b199` (526 tests, same counts); no dated test fails.
- The Windows diagnostic variant (tzdata on PYTHONPATH, git `core.autocrlf=false` for test subprocesses,
  `PYTHONUTF8=1`) ran 663 tests: `failures=1, errors=2, skipped=1`. These are the three pre-existing Windows
  residuals: the v1 launcher's `SO_REUSEADDR` test and two evidence-store SQLite file-lock errors.
- Frozen price detectors: 9 OK. Frozen handoff: 88 OK.

Frontend, from `frontend/`:

- `npm run typecheck` exited 0; `npm test` passed 118 tests in 14 files; `npm run build` exited 0.
- Playwright passed 65 tests (31 existing and 34 new) against a production server on 127.0.0.1:3061, with the
  browser origin mapped from 3060 because a demo held that port.

Review and pre-commit checks:

- Four independent reviewers raised 2 major and 7 minor findings. All were fixed with tests that fail when the
  fix is reverted.
- A live contract round trip validated 161 real Python API responses with the frontend schemas and loaders,
  with 0 failures. A golden parity test now guards that boundary.
- Pre-commit checks:
  - The leak scan of 47 changed files against 61,611 real price values, 100 real fund names and 92 non-target
    codes found 0 hits.
  - No new file has CRLF line endings.
  - The registered v1/v2 sources and the frozen files are unchanged.
  - Tracked-file edits are append-only.

Runtime checks:

- The local demo runs from this clone: the fixed-date API on 8767 (bundle `086d934a…`), the dated API on 8768
  and the production frontend on 3060.
- `/` and `/dates` return 200 with `no-store`. The proxied index returns 12 entries; an off-grid date returns
  404 and a pre-range date returns 400.

## Not tested, limits

- The suites were not run on Linux here. Other machines must seal their own dated bundles, because bundles are
  tied to the absolute paths they were sealed with.
- The data is recorded-date reconstruction with unknown historical availability, unknown rights, a post-event
  universe and categories, and a post-order snapshot. KAP revisions (TC-TIME-002) are not handled.
- There is no measured evaluation; the per-date counts are not performance figures.
- Pre-existing Windows test failures remain (separate hygiene work).

Data mode: `HISTORICAL_REPLAY` / `EXPLORATORY_ARCHIVE`, knowledge basis
`RECORDED_SOURCE_DATE_RECONSTRUCTION`, D1 only. Real data is shown only in the private local demo (DEC-027).

Migration effects: none. New private outputs are under `raw/research/fund-review-dated/`.

Next recommended slice: per-date estimated flow, under a new versioned protocol that uses the (M-2, M-1) rule
pre-recorded in DEC-026.
