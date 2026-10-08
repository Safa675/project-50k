# Local raw data layout

Approved by the owner in chat on 2026-10-08. This maintenance change centralizes
the existing local data files under the repository-root `raw/` directory. Code and
documentation may be committed and pushed; raw data and local aliases remain
gitignored and are not uploaded.

## Requirement linkage

- **FR-018 / FR-019:** preserve the original source bytes, timestamps and provenance
  while changing their filesystem location.
- **FR-032:** keep the existing daily-price inputs reachable at the new canonical
  path, without changing values or missing-price handling.
- **NFR-038:** retain the replay cutoff boundary and existing regression checks.

This is maintenance only. It adds no detector, establishes no historical
availability or performance, and upgrades no requirement or frozen registry status.

## Committed changes

- `.gitignore`: ignore the canonical root `raw/` and retain legacy exclusions.
- `research/spikes/2026-10-06-tefas/`: change paths in `spike.py`,
  `kap_pdf_check.py`, `kap_batch.py` and `kap_series.py`; annotate `REPORT.md`.
- `research/events/2026-09-17-spk-liquidations/`: change paths in `extract.py`
  and `price_detectors/run.py`; annotate `NOTES.md`.
- `AGENTS.md`, `docs/notes/codex-context-2026-10-07.md` and
  `docs/notes/evidence-store-replay-slice.md`: document current local paths.
- This note records the layout and executed verification.

## Canonical directories

All paths in this section are relative to the repository root:

```text
raw/
  tefas/
    prices/           Existing per-fund dated price JSON files
    responses/        Original provider-spike responses and mixed requests.json
    logs/             Existing price-download logs
    price-detectors/  Existing detailed research output
  kap/
    reports/          Original fund directories, report lists, pages and PDFs
    series/           Existing parsed per-fund series JSON files
  spk/                Original bulletin PDF
```

The directories and their files are local-only. A fresh clone or a cloud checkout
does not contain them or the legacy symlinks. Scripts may recreate output
directories, but doing so does not recover the historical files. This relocation
is a move on the same machine, not a backup or a data transfer to GitHub.

Acquisition-context files inside the old KAP fund directories, such as saved TEFAS
profiles or price responses used during that acquisition, stay alongside their
reports. Splitting those directories would change their local archive topology.
The provider-spike `requests.json` contains both TEFAS and KAP request metadata;
its filename and bytes remain unchanged in `raw/tefas/responses/`.

## Relocation and compatibility

- `research/events/2026-09-17-spk-liquidations/raw/prices/` moves to
  `raw/tefas/prices/`.
- The event directory's `prices*.log` files move to `raw/tefas/logs/`.
- Its existing `raw/price_detectors/` output moves to `raw/tefas/price-detectors/`.
- Its bulletin PDF moves to `raw/spk/`.
- `research/spikes/2026-10-06-tefas/raw/kap/` moves to `raw/kap/reports/`.
- The spike's standalone `kap_*.body` responses and KAP PDF move to
  `raw/kap/reports/`.
- Its `raw/kap_series/` moves to `raw/kap/series/`.
- Its `fon*.body` responses and mixed `requests.json` move to
  `raw/tefas/responses/`.

Ignored compatibility symlinks at the old relative paths resolve to the same
files. Historical research result JSON, frozen registrations, source path strings
embedded in raw metadata, and existing immutable bundle locators are not rewritten.
New consumers and documented examples use the canonical paths. The aliases remain
necessary for old local records and frozen consumers.

SQLite databases, including `fund_snapshots.sqlite3`, its existing backup and any
evidence database, remain in `~/.local/share/project-50k/`. This task neither moves
nor imports them. A new evidence import may record a different source locator;
that does not mutate an existing sealed bundle.

## Verification boundary

The one-off migration audit is stored outside Git at
`~/.local/share/project-50k/raw-migration-2026-10-08.json`. The before/after inventory
compares file counts, byte sizes and whole-file SHA-256 fingerprints for each
relocated file and checks that every old alias reaches the same bytes. It does not
parse fund values, calculate statistics or run detectors. Hashing an unopened file
does not open the sealed evaluation set for research.

Acceptance checks:

1. Every mapped file exists at its canonical location with unchanged size and hash.
2. Legacy aliases resolve correctly; there is no second physical data copy created
   by the move and no dangling compatibility symlink.
