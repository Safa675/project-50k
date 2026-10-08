# Local top-100 fund research app: completion and verification

Recorded: 2026-10-09. Final regression runs: 2026-10-08. Host: owner's laptop.
Status: the approved private prototype is implemented locally. The owner approved
the concrete list/detail design with “design is okay go on”. This approval covers
the local layout; formal G09, rights and competition gates remain separate.
No push, merge, public/LAN deployment or systemd installation was performed.

## Delivered scope and requirement coverage

The actual `/` route keeps all 100 selected funds. Search, category/finding
filters, denominator-labelled coverage, Turkish deterministic comments and
missing/stale states are present. Filters and immutable bundle identity persist
through detail and browser back/forward navigation. Rapid edits use supported
native history updates rather than delayed server query replacements.

`/funds/[code]` shows separate D1 and conditional estimated-flow calculations,
exact inputs, metric periods, recorded publication times and source versions.
A Lightweight Charts graph consumes sealed common-baseline indices; separate
segments preserve missing observations. An accessible table retains null gaps.
The chart's peer-price median is explicitly distinct from D1's daily excess-log-
return median. The fund is excluded from its own peer group.

Own-fund prices, monthly data, notification lists and PDFs are primary evidence;
peer prices and calculation versions remain in collapsed groups. Detail requires
exact source-reference membership and own-fund attribution for KAP records.
Missing monthly PDFs remain visible separately. Official disclosure URLs are
validated. PDF bytes must match the manifest hash, bundle, cutoff and provenance
headers before rendering. A native modal contains local PDF.js page rendering,
page controls, zoom, extracted-text fallback and verified original download.
Closing aborts requests, destroys rendering work, revokes blobs and restores focus.
Reopening requires fresh verification. Worker/fonts/decoders come from pinned
installed packages, with no CDN request. `/preview` remains explicitly synthetic.

Partial requirement coverage:

- FR-036 / FR-037: frozen D1 and signed July/August endpoint-change research.
  Historical categories, actual investor cash and production flow admission
  remain unresolved.
- FR-073 / FR-074 / FR-078: source-linked comments, actual list/detail navigation,
  chart context and evidence/PDF inspection.
- FR-018 / FR-019 / FR-108 / FR-109 / NFR-038: fixed cutoff, immutable identity,
  source hashes, strict client/API validation and future-invariance checks.
- FR-111: private archived-research contract and labelled synthetic preview.

The frozen 284-status requirement registry is unchanged. No production acceptance
or fraud accuracy/false-positive measurement is claimed.

## Calculation and source evidence

The protocol was committed before new real joined calculations:
`research/events/2026-09-17-spk-liquidations/fund_review_app/PROTOCOL.md`.
Private bundle:
`raw/research/fund-review-app/a13b74d09993616a7c7da6b8b396b6570502cf7f3752683599071b14341cde88/`.
Registration binds calculation implementation commit
`3b8e74e38cf78fbe99dbcd9d9a537d014faa0ee3` and protocol commit `11f38a4`.
The final UI/launcher implementation is local commit `f244572` (2026-10-09).
Subsequent UI/launcher/documentation changes preserve registered calculation bytes.
The bundle was not regenerated during UI integration.

Independent computation reproduced 71 finite D1 statistics, including one stale
result, 83 exact-fraction flow checks, all 166 retained original KAP endpoints and
all 4,260 normalized chart points/gaps. No threshold was changed or recalibrated.
Of 100 records, 54 have both eligible calculations, 45 have partial assessment
and one has neither. Descriptive groups contain 2 with two crossings, 19 with one,
42 without eligible crossings and incomplete evidence, and 37 with both eligible
calculations without crossings. These aggregates are not fraud labels.

The actual production API was validated by the frontend's TypeScript loaders:
all 100 detail objects equal their list records; summary counts, cutoff, bundle,
exact source sets and monthly source attribution agree. All 102 JSON responses
were no-store. This in-memory audit passed in 29.23s; temporary tests/configuration
were removed and no actual response payload was saved. The earlier independent
HTTP probe also matched an original PDF byte hash through the same-origin proxy.

All 1,907 audited original private files, including SQLite, retain their hashes;
216 frozen-handoff manifest entries verify. Frozen detectors, preregistration and
calibration remain unchanged. No unopened price files were consumed. Real values,
PDFs and private screenshots are absent from Git. Generic Bilun primitives and
notices retain their authorized provenance; Bilun health data is not a dependency.

## Executed regression commands

