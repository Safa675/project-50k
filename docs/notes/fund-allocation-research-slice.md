# B2: comparable monthly-average fund allocation changes

The owner approved AN-FND-004 / FR-035 implementation on 2026-10-08.
Scope is DEC-024, existing selected top-100 Turkish funds and local KAP PDFs.
No new network collection, external publication or service-account work.

## Resulting behavior and requirement boundary

**FR-035 (partial):** extract the semantic monthly-average asset-type percentage
table from supported KAP PDF text geometry. Keep native category labels, printed
Decimal percentages and source page/rectangle references. The section letter may
vary. No complete category aliases or signed-exposure model is invented.

**FR-037 / AN-FND-004 (partial):** calculate the composition distance
`D = 0.5 * sum(abs(current_fraction - previous_fraction))`, preserve signed
category deltas and apply the fixed catalog rule `D >= 0.20` or any category
changing by at least 20 percentage points. This is not relative percentage change,
actual portfolio turnover, a cash-flow estimate or fraud detection accuracy.

**NFR-038 (partial):** the service evaluator uses an immutable ReplayCursor and
admits only dated, source-compatible, complete and rights-eligible observations.
Missing/future evidence, incompatible bases/categories or unknown admission
metadata returns ABSTAINED without metrics or future evidence IDs. Monthly-average
composition remains distinct from month-end holdings. No AN-FND-002 historical
baseline policy is imported into this different catalog rule.

Current real archive timing/rights remain unverified. The research runner is
separate exploratory arithmetic; every real production status remains ABSTAINED.
No public FR-064 event, API, deployed UI or external alert is created. Frozen
handoff requirement statuses and the existing price/flow algorithms are unchanged.

## Choices fixed before outcomes

The protocol was locally committed before allocation results in commit `7e0c558`:
`research/events/2026-09-17-spk-liquidations/fund_allocations/PROTOCOL.md`, SHA-256
`ac2f07b63373cc485719c1cd713072b598f96da55754dbe35b6a9e68a75149cd`.

Use consecutive monthly closing periods October 2025–September 2026, with
September 2025 as an opening endpoint only. All 12 scheduled pairs are attempted
for every selected fund, including explicit missing-source/month attempts. Weekly
metadata, duplicate monthly disclosures and ambiguous attachments are excluded.
Latest scheduled, latest reported and latest valid earlier pairs are different.

The first version requires nonnegative printed percentages summing **exactly to
100** and identical native category sets. Do not renormalize rounded totals, drop
negative positions, impute zero for a missing sparse category, merge unverified
synonyms or manufacture an Other residual. This deliberately limits coverage.
Only the comparable monthly-average table is used; month-end holdings, turnover
columns and investor-information-form charts cannot supply interchangeable input.

The raw schema audit used four selected layouts. Some print explicit zero
categories; others use sparse tables and different precision. Spatial table
boundaries matter because neighboring turnover tables repeat category names.
All tracked parser/test examples are authored synthetic data, not original PDFs
or percentages. Parser corrections address extraction defects and preserve the
fixed calculation/window/threshold; code/source fingerprints identify each run.

## Files and migration effects

- `services/p50k/providers/kap_allocation.py`: pure text-geometry parser.
- `services/p50k/detectors/fund_allocation.py`: exact Decimal calculation and
  provenance-bound service evaluator.
- `research/events/2026-09-17-spk-liquidations/fund_allocations/PROTOCOL.md` and
  `run.py`: pre-registered, selected-source, immutable private archive screen.
- Three `tests/unit/test_*allocation*.py` modules: synthetic parser, arithmetic,
  replay and runner acceptance tests.
- This completion note. A private result-review artifact may live outside Git.

No database/schema migration or raw-input rewrite. Service imports/tests remain
standard-library-only; the runner lazily uses the already installed PyMuPDF for
original PDF text geometry. Source receipts/hashes, identity and reported month
are retained separately from unverified historical first availability.

## Verification and local run

Executed on the implemented code, all with exit code 0. The repository suite was
rerun after the geometry-reuse fix in `5994ea9`; the price/reference code did not
change:

1. Repository root:
   `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services /home/safa/miniforge3/bin/python3 -m unittest discover -s tests -t . -v`
   — final run: `Ran 295 tests in 3.321s`, `OK`. The earlier implementation run
   also passed (`Ran 294 tests in 3.458s`).
