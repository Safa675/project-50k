# Dated D1 view: design note and protocol clarifications

Slice: DEC-026, `research/events/2026-09-17-spk-liquidations/fund_review_dated/PROTOCOL.md`.
This note records how the implementation reads the protocol where its text needed
interpretation, and the owner reviews. It does not change any protocol rule.

## Protocol clarification 1: later dates in required sentences

PROTOCOL.md "Records, comments and order" says that no date after the selected date
may appear, except in the date selector's options and the fixed-view link sentence.
The same section requires three sentences that name later dates:

- the survivorship sentence ("Ekim 2026");
- the snapshot label "Ad ve kategoriler: {date} anlık görüntüsü." (the snapshot date
  is after every cutoff);
- the "Neden yalnızca bu tarihler?" text ("Ağustos 2026").

Reading: these three required sentences are also exempt from the later-date rule,
because the protocol requires them verbatim. They state how the fund list, the
names and categories and the dates were chosen, and they report no outcome,
observation or finding dated after the cutoff. No other text is exempt; the browser
check names exactly these sentences. The conflict was found by the independent
frontend review on 2026-10-10 and recorded here before the first real index was
sealed.

## Implementation readings recorded during the build

- `PREREGISTRATION.md` is registered as a PROTOCOL source, not CALIBRATION, so the
  audited (PRICE, UNIVERSE, CALIBRATION) reference sets stay identical to v1's.
- Dated pages use their own header and footer instead of the shared `Shell`, whose
  footer and preview link are fixed-view text.
- The browser fetches dated data only through the same-origin proxy; the dated API
  sets no CORS headers.
- A source's `retrieved_at` may be after the cutoff (it is the archive retrieval
  time). It is never displayed as evidence time; `published_at` stays at or before
  the cutoff.

## Owner reviews

- Review point A (protocol and DEC-026): approved in chat on 2026-10-10 and
  committed as `d8e445b` before any dated runtime commit.
- Review point B (synthetic `/preview/dates` layout): delegated to the agent by DEC-027 and done on
  2026-10-10 before the real view was opened, from private screenshots at 390, 768 and 1440 px of the ready,
  earliest-date, detail and unregistered-date states. No horizontal overflow, the guard sentence on every
  state, no fabricated rows in error states. The only console message was one 404 for the absent favicon.
- Review point C (real `/dates` after sealing): delegated likewise and done on 2026-10-10 on the sealed index
  `6623c78d…`, at the same widths for the default date, 2025-10-31, an unregistered date and a fund detail
  page. Same results. Notes: the native select truncates the long window-end label on desktop (the full text
  shows when opened); at early dates the eligible crossings that sort first include liquidated targets, which
  is exactly the reading the guard sentence and DEC-025's pitch limits address.

These reviews approve layout and wording only. Screenshots of real data stay private. G09 (design gate)
stays open.
