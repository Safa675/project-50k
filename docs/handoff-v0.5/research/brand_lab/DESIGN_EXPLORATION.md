# Project 50K — visual direction exploration

Prepared 2026-10-02. **Status: proposals for owner and designer review.** This exploration does not approve a name, logo, tokens or product screen. It leaves the existing PRODUCT/DESIGN and shared design tokens unchanged. Relevant requirements: UR-020–027, UR-044, UR-073–077; FR-072–080, FR-112–119; NFR-056–069 and NFR-082.

## Recommended direction: Mineral / Ink

Make the product feel like a small, well-edited financial research instrument. Cool paper, dense ink, quiet petrol actions and generous typography give it authority without suggesting a trading terminal. The distinctive object is the evidence story: a specific change, its observation time, two or three useful numbers, its sources and what remains uncertain. Visual character comes from type, precise alignment and the repeated inspection-frame motif rather than decoration.

Use one light theme first. The identity should work on a phone in daylight and in a jury presentation; this is a design hypothesis, not an observed usability result. The owner-selected demonstration still includes BIST, Turkish funds, crypto, US equities and meaningful on-chain. The same hierarchy covers them while the data modules preserve their actual capabilities and cadence.

### Three palette proposals

| Role | Mineral / Ink — recommended | Aubergine / Frost | Graphite / Copper |
|---|---|---|---|
| Canvas | `#F4F6F7` | `#F6F5F8` | `#F7F6F3` |
| Surface | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` |
| Soft surface | `#EAF0F3` | `#EEEAF2` | `#F0ECE5` |
| Main ink | `#172A31` | `#292332` | `#2D2924` |
| Secondary text | `#52656C` | `#625B6B` | `#675E53` |
| Action/brand | `#234B5D` | `#5A4268` | `#7A4937` |
| Action hover | `#183C4B` | `#45324F` | `#603A2C` |
| Required control edge | `#75888F` | `#837B8B` | `#897F72` |
| Decorative separator | `#C8D2D7` | `#D0CBD6` | `#D6CFC5` |
| External focus | `#152F42` | `#152F42` | `#152F42` |

Mineral / Ink provides the clearest separation between actions, financial direction and alert importance. Aubergine offers a more unusual brand character, but violet must not become an ambiguous mixture of branding, replay and critical events. Copper feels tactile and editorial, but broad tan surfaces or copper warnings would weaken its functional distinction. These are judgments to test with the designer, not measured customer preferences.

## Logo metaphor for the naming lane

Develop an **open inspection frame around an offset observation**. Two bracket-like edges or restrained corner strokes define a frame; one small datum or short horizontal trace is slightly displaced inside. It expresses “an unusual observation, brought into context.” The mark can also inspire the event's source/evidence affordance and the selected point on a chart.

Keep the silhouette readable in one ink color, at 16/24/32px and on a plain app tile. Use a substantial stroke and few parts; no tiny network-node constellation. A compact optical wordmark can sit beside the mark; the final name determines spacing and glyph details. A designer must redraw and check the resulting mark for reproducibility, originality and legibility. An image-generation concept is a visual proposal, not a vector-ready trademark or a uniqueness check.

Alternative metaphor: two offset parallel layers becoming aligned at a small shared center, suggesting evidence reconciliation. The inspection frame is the stronger first exploration because it provides a simple reusable interface motif. Rising arrows, shields, coins and candlestick emblems would imply returns, safety or a brokerage rather than the chosen product promise.

## Typography and Turkish content

Start with `system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` as the implementation fallback. This avoids a font download as a dependency for the first layout. Device-specific glyph and numeric behavior still need actual browser checks; a system stack is not a tested universal font.

**Optional designer candidate: IBM Plex Sans**, using restrained 400/500/600 weights throughout. Its slightly technical forms suit readable evidence and allow the visual identity to emerge without a second decorative display face. IBM's official repository describes extended-Latin support and UI suitability; its included license is OFL 1.1 with the reserved font name Plex. This makes it a plausible candidate, not proof that a specific delivered subset includes all Turkish glyphs. Inspect the exact selected files, keep their license/notice if distributed, and do not imply IBM endorsement. No fonts were downloaded or bundled here.

Suggested type hierarchy: 16px body with approximately 1.5 line height; 14px supporting labels; 22–28px event title; 36–48px landing headline with short line length. Give numeric rows tabular figures when the selected font supports them; use proportional figures in prose. Reserve monospaced text for literal contract/mint identifiers and expandable technical details. Do not letter-space Turkish body copy or force all-caps labels.