2. `research/events/2026-09-17-spk-liquidations/price_detectors`:
   `PYTHONDONTWRITEBYTECODE=1 /home/safa/miniforge3/bin/python3 -m unittest test_detectors -v`
   — `Ran 9 tests in 0.391s`, `OK`.
3. `docs/handoff-v0.5`:
   `PYTHONDONTWRITEBYTECODE=1 /home/safa/miniforge3/bin/python3 -m unittest discover -s tests -v`
   — `Ran 88 tests in 0.011s`, `OK`.

Total across the three final suite results: **392 passed tests**, including 99
new allocation tests (33 detector, 28 parser, 38 runner). Acceptance coverage
includes exact threshold equality,
Decimal-context independence, nonunit totals, explicit zeros versus absent
categories, negative/nonfinite inputs, wrapped headers, neighboring turnover
columns, source identity/month checks, duplicate revisions, missing scheduled
pairs, future evidence/revisions, rights and incompatible-source abstention,
registration enforcement and output/source alias rejection. Independently
executed infinitesimal-nonunit and dedented-missing-category probes also rejected
the invalid inputs.

Executed from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services /home/safa/miniforge3/bin/python3 research/events/2026-09-17-spk-liquidations/fund_allocations/run.py --protocol-sha256 ac2f07b63373cc485719c1cd713072b598f96da55754dbe35b6a9e68a75149cd
```

The initial, now superseded, private run fingerprint is
`33359b52cc0aeb4732890c5a33a915e8d0a12f4f1d5258bafba07b8d4a87521f`;
result path is
`raw/kap/allocation-analysis/33359b52cc0aeb4732890c5a33a915e8d0a12f4f1d5258bafba07b8d4a87521f/results.json`.
The result is 15,612,139 bytes, SHA-256
`cad617d47933c2ebfdefaa3d6dd443f873884618961d83d530789fbbc415aad8`.
Input/code identity includes the original PDF and list hashes, committed runtime
manifest, allowlist, protocol and parser versions. Source-row values and other
fund codes remain in ignored private outputs.

Actual initial run coverage:

- 100 selected funds, 99 present report-list sources and one missing source.
- 1,226 monthly source PDFs inspected; 505 reports supplied valid distributions
  across 58 funds. Weekly reports were excluded (81); four duplicate months
  remained ambiguous. No attachment set was ambiguously selectable.
- 1,200 scheduled comparisons; **351 calculable pairs across 53 funds**. The
  remaining 849 comparisons have explicit unknown/invalid reasons.
- Historical crossings: four pairs in three of the 53 calculable funds.
- Fixed latest scheduled September 2026: 11 calculable funds, zero crossings.
- Each fund's latest reported month: 38 calculable funds, one crossing; this
  mixes dated earlier endpoints and is not a current September result.
- The eight previously selected targets: 47 calculable pairs across six funds,
  zero historical crossings. DFI and KHA have no calculable pairs. All eight
  lack a calculable latest scheduled September comparison.
- Every real production status remains **ABSTAINED**. No fraud hit rate or
  false-positive rate can be inferred from these counts.

Rejections can overlap: 578 PDFs failed the exact full-title identity check,
150 lacked a supported printed report period, 162 had nonunit percentage totals,
84 lacked a supported monthly-average section and 20 exceeded the text-cell
bound. Sparse category-set mismatches affected 377 attempted pairs. These are
coverage limitations, not evidence that excluded funds are normal.

Post-run SHA-256 checks found **zero changes in 1,809 snapshotted files**, covering
selected raw report/series sources, fallback lists, the prior flow result and the
unrelated research brief. The frozen handoff manifest also verified all 216
entries unchanged. No network collection or raw rewrite occurred.

Independent validation used a Fraction-based checker without importing the
detector/parser/runner. It passed 29,892 checks: all 351 calculable pairs, signed
deltas, thresholds, 100 summaries, complete cohort counts and all three rankings.
It also verified all 99 report-list files and 1,226 original PDFs (581,906,471
bytes), metadata record hashes, protocol and runtime fingerprints. This checker
verifies source bytes and embedded arithmetic, not full PDF extraction.

A separate PDF audit visually checked page 1 and enlarged allocation tables in
nine PDFs, independently re-extracted 178 printed category/value rows, and
reconciled five selected pairs (the four crossings plus THF July–August) using
Fraction arithmetic. Every source row, category delta and threshold decision
matched. This is a sample extraction audit, not an audit of all rejected PDFs.

The source rejection review found literal title abbreviations/renames,
unsupported abbreviated month headings and signed/leverage tables. Some large
reports exceed the whole-document text-cell bound although page 1 is readable.
The sampled DFI tables remain blocked by name or signed-weight constraints even
when page 1 is isolated. These limitations require a reviewed identity/signed
exposure contract; none was invented to increase observed coverage.

The first identical full rerun exited 2: `refusing to overwrite output with a
different schema or source fingerprint`. Root cause was JSON re-reading PDF
floating coordinates as Decimal, then converting them to strings during
comparison. Financial values were already exact strings. A new synthetic
fractional-coordinate repeat test reproduced that failure (exit 1), and the
minimal normal-JSON-number round-trip fix passed the final 295-test suite.
No formula, threshold, window, gate or source input changed. The original run
remains immutable and superseded by the corrected runtime fingerprint below.

Corrected runtime `5994ea9` produced fingerprint
`eec800c1c8115604eb0425187251fdc22d12359662c0c7c3c0593eb6bad8b6c4`:
`raw/kap/allocation-analysis/eec800c1c8115604eb0425187251fdc22d12359662c0c7c3c0593eb6bad8b6c4/results.json`,
15,612,139 bytes, SHA-256
`9836c1f28c49f83cbef844d12590d8e346b6d05aaa02bdaf778f625ecfe2faed`.
Only registration/runtime hash, fingerprint and run metadata differ from the
initial result. All source rows, fund results, reasons, counts and rankings are
identical. The independent checker was rerun against this corrected output and
current runtime manifest: again 29,892 checks passed with zero failures.

The private review artifact is outside Git:
`/home/safa/.cursor/projects/home-safa-context-pack/canvases/fund-allocation-review.canvas.tsx`.
It embeds the corrected result, separates fixed September, latest reported and
historical peak views, and retains all 100 funds including unknown results.
Source PDF links, hashes and row/page coordinates remain available locally.

Executed artifact checks, both exit 0:

- `/home/safa/.local/bin/node /tmp/p50k-allocation-canvas-typecheck.cjs`:
  TypeScript 5.9.3, actual SDK declarations plus minimal React declarations,
  zero diagnostics.
- `/home/safa/.local/bin/node /tmp/p50k-allocation-canvas-smoke.cjs`:
  100 funds, 1,200 pairs, 2,212 endpoint references and 1,226 PDF sources
  reconciled; 300 SDK-stub views and 261 charts checked. No empty tables/charts;
  noncomputable funds have no weight charts. The original result was unchanged.

These are SDK type and stub-render checks, not actual host visual verification.
Opening the artifact returned queued; no host rendering success is claimed.

The exact full research command was run again on corrected runtime `5994ea9`:
exit 0. Its stdout payload, result bytes/SHA-256 and original `run_at_utc` metadata
were unchanged. Both the superseded initial result and corrected result remain
immutable. Final checks again found zero changes in the 1,809 snapshotted source
files and all 216 frozen manifest entries.

Private verification evidence is saved outside the immutable run directory at
`raw/kap/allocation-analysis/verification-eec800c1c8115604eb0425187251fdc22d12359662c0c7c3c0593eb6bad8b6c4.json`.
Implementation, registration, reuse fix and this note are local commits on
`codex/fund-allocation-shift`; no push, PR, external upload or deployment was
performed for this slice. The unrelated market research brief was left intact.

## Limitations and next task

Data mode is EXPLORATORY_ARCHIVE / HISTORICAL_REPLAY, rights UNKNOWN; authored
fixtures are SYNTHETIC. Missing/unsupported/rounded tables are not normal funds.
Current categories and today's selected universe do not establish historical
membership. A pre-order nominal reporting period does not establish a warning
made or available before the SPK order. Non-target funds are not known-clean
controls, and liquidation-list membership is not a fraud label.

Source admission, a full official revision archive, parsed security holdings,
licensed liquidity measures, detector calibration, current fund status, product
event assembly and host UI rendering remain separate work. Next, inspect the
largest valid composition changes against the source PDFs and explain them with
dated disclosures; do not tune this threshold to fit observed targets.
