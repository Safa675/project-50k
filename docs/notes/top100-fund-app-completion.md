# Local top-100 fund app: implementation checkpoint

Date: 2026-10-08. Host: owner's laptop.
Status: protocol, immutable bundle and read-only API implemented and verified;
synthetic UI scaffold reviewed technically. Owner screen review is pending.
The real-data fund list/detail, interactive chart and PDF dialog are unfinished.
This is a checkpoint, not acceptance of the full app plan.

## Authorization and remaining screen review

The owner requested implementation on the laptop because the VPS was unavailable.
That authorizes local work on the [app plan](../../plans/2026-10-08-top100-fund-research-app.md).
No push, merge, public/LAN deployment or systemd installation is included.
The plan's P0 requires concrete design review before full UI implementation.
The running `/preview` presents six explicitly synthetic records and a detail
wireframe. Screenshots were shown to the owner and the screen-review choice was
requested. No response has been recorded. See [screen review](top100-fund-app-design.md).
G09 is still open; no designer or Impeccable approval is claimed.

## Partial requirement coverage

- FR-036 / FR-037: frozen D1 peer-return calculation and signed July-to-August
  endpoint-change research arithmetic. Historical category membership, actual
  investor cash and a validated production flow baseline remain unresolved.
- FR-073 / FR-074 / FR-078: source-linked deterministic Turkish comments and
  chart/evidence payloads; synthetic list/detail hierarchy and validated client
  contracts. Actual-data UI navigation, chart and PDF interaction are pending.
- FR-018 / FR-019 / FR-108 / FR-109 / NFR-038: immutable hashes, selected-source
  references, fixed cutoff and future-invariance tests. Recorded publication
  filtering does not establish verified historical availability or replay
  admission.
- FR-111: separate private archived-research contract and conspicuous synthetic
  preview mode. Competition and external-release gates remain open.

The frozen 284-status requirement registry is unchanged.

## Implemented files

- `research/events/2026-09-17-spk-liquidations/fund_review_app/PROTOCOL.md` and
  `run.py`: protocol committed before real joined calculations; explicit sealed
  bundle generation, no downloads or recalibration.
- `services/p50k/research_reviews/`: contracts, immutable source registry,
  selected-source bundle validation, frozen D1 adapter, conditional Decimal flow
  arithmetic and tested Turkish comments.
- `services/p50k/api/`: strict FastAPI/Pydantic research health, summary, list,
  detail and opaque manifest-backed source routes. JSON/PDF/error responses are
  `no-store`; source paths are private.
- `pyproject.toml`, `uv.lock`, `ops/local/`: locked optional API/test/research
  dependencies and a loopback launcher with explicit bundle selection.
- `frontend/`: locked Next.js/TypeScript/next-intl scaffold, Bilun generic
  primitives and notice, strict runtime response client, synthetic preview and
  tests. Real-data routes currently redirect to the labelled preview.
- Synthetic Python tests for bundle/comment/API contracts; design note,
  repository README and app-plan status.

## Actual archive verification

Final private bundle:
`raw/research/fund-review-app/a13b74d09993616a7c7da6b8b396b6570502cf7f3752683599071b14341cde88/`.
Its financial contents and source copies are ignored and absent from Git.
Registration binds implementation commit `3b8e74e38cf78fbe99dbcd9d9a537d014faa0ee3`
and protocol commit `11f38a4`. Subsequent launcher/documentation changes do not
alter its registered calculation-source bytes.

Exactly 100 selected records remain present. Independent computation reproduced
71 finite D1 statistics, including one stale result, and 83 exact-fraction flow
checks. All 166 retained flow endpoints matched the original selected KAP series.
All 4,260 chart points matched independently calculated common-baseline values
or explicit gaps. No frozen threshold was changed or recalibrated.

Of 100 records, 54 have both eligible calculations, 45 have a partial assessment
and one has neither. Descriptive groups are two findings: 2; one finding: 19;
no eligible finding with incomplete evidence: 42; both calculations eligible
without crossings: 37. These are archive observations, not fraud labels,
accuracy, false-positive rates or a validated crisis-beforehand result.

All 1,907 audited original private files, including the existing SQLite database,
retain their original hashes. The 216 frozen-handoff manifest entries verify;
the frozen price detector/preregistration/calibration files are unchanged.
No unopened price files were consumed. No real values or private screenshots
were staged. The Bilun source checkout was unchanged.

## Executed tests and probes

Python 3.13.13, locked NumPy 2.4.6 and PyMuPDF 1.27.2.3; optional API/test
dependencies installed in the ignored `.venv`.

