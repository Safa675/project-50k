# Top-100 fund app: screen review

Date: 2026-10-08. Scope: private laptop research prototype.
Status: concrete synthetic wireframe prepared; owner design review pending.

## Hierarchy

The header names `Fon araştırması`, Project 50K, and archive mode. The list leads
with `Fonların verileri ne söylüyor?`, the fixed Istanbul cutoff, archive limits,
then denominator-labelled data availability counts. A single toolbar searches
code/name and filters category/finding. A comparable table shows code, category,
D1 statistic, signed estimated-flow statistic, deterministic comment and missing
state. On narrow screens the same fields become a readable record list; source
and missingness meanings remain present. Finding order is descriptive, not a risk
score.

Detail leads with the synthetic fund identity and authored illustrative comment.
Two separate metric panels retain different observation periods. The current
chart is an authored static SVG with an illustrated gap; it does not render
`chart.points` or use Lightweight Charts yet. A pure segmentation helper is
tested for a later actual chart. The source panel illustrates recorded
publication, retrieval and unknown historical availability, plus a missing-PDF
state. Real manifest-backed PDFs and official disclosure links are later
integration work, not verified functionality of this scaffold.

## Concrete review routes

`/preview` contains six authored synthetic records, including two findings,
one finding, finite-but-stale D1, fully unavailable input and no crossings.
No preview fund or quantity is a real archive result.
`/preview?detail=AAA` illustrates detail hierarchy; `detail=DDD` illustrates an
unavailable chart/metric. Search has a no-match state. `state=error` and
`state=loading` provide actual rendered transport states. These synthetic routes
must remain conspicuously labelled and separate from real runtime research data.
The current `/` and `/funds/[code]` routes redirect to this synthetic preview;
they do not fetch or display the private 100-record research bundle. Runtime
API/contract helpers exist with synthetic tests but are not wired to these pages.

## Visual and accessibility rules

Light neutral canvas, ink type, restrained green accent, tabular quantities and
quiet separators. No decorative gradients, trading terminal density, invented
risk score, safety verdict or AI badge. System fonts support Turkish glyphs.
Text labels carry significance alongside color; visible keyboard focus, labelled
controls, semantic headings and reduced-motion rules are required. Mobile does
not hide missingness. A later PDF dialog must use native focus containment,
Escape and focus restoration. The current custom overlay code is not exercised
by the synthetic preview and does not yet satisfy those dialog requirements.
The illustrated chart has period/unit text; unavailable charts retain the source
panel. Browser checks cover the rendered scaffold, not an actual source PDF or
private API outage.

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
resolved versions. Lightweight Charts is the single installed chart library;
its actual chart component remains pending design approval and integration.
Turkish messages use a client `next-intl` provider with an explicit locale and
time zone; no server translation plugin or server API data fetch is needed by
the current scaffold.

## Gate and limitations

This is a concrete owner-review scaffold, not designer approval or an Impeccable
audit. G09 remains open until the owner reviews this screen. Backend/contracts
may proceed independently; the real-data UI integration follows concrete design
approval. Historical archive/version availability, rights and competition gates
remain unresolved. No account, deployment, public/LAN listener or production
authentication change is included.

## Executed scaffold verification

From `frontend/`: `npm run typecheck`; `npm test` (28 synthetic tests);
`npm run test:browser` (5 headless system Chrome checks against the loopback
preview); `npm run build` (Next.js 16.4.0, webpack). These passed on 2026-10-08.
The browser checks include search/reset/no-match, unavailable detail/source,
loading/error illustrations, 390-pixel layout/keyboard focus, and filtered
detail/back state restoration. Screenshots, traces and videos are disabled.

Runtime schema tests reject invalid status/unit/numeric/source fields and false
D1 or signed-flow screen claims. Decimal threshold comparisons are exact string
comparisons; the frontend does not independently redo the Python endpoint
division. Real bundle calculations, API, chart rendering, PDF access and the
100-record UI have not been verified through this scaffold.