The actual glyph rehearsal should include `İ ı Ş ş Ğ ğ Ü ü Ö ö Ç ç`, `Ilıca`, `İşlem hacmi`, `Günlük fon pay fiyatı`, `Önemli gelişme`, `₺ 1.234,56`, `−%3,2`, `0,00001234` and long company/fund names. Test both normal and semibold, wrapping, search casing and truncation. Locale casing/normalization is an implementation test, not solved by a font choice. English identifiers stay in the engineering layer.

## Semantic grammar

| Channel | Visual treatment | Required meaning |
|---|---|---|
| Actions/navigation | Petrol action color, visible label, underline for inline links | Something the user can do |
| Event importance | `Dikkat`, `Önemli`, `Kritik`; icon and fixed location, restrained ochre/orange/plum | Importance, independent of market direction |
| Evidence strength | Ink text `Kanıt gücü: 78/100`, expandable method/components; no score if unavailable | Inspectable heuristic support, never a probability or safety rating |
| Price direction | Explicit signed number, `yükseldi`/`geriledi` when helpful; green/red as a supplement | Price movement only |
| Data mode/freshness | Reserved band with source, as-of time and clear mode/coverage text | Live/delayed/replay/synthetic/partial/stale/unavailable; current data is not a safe asset |
| Sector/category/series | Named legend/direct label plus differing line patterns; quiet categorical colors | Identity, with no good/bad or severity meaning |

Proposed event text/background pairs: attention `#805300`/`#FBF4E2`; important `#9C3F17`/`#FFF0E7`; critical `#80314D`/`#FBEAF1`. Proposed price pairs: rise `#1F684C`/`#E8F4EE`; fall `#9D3342`/`#FBECEF`. Exact source-state and series colors are in color_candidates.json. These are separate token channels; similar hues can still be confused, so labels, location and shapes carry the distinction. Color alone cannot encode the product's semantics.

Avoid a bright status tile for every metric. A critical event gets one importance marker; chart direction stays in its numeric row; evidence strength is a quiet textual observation; freshness sits with the source. This lets a normal decline, a concerning rise and unavailable evidence remain intelligible.

## Layout, density and mobile behavior

**Landing:** a concise value proposition, prominent asset search, one evidence-rich product example and a small scope/method explanation. The example's live/delayed/replay/synthetic label is visible. No invented metrics, reviews or client logos. The identity can use the inspection frame sparingly around the example rather than around every paragraph.

**Feed:** prioritize a small number of useful developments. Use editorial rows with a clear asset/type/time line, strong title, brief explanation and one source/evidence action. A chart thumbnail earns space only if it explains the event. Secondary items can be compact rows; ranking and coverage must be explained rather than treated as certainty.

**Asset/event:** identity and coverage first; chart and event timing next; then what changed, evidence, alternative explanations and limitations. Source drawers use real records and retain publication/availability dates. Chat is a contextual drill-down after the evidence, with short suggested questions. Asset-specific modules can differ: dated fund NAV/allocation; market volume/venue; chain/contract/mint/finality/coverage.

**Desktop:** use an approximately 1200px maximum content width, a generous main evidence column and a restrained optional side rail. Prefer separators, aligned numeric columns and a few emphasized surfaces to nested cards. The chart needs room for its time axis; the main event narrative should remain a readable measure.

**Mobile:** test 390px and additionally 320px reflow, alongside 768/1440px. Stack identity, source/date, chart, selected event and evidence in that order. Keep source/mode/limitations visible; collapse only secondary metrics. “Bu gelişmeyi sor” opens a user-controlled sheet or a dedicated view with predictable back/close behavior. Use explicit chart controls and an accessible table/summary so a drag gesture is not the only way to inspect data. Keep page scroll available over the chart. No compulsory chat overlay.

## States and interruption

| State | Proposed behavior/copy |
|---|---|
| Loading | Stable layout and an honest short progress label; avoid endless skeletons after known source failure |
| No eligible event | `İzlediğimiz verilerde yeni bir uyarı yok.` plus actual coverage; never imply safety |
| Partial evidence | Show available evidence and name the missing scope rather than silently filling it |
| Stale/delayed | Explicit age/lag with the source; essential text remains normally readable |
| Unavailable | `Bu veri şu anda alınamıyor.` with retry/status; no disabled gray explanation |
| Replay | `Geçmiş verilerle gösterim` with cutoff/origin; no current-research confusion |
| Synthetic | `Örnek senaryo — gerçek piyasa olayı değildir.` persistently visible |
| Chat abstention | `Bunu doğrulamak için yeterli veri yok.` and the available evidence/coverage limit |
| New event | Quiet inline update or deliberate notification; no flashing chart, forced refresh or jumping reading position |