```sh
# Repository root
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/bin/python -m unittest discover -s tests -t . -v
# Frozen price detector directory
PYTHONDONTWRITEBYTECODE=1 /home/safa/Documents/project-50k/.venv/bin/python -m unittest test_detectors -v
# Frozen handoff directory
PYTHONDONTWRITEBYTECODE=1 /home/safa/Documents/project-50k/.venv/bin/python -m unittest discover -s tests -v
```

After parsing/dependency fixes: root **501 tests, 22.127s, OK**;
price detector **9 tests, 0.457s, OK**; frozen handoff **88 tests, 0.006s, OK**.
No skips. Exact logs are local `/tmp/p50k-app-regression-{root,price,frozen}-fixed.log`.

The final root regression, including two launcher socket integration tests:
**503 tests, 24.724s, OK, no skips**. Exact log:
`/tmp/p50k-app-regression-root-final.log`. The other frozen suites were unchanged
after the launcher-only correction.

The first locked full run failed: 497 tests, one failure and two errors. The
errors were a missing locked PyMuPDF dependency. The failure was invalid Decimal
input parsing altering the caller's context flags. Both new domain/API parsers
now isolate conversion flags; synthetic regressions test precision, traps and
pre-existing flags. Original preregistered futures math/runners were unchanged.

From `frontend/`, actually executed:

```sh
npm run typecheck
npm test
NEXT_TELEMETRY_DISABLED=1 npm run build
npm run test:browser
```

Typecheck and build exited 0; 28 synthetic unit tests and five Chrome browser
tests passed (browser run: 11.3s). Checks include search/filter/detail/back,
no matches, loading/error/missing states, mobile category/metric labels,
keyboard focus and no horizontal overflow. These do not verify a real-data UI.
The 201 build assets contained no private fund names, bundle ID or source hashes.
Seven adapted Bilun primitives and the exact copyright/license notice were
checked against `cafa27bc9d7f6fe4c6a75f1eaea431fed90e2f52`.
The frontend evidence record `/tmp/p50k-frontend-scaffold-verification.txt`
summarizes captured tool outcomes; it is not a full raw command log.

Root manual CUA checks inspected desktop and 390x844 mobile list/detail states;
mobile viewport override was reset. Eight major text/background pairs had
calculated contrast ratios of at least 5.17:1. This is a limited check, not a
complete accessibility or Impeccable audit.

Independent read-only calculation probe:
`/tmp/p50k-review-independent-audit.py`, output
`/tmp/p50k-app-independent-audit-final.json`. Actual HTTP probe:
`/tmp/p50k-app-real-api-probe.py`, output
`/tmp/p50k-app-real-api-probe-final.json`. These local scripts read the selected
private archive only and were not committed.

The final actual HTTP run verified all 100 list/detail records and source
references against the sealed bundle, summary/health identity, `no-store`, an
original PDF byte hash and the frontend's same-origin API proxy. It completed in
22.996s. These are live local API probes, not browser coverage of a real-data UI.
The documented `--check` returned exit 0 and the combined launcher started both
services; `ss` confirmed only `127.0.0.1:3060` and `127.0.0.1:8767` listeners.

A launcher restart check initially mistook a closed connection's `TIME_WAIT`
for an occupied port. Its probe now uses `SO_REUSEADDR`; integration tests
reproduce the original false positive and verify that an active listener is
still rejected without interruption. Generated Next.js `next-env.d.ts` is
ignored because dev/build commands rewrite its type paths; its local generated
file is retained.

## Data mode, limits and next work

Every research response uses `HISTORICAL_REPLAY`, `EXPLORATORY_ARCHIVE`, cutoff
`2026-09-16T23:59:59+03:00`, `RECORDED_SOURCE_DATE_FILTER`, false point-in-time
verification, unknown historical availability/rights, October 2026 universe
selection and current-snapshot categories. Production decisions remain
`ABSTAINED`; strict `ReplayCursor` is unchanged.

Flow uses monthly July/August reports only. Missing/ambiguous publication,
duplicate eligible reports and incompatible known units/actions disable it.
Unknown scope/currency/action history remains explicitly conditional. Quantities
retain report-currency units rather than an invented TRY label. No success rate,
novel detector claim, safety verdict or buy/sell advice is established.

No schema migration, original-data relocation, fresh data collection, public
listener, authentication bypass, credential creation or outbound delivery was
performed. The API/scaffold can run locally after explicit locked setup; a fresh
Git clone lacks the private archive and cannot recreate real results unaided.

Next required step: owner review of the concrete screen. Once approved, complete
P3/P4 real-data list/detail, gapped Lightweight Charts and native manifest-backed
PDF dialog; verify the actual 100-fund browser flow and finish P5. A date selector
still requires a separate selection/freshness protocol.
