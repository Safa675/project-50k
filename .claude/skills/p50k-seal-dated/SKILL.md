---
name: p50k-seal-dated
description: Seal (or reseal) the dated D1 view's 12 per-date bundles and date index from the private archive, verify them and wire them into the demo. Use on a machine that holds the private data when the dated view must be shown there, or after an intended change to registered dated code.
---

# Seal the dated D1 view

Rules: `research/events/2026-09-17-spk-liquidations/fund_review_dated/PROTOCOL.md` (DEC-026). The protocol is
frozen once a real index is sealed; a rule change needs a new versioned protocol, not an edit.

## Preconditions

- An LF checkout (the runner refuses CRLF and names the file; `.gitattributes` makes new checkouts LF, and
  `docs/notes/agent-tooling.md` shows how to convert an older CRLF checkout) with a clean
  working tree at a commit that contains the protocol and dated runtime. `git status` must be empty for every
  registered file, because the runner compares working bytes with `git show HEAD:`.
- Private inputs at the canonical paths (never in git):
  - `raw/tefas/prices/<CODE>.json` for the 100 codes in `research/events/2026-09-17-spk-liquidations/top100_funds.txt`
    (the other downloaded price files are never read);
  - a snapshot database with rows retrieved at or before `2026-10-07T08:52:12.470547+00:00`
    (for example `raw/snapshots/fund_snapshots.sqlite3`);
  - the sealed v1 base bundle `raw/research/fund-review-app/<v1-base>/bundle.json` (the bundle without the
    concentration extension). The runner reads only that file, in phase 2.
- Locked Python environment (`uv sync --locked --extra api --extra api-test --extra research`).

## Steps (repository root; Windows: `.venv\Scripts\python.exe`)

1. Verify the v1 base bundle where it was sealed, on spare ports so a running demo is not disturbed:
   `.venv/bin/python ops/local/run_app.py --bundle <path to v1-base> --api-port 8797 --frontend-port 3097 --check`
2. Seal:
   `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/bin/python research/events/2026-09-17-spk-liquidations/fund_review_dated/run.py --v1-bundle raw/research/fund-review-app/<v1-base> --snapshot-db <snapshot.sqlite3>`
   It prints JSON with `audit`, `grid`, `index_id` and `index_directory`. Expect `"audit": "D1_AND_CHART_EQUAL"`
   and 12 grid dates ending at 2026-09-16. An identical rerun reuses the same bytes.
3. Check: `.venv/bin/python ops/local/run_dated_app.py --index <index_directory> --check` (exit 0).
4. Start or restart the demo with `/p50k-demo`, passing the printed index directory.

## When it refuses

- `differs from committed HEAD` / CRLF: commit or revert the named file; never edit registered files to pass.
- `differing fields: ...`: the dated 2026-09-16 result differs from the v1 bundle (field names only). Do not
  seal; find out whether inputs, categories or code changed since the v1 seal.
- `protocol guard`: an index sealed under a different protocol exists; a new protocol needs a new version.
- Snapshot or target-category refusals: the snapshot database does not match the calibration-time categories.

Never commit anything under `raw/`. Record a new seal (date, index ID, audit status, exact commands) in a
completion note without real values or non-target fund names.