Keep high-importance event opt-ins, email modes and data coverage distinct in preferences. Use “Takip listem” for the user's list. A fund's actual allocation can be called “Varlık dağılımı”; a followed asset does not become an owned position.

## Contrast experiment: scope and results

The script implements the W3C opaque sRGB luminance conversion using the 0.04045 breakpoint and contrast `(lighter + 0.05)/(darker + 0.05)`. AA normal text uses 4.5:1; eligible large text uses 3:1, but this experiment conservatively treats every proposed text pair as normal. Required UI/graphic contrast uses 3:1. Genuinely inactive controls are exempt; we separately test a voluntary readability target. Decorative separators are qualified only when not necessary to identify a control/data. [BR-WCAG22](https://www.w3.org/TR/WCAG22/)

Focus is proposed as an external 3px opaque outline with a 2px surface-colored offset, so the tested adjacency is the surrounding light surface. Actual geometry, clipping and obscuration need rendered checks. W3C's supporting guidance explains adjacency; its focus-appearance criterion is AAA and is not asserted as passed here. [BR-NONTEXT](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html), [BR-FOCUS](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html)

Executed command: `python experiments/color_contrast.py` (from the project, or the equivalent project-relative command from scratch). No extra package or network is needed. The output contains an input SHA-256, formula checks, every pair, applicability and unrounded threshold decisions.

| Candidate | Applicable pairs | Below applicable threshold | Qualified exemptions | Lowest normal text | Lowest nontext |
|---|---:|---:|---:|---:|---:|
| Mineral / Ink | 46 | 0 | 4 | 5.312:1 | 3.217:1 |
| Aubergine / Frost | 46 | 0 | 4 | 5.479:1 | 3.420:1 |
| Graphite / Copper | 46 | 0 | 4 | 5.400:1 | 3.338:1 |

All 138 applicable **listed opaque color pairs** meet their chosen threshold. The twelve qualified exemptions are nine decorative divider/surface pairings and three inactive-control labels; their applicability is conditional, not a free pass to reuse them for active content. Each inactive label also meets the voluntary 4.5:1 target. The script checks black/white, identical-color, symmetry and luminance endpoints, and rejects short/alpha/nonhex inputs.

**Not tested:** rendered screenshots, typography/glyphs, browser/CSS compositing, gradient/image contrast, dark theme, chart adjacency or color-vision distinction, keyboard/screen-reader flows, touch/scroll/focus geometry, actual Impeccable or full WCAG conformance. No frontend exists in this package to certify. The designer must approve/replace the direction and inspect a representative asset/event screen and its real states before patterns spread across the product.

## Source review and follow-up

| Source | Review depth on 2026-10-02 | Supported use / boundary |
|---|---|---|
| [W3C WCAG 2.2](https://www.w3.org/TR/WCAG22/) | Relevant normative contrast/luminance/use-of-color/focus/reflow/target sections | Contrast math and criterion distinctions; no full standard/product audit |
| [W3C nontext understanding](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) | UI-boundary, focus adjacency, inactive-control sections | Informative interpretation; not a new normative rule |
| [W3C focus understanding](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html) | Criterion and area/contrast explanation | AAA geometry remains untested |
| [IBM Plex official repository](https://github.com/IBM/plex) | README typeface, UI and extended-Latin description | Plausible typography candidate; selected file glyph/subset proof not established |
| [IBM Plex license](https://github.com/IBM/plex/blob/master/LICENSE.txt) | Copyright, OFL and conditions read | Retain notice/license; reserved-name conditions apply; no fonts bundled or modified |

Next design work: select the name direction, ask the designer to choose/adjust the palette and mark, then create one real responsive asset/event screen with populated/empty/partial/replay/synthetic states. Review Turkish comprehension, source visibility, chart summary, long labels and actual focused controls before additional pages. Run the installed Impeccable workflow and manual designer/accessibility review on that implementation. This exploration creates reproducible proposals only, with no migrations, accounts, spend or remote action.
