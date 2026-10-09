# Disclosed-security concentration in the local fund app

Owner-authorized on 2026-10-09. Implementation is in progress.

Add descriptive AN-FND-006 / FR-038 research to the approved local top-100 app.
FR-018/019 source dates, FR-078 fund-page context and NFR-038 cutoff checks are
partial contributions; no frozen requirement status or release gate is upgraded.

The first slice reads the supported monthly security tables from existing KAP
PDFs, computes identified-security top-1/top-5/top-10 and HHI with explicit
portfolio coverage, and displays them on the list/detail pages. Company/issuer
mapping is unknown. Partial scope cannot become a full-fund concentration claim.
No concentration alarm threshold is selected from the already studied outcomes.

Implementation plan:

- New geometry-aware provider and synthetic parser tests.
- New descriptive concentration arithmetic and sealed extension modules; preserve
  all v1 manifested calculation sources and the original bundle.
- New registered offline runner using selected existing monthly sources only.
- Strict API/client extension, neutral list metric, dated detail/source panel.
- Synthetic arithmetic, replay, source, API and UI tests, followed by independent
  private arithmetic/source checks and actual local browser verification.

Ambiguities resolved before implementation: securities versus issuers, identified
  subset versus full portfolio, monthly versus weekly cadence, stale snapshots,
  repeated lots/totals, signed holdings, derivative notionals, missing source
  identities, unknown historical versions and undefined alarm threshold. The
registered [protocol](../../research/events/2026-09-17-spk-liquidations/fund_concentration_app/PROTOCOL.md)
records the conservative interpretation. Unsupported evidence remains unknown.

Actual completion, verification, coverage and limitations will be recorded here
after execution. No new collection, spending, public release or push is requested.
