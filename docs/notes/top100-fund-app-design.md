# Top-100 fund app: screen review

Date: 2026-10-08. Scope: private laptop research prototype.
Status: the owner approved the concrete two-screen layout on 2026-10-08 ("design is okay go on"). Runtime integration and local acceptance checks are complete. This is layout approval, not completion of all G09/design audit work.

## Hierarchy

The header names `Fon araştırması`, Project 50K, and archive mode. The list leads
with `Fonların verileri ne söylüyor?`, the fixed Istanbul cutoff, archive limits,
then denominator-labelled data availability counts. A single toolbar searches
code/name and filters category/finding. A comparable table shows code, category,
D1 statistic, signed estimated-flow statistic, deterministic comment and missing
state. On narrow screens the same fields become a readable record list; source
and missingness meanings remain present. Finding order is descriptive, not a risk
score.

Detail leads with the selected fund and its bundle-provided deterministic comment.
Two metric panels retain their separate periods, exact inputs, missing reasons
and qualifications. D1 is the median of daily excess log returns over its actual
window; flow is a signed conditional endpoint estimate. The actual Lightweight
Charts component consumes the bundle's common-baseline indices, splits null gaps
and provides a keyboard-readable data table. The chart is separate from D1.

The primary source panel shows the fund's own prices, extracted monthly data,
notification list and original PDFs. Peer price archives and code/protocol/global
versions remain accessible in labelled collapsed sections. Source titles are
Turkish; exact hashes and filenames remain in version details. Official KAP links
use validated numeric disclosure IDs. PDF opening validates the exact manifest
hash, fixed bundle/cutoff and response provenance before local PDF.js rendering.
Its pinned worker, fonts and decoders are served locally. Verified original bytes
also have ephemeral download/open links; closing revokes them and destroys the
renderer. A missing PDF stays explicitly unavailable.

## Concrete review routes

`/preview` contains six authored synthetic records, including two findings,
one finding, finite-but-stale D1, fully unavailable input and no crossings.
No preview fund or quantity is a real archive result.
`/preview?detail=AAA` illustrates detail hierarchy; `detail=DDD` illustrates an
unavailable chart/metric. Search has a no-match state. `state=error` and
`state=loading` provide actual rendered transport states. These synthetic routes
must remain conspicuously labelled and separate from real runtime research data.
The `/` and `/funds/[code]` routes now load the private API at browser runtime.
They never fetch real financial data during Next.js build or server rendering.
List/summary fingerprints must agree; detail code, expected bundle and source
references are validated. Links retain filters and the exact bundle. A changed
bundle fails visibly instead of mixing versions. Loading/error/retry, unknown
fund, malformed response and request-abort states preserve unavailable results.
Filter-only URL updates use Next.js-supported native history replacement. The
current search parameters control the fields; delayed server route responses
cannot restore an earlier category over a newer local edit. Browser history
retains the selected filters when returning from a detail view.

## Visual and accessibility rules

Light neutral canvas, ink type, restrained green accent, tabular quantities and
quiet separators. No decorative gradients, trading terminal density, invented
risk score, safety verdict or AI badge. System fonts support Turkish glyphs.
Text labels carry significance alongside color; visible keyboard focus, labelled
controls, semantic headings and reduced-motion rules are required. Mobile does
not hide missingness. The PDF viewer uses a native modal dialog, Escape, focus containment and
restoration. The actual chart carries period/unit text and a tabular equivalent;
unavailable charts retain the source panel. Main and preview query parameters
are sanitized so duplicate URL fields cannot crash the controls. Mobile retains
category, both metric names, values, comments and missingness.

## Reuse and notices

Copied/adapted generic primitives: DataTable, Toolbar, Chip, Stat, EmptyState,
form classes and cn from Bilun commit
`cafa27bc9d7f6fe4c6a75f1eaea431fed90e2f52`. Copyright statements and the exact
proprietary notice are in `frontend/BILUN-NOTICE.txt`. Only narrow transport/proxy
patterns are adapted; no Bilun patient/chat/sidebar/cache source or data is
included. Source reuse was authorized by the owner for this private app; this
record grants no public redistribution rights.

Dependencies were resolved fresh from registry metadata and the current official
Next.js App Router installation, next-intl App Router, Tailwind Next.js and
TradingView Lightweight Charts documentation. The npm lock records actual
resolved versions. Lightweight Charts is the single chart library and now renders the actual
bundle-provided normalized series.
Turkish messages use a client `next-intl` provider with an explicit locale and
time zone; no server translation plugin or server API data fetch is needed by
the current app.

## Gate and limitations

The owner approved the reviewed layout. This is not an Impeccable audit, a
formal designer signoff on every interaction or complete G09 closure. Current
keyboard/mobile/browser checks cover the local implementation; remaining audits
and source-rights/competition gates stay separately recorded. Historical archive/version availability, rights and competition gates
remain unresolved. No account, deployment, public/LAN listener or production
authentication change is included.

## Executed local verification

From `frontend/`: `npm run typecheck`; `npm test` (47 unit tests);
`npm run test:browser` (26 system Chrome checks against the production build);
`npm run build` (Next.js 16.4.0, webpack). All passed on 2026-10-08. Browser
fixtures contain 100 independently authored synthetic records and a two-page
PDF; screenshot, trace and video recording is disabled. Actual private list,
detail, missing/stale cases and original KAP PDF rendering were separately
inspected in the in-app browser. A chart mounted on desktop then resized to
390 pixels fits without body overflow, including while the PDF is open.

Runtime schema tests reject invalid status/unit/numeric/source fields, foreign
fund KAP evidence and false D1 or signed-flow screen claims. Decimal threshold
comparisons are exact string comparisons; the frontend does not independently
redo the Python endpoint division. Exact results and remaining limitations are
in the [completion note](top100-fund-app-completion.md).