Locked Python 3.13.13, NumPy 2.4.6 and PyMuPDF 1.27.2.3, with API/test extras:

```sh
# Repository root
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services .venv/bin/python -m unittest discover -s tests -t . -v
# research/events/2026-09-17-spk-liquidations/price_detectors/
PYTHONDONTWRITEBYTECODE=1 /home/safa/Documents/project-50k/.venv/bin/python -m unittest test_detectors -v
# docs/handoff-v0.5/
PYTHONDONTWRITEBYTECODE=1 /home/safa/Documents/project-50k/.venv/bin/python -m unittest discover -s tests -v
```

Final P5 run: root **503 tests, 18.222s, OK**; frozen price **9 tests, 0.283s, OK**;
frozen handoff **88 tests, 0.003s, OK**. No skips. Exact local logs:
`/tmp/p50k-app-regression-{root,price,frozen}-p5.log`.
The earlier dependency/Decimal-context failures were fixed and tested; original
preregistered futures math/runners were not patched.

From `frontend/`, actually executed:

```sh
npm run typecheck
npm test
NEXT_TELEMETRY_DISABLED=1 npm run build
npm run test:browser
```

Typecheck and optimized webpack build exited 0. **47 unit tests passed, 591ms**.
Raw logs: `/tmp/p50k-frontend-final-{unit,typecheck,build}.log`.
**26 production-build browser tests passed in 12.2s**, exit 0. The final
desktop-mounted chart → 390-pixel viewport → rendered PDF → close check passed
in 724ms. It preserves all six authored chart rows, their null gap and exact D1
value without body overflow. The suite also covers rapid filters/history,
100-record coverage, missing/stale data, errors/retry, bundle/code/source
validation, verified PDF pages, corrupt bytes/headers and modal keyboard focus.
Raw log: `/tmp/project-50k-browser-production-resize-20261008.log`.
Fixtures/PDFs are independently authored; no real screenshots, traces or video
are produced by committed browser tests.

## Runtime and visual verification

The combined launcher runs the explicit sealed bundle in production mode, on
`127.0.0.1:3060` and `127.0.0.1:8767` only. Both HTTP probes returned 200 with the
same bundle. `--mode production --check` returned 0. Startup creates no data,
performs no calibration/download/migration and installs no dependencies.

The direct launcher also checks generated PDF.js assets. The locked npm install
prepares them via postinstall; explicit `prepare:pdfjs` is available if scripts
were disabled. An actual missing-assets probe was refused with exit 1; postinstall
recreated all 202 asset files byte-identically, then the same check returned 0.
Probe record: `/tmp/p50k-pdfjs-prerequisite-probe.json`.
A scan of 277 production/PDF asset files found no actual fund names, private
bundle ID or source hashes: `/tmp/p50k-frontend-final-asset-audit.json`.

Manual CUA verification used actual private list/detail data, including full,
missing and stale cases. The actual three-page KAP PDF rendered visibly in the
in-app browser; page change, zoom, Escape and focus restoration worked. Native
PDF iframe support was blank in that browser, so local PDF.js rendering replaced
it. After mounting the actual chart on desktop, the 390x844 view had a 375-pixel
body and 339-pixel chart; its rendered PDF dialog was 358 pixels wide. Escape
closed the dialog and restored focus to the source button. The grid's child
minimum width now permits the chart to shrink during viewport changes.
The earlier scaffold's eight
major text/background pairs measured at least 5.17:1; this is a limited check,
not a complete accessibility/Impeccable audit. Private screenshots stay in `/tmp`.

## Research limits and handoff

Responses retain `HISTORICAL_REPLAY`, `EXPLORATORY_ARCHIVE`, cutoff
`2026-09-16T23:59:59+03:00`, `RECORDED_SOURCE_DATE_FILTER`, false point-in-time
verification, unknown historical availability/rights, October 2026 universe
selection and current-snapshot categories. Production decisions stay `ABSTAINED`;
strict `ReplayCursor` is unchanged.

Flow uses eligible monthly July/August reports only. Known incompatible units,
actions or ambiguous reports disable it. Unknown currency/scope/action history
stays conditional; displayed amounts retain report-currency units. No buy/sell
advice or verified crisis-beforehand detection is established. Arbitrary-date
selection still needs a separate selection/freshness protocol.

See [local startup](../../ops/local/README.md), [approved design](top100-fund-app-design.md)
and [app plan](../../plans/2026-10-08-top100-fund-research-app.md).
A fresh Git clone contains code and synthetic tests, but requires the owner's
private archive or sealed bundle for actual results.