3. `raw/` and old aliases are ignored; no raw file or alias is tracked or staged.
4. Updated consumers resolve canonical paths in synthetic temporary repositories;
   checks do not regenerate local series or existing research outputs.
5. Frozen handoff manifest entries and frozen detector registrations retain their
   bytes. External databases and immutable bundle locators remain unchanged.
6. The three existing offline regression suites pass.

Read-only Git checks from the repository root:

```sh
git ls-files -- raw
git check-ignore raw/tefas/prices/THF.json raw/kap/reports/THF/kap_report_list.json raw/spk/spk-bulten-2026-61.pdf
git diff --check
```

`git ls-files -- raw` must be empty. `git check-ignore` must list each named path;
it checks ignore rules and does not expose file contents.

Executed regression commands, path smoke checks and review results are recorded
below.

## Limitations

There are no downloads, provider probes, real-data imports, new detector outputs,
charts or real-data statistics in this task. The unopened-price restriction and
pending company-level evaluation split remain binding. Data rights are still
unreviewed, and the local data retains its existing origin and availability limits.
This change does not admit unknown KAP versions into replay, install a snapshot
timer, clear release gates or supply the data to a fresh clone.

The next research step can use the already opened top-100 development data within
those boundaries. A path migration is not evidence that an anomaly detector works.

## Actual verification

The local migration audit on 2026-10-08 has status `verified`:

- 3,906 files moved, totaling 719,198,854 bytes.
- 3,906 of 3,906 SHA-256 hashes and modification times match before/after.
- All 3,906 legacy file paths resolve to the same files at the canonical locations.
- Group counts: 2,022 price files, 101 KAP series files, 1,769 KAP report/archive
  files, 10 provider-spike response/metadata files, 2 download logs, 1 detailed
  detector-output file and 1 SPK bulletin. The KAP archive count includes metadata
  and is not a PDF count. The KAP PDF count is 1,342: 1,341 batch-report PDFs and
  the original standalone spike PDF. The SPK archive contains 1 PDF.
- All 216 frozen handoff entries retain their manifest sizes and SHA-256 hashes.
- The two frozen detector registration/code files match `origin/main`.
- Tracked files under the new `raw/` directory: 0.
- All 3,906 canonical file paths and all 24 legacy symlink paths are Git-ignored,
  checked with `git check-ignore --stdin -z`.
- Six updated scripts compile/import with Python 3.13. Temporary synthetic-cache
  smoke checks pass for provider routing, batch cache fallback, report lists,
  history inputs and price reads; they use no real-data calculations or network.

Working directory `/home/safa/Documents/project-50k`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services /home/safa/miniforge3/bin/python3 -m unittest discover -s tests -t . -v
```

Output: `Ran 129 tests in 0.086s`; `OK`; exit 0.

Working directory
`/home/safa/Documents/project-50k/research/events/2026-09-17-spk-liquidations/price_detectors`:

```sh
PYTHONDONTWRITEBYTECODE=1 /home/safa/miniforge3/bin/python3 -m unittest test_detectors -v
```

Output: `Ran 9 tests in 0.353s`; `OK`; exit 0.

Working directory `/home/safa/Documents/project-50k/docs/handoff-v0.5`:

```sh
PYTHONDONTWRITEBYTECODE=1 /home/safa/miniforge3/bin/python3 -m unittest discover -s tests -v
```

Output: `Ran 88 tests in 0.003s`; `OK`; exit 0. Total: 226 passing tests.

The one-off consumer-path smoke script remains outside the repository. From the
repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 /home/safa/miniforge3/bin/python3 /tmp/p50k-raw-paths-smoke-2026-10-08.py
```

Exit 0: six scripts compiled/imported, 24 canonical-path assertions and 10
synthetic cache/reader/writer/locator assertions passed. Network calls and real
raw-data reads were disabled; all writes used temporary files.

Independent review found no significant actionable issue in the code or stable
documentation. Its separate synthetic probes confirmed canonical input paths,
report-list precedence, cache fallbacks and reuse. Its read-only metadata audit
confirmed that all 3,906 legacy paths reach the same inode, size and modification
time, and all 3,930 canonical files and top-level legacy links are ignored. It
also verified no diff in the frozen handoff, detector code or preregistration.
`git diff --check` passed. Live downloads and real-data processing remain untested
for this maintenance change.

The staged content scan checked all 13 changed files against long numeric
literals from 198 opened-universe price/KAP source files: 0 matches. No raw file
or alias was staged; the unrelated untracked research brief was excluded.
