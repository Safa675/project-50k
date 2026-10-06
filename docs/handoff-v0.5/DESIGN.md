# Project 50K — design direction and quality contract

Status: proposed direction, designer approval required. UI Turkish; engineering discussion English.

## Character
Calm, precise financial intelligence with editorial hierarchy. More readable than a dense trading terminal, more informative than a decorative consumer fintech. Start with a light neutral canvas, dark readable type, disciplined data alignment and a restrained accent. Proposed tokens are in `config/design_tokens.json`, not a final brand.

## Hierarchy
One clear primary action per page. On an event show what changed, source/as-of, why it matters and what remains unknown. Severity, evidence strength, market direction and freshness use distinct text labels. A score never substitutes for an explanation.

Use tables for comparable numbers, text for reasoning, and charts for genuine time-series context. Avoid card-inside-card layouts, endless pills, gradient hero blobs, neon status soup, arbitrary animated counters, fake testimonials and repetitive “AI-powered” labels. Empty space is intentional; density is earned by useful content.

## Typography and data
Use a locally safe system stack initially; choose any final licensed family with proper Turkish glyph testing. Tabular numerals for aligned data. Dates and currency use `Intl` with `tr-TR`; machine time stays UTC and user time is Istanbul. Price precision follows asset semantics, not one global two-decimal rule. Small text must remain readable.

## Interaction and accessibility
Visible focus, semantic headings, reachable menus, reduced motion and no color-only significance. Narrow screens retain chart/evidence/limitation meaning; secondary metrics can collapse but source/freshness cannot disappear. Do not cover the asset page with a mandatory chat panel. Chat is an optional drill-down.

## Turkish examples
`Takip listem`, `Piyasada öne çıkanlar`, `İşlem hacminde sıra dışı artış`, `Portföy dağılımında değişim`, `Kanıt gücü`, `Kaynakları incele`, `Veri gecikmeli`, `Bu veri şu anda alınamıyor`, `Geçmiş verilerle gösterim`, `Örnek verilerle gösterim`.
Never write “Portföyün” when only a watchlist is known. Never call an unavailable detector “Normal.”

## Design workflow
Designer brief/reference → page hierarchy and states → token/component contract → agent implementation → current Impeccable audit/critique/polish workflow → manual designer and accessibility review → fix findings. Verify current Impeccable command syntax from the installed version. No claim that its audits were run on this spec-only package.

## v0.5 exploration
A proposed İzvanta logo and Mineral/Ink palette, two alternatives, Turkish static preview and reproducible contrast arithmetic are retained in research/brand_lab. Current tokens are not automatically replaced. Logo is a raster concept; no production vector, tiny-size review, full accessibility/Impeccable or owner/designer approval is claimed.
