# BlackSwan Figma implementation, 2026-10-10

Implementation checkpoint for T5.5, with T3.6 fund screens and T5.2 contextual
chat integration. Final integrated verification and release are still in progress;
this report does not claim the final build has been deployed or merged.

## Result and scope

Figma access is fixed. All 22 requested nodes were read as design context and
screenshots, following the installed `figma-design-to-code` skill. The request
contains ten base pages/states and twelve hover/context variants. The full links
and route/state mapping are retained in
[the implementation record](figma-implementation-2026-10-10.md).

Four agents worked in parallel with separate file ownership. The implementation
adds the supplied typography, dark palette, exact logo and SVGs, spacing, pill
controls, source cards, charts, contextual tooltips and chat drawer. Theme choice
persists locally. Navigation/search, account actions, watchlists, notification
preferences/read state, evidence feedback and chat use working product paths.
Real-data access remains authenticated; the public landing page does not expose
private observations.

## Changed files

- Shared UI: `web/app/design.css`, `web/app/layout.tsx`, `web/app/page.tsx`,
  `web/app/method/page.tsx`, `web/components/DesignShell.tsx`,
  `web/components/RealEvidenceExample.tsx`, `web/lib/optional-user.ts`,
  `web/public/design/`, `web/public/fonts/`, and the fund/stock layouts.
- Fund screens: `web/app/funds/page.tsx`, `web/app/funds/[code]/page.tsx`,
  `web/components/Funds.module.css`, `FundEvidence.tsx`, `FundSections.tsx`,
  `FundShare.tsx`, `FundTooltip.tsx`, `NavChart.tsx`, `web/lib/fund-display.ts`
  and exact fund SVG assets.
- Watchlists/notifications: `web/app/watchlist/`, `web/app/notifications/`,
  `WatchlistButton.tsx`, `WatchlistViews.tsx`, `watchlist.css`, exact watchlist
  assets, `services/p50k/product/watchlists.py`, `watchlist_routes.py` and
  migration `009_watchlist_notifications.sql`.
- Development detail and contextual chat: `web/app/developments/`, evidence
  components/styles, `ChatPanel.tsx` and its styles, evidence backend routes,
  migration `010_evidence_feedback.sql`, and related browser/backend tests.
- Records: current state, team asks, build plan, Figma mapping and this report.

These are new product modules and migrations. The frozen handoff, detector
protocols, calibrated detector modules and registered research-demo sources were
not changed by this design slice.

## Truthful adaptations

- Figma example growth multiples and sample financial values are not hardcoded.
  Evidence cards use stored detector values, thresholds and source references;
  anonymous visitors see the case context and a real sign-in link.
- Catalog ordering is stated as alphabetical where investor ranking is not
  supported by the current data. No popularity ranking is fabricated.
- Charts use actual NAV observations and preserve gaps. Available ranges follow
  the API's two-year bound rather than the design's unsupported five-year control.
  No allocation tab, historical unit series, return figure or currency assumption
  is added when the source does not support it.
- Evidence provenance and availability replace invented confidence scores.
  Unknown publication time remains unknown; identity-confirmed SPK entries with
  unknown publication time remain ineligible to trigger.
- The method page describes current funds and BIST 30 support. It does not retain
  obsolete stock exclusions or promise every detector for every instrument.
- Existing email/password authentication is retained. Figma registration/OAuth
  ideas do not imply a new account provider or a nonfunctional button.
- Notification badges depend on actual unread records; empty states and disabled
  notification preferences describe stored state. No fabricated personal feed is
  shown to a signed-out visitor. Only the real in-app preference is offered; email
  delivery and scheduled summaries are not claimed.
- Dark frames are the high-fidelity target. Light theme is an accessible functional
  adaptation, not a separately verified light Figma frame.
- The LLM remains bounded to approved derived evidence. It does not receive raw
  price series, TEFAS size/unit/investor values, KAP text or private human-review
  details. The original proposal and human review remain separately visible.

## Actual verification at this checkpoint

Shared-shell checks ran from `web/` against Next.js development port 3000 and the
isolated synthetic backend on 8771, using a temporary Playwright configuration
outside git:

```text
npx playwright test foundations.spec.ts --config C:/Users/mirza/AppData/Local/Temp/blackswan-design-review/playwright.config.mjs
3 passed (8.1s)
```

The three tests cover public authentication boundaries and persistent theme
choice; search navigation to the protected catalog; method anchors, nonempty
local image loading, intrinsic asset geometry and no document overflow at 1440
and 390 pixels. Desktop landing/method screenshots were inspected against Figma.
Both routes returned HTTP 200 with no browser JavaScript errors. Screenshot
artifacts remain outside git in Windows TEMP.

All 29 shared SVG files were checked for nonempty valid XML and root dimensions.
The exact logo remains approximately 26 pixels, feature icons 40 pixels, method
icons 20 pixels and small contextual icons 16/14/6 pixels as designed. Font files
include their upstream license. The last shared-shell typecheck attempt observed
only the then-in-progress contextual ChatPanel property changes; it was not
reported as a pass. Final combined typecheck/build/browser results must be
recorded after root integration.

## Additional per-agent checks

These are completed checks reported by the implementing agents, before the final
combined root regression pass:

| Check | Actual result |
|---|---|
| Fund UI: `npm test` | 16 tests passed across four files |
| Fund UI: `npm run typecheck` | Exit 0 |
| Fund UI: `npm run test:browser -- tests/browser/fund-design.spec.ts` on isolated 3071 | One passed in 2.2s |
| Watchlist PostgreSQL: `tests.unit.test_product_watchlists` | Six passed, zero skips, 0.785s |
| Watchlist frontend typecheck and Docker web build | Exit 0 |
| Watchlist browser: `watchlist.spec.ts` | Two passed in 6.5s |
| Root PostgreSQL watchlist/evidence integration | Nine passed, zero skips, 1.048s |
| Root PostgreSQL chat/API integration | 32 passed, zero skips, 2.036s |

Fund review additionally checked eight source disclosures, two null NAV rows,
chart Home/ArrowRight navigation against the table, and tooltip focus/Escape.
Desktop 1440/mobile 390 views had no overflow. Shared/reused SVG hashes and
rendered geometry were verified. The KAP-document asset is valid, but a populated
KAP marker and document-icon DOM geometry remain untested because the synthetic
THF fixture has no such document; do not count this as covered.

Watchlist checks covered persistence through reload, removal, notification
preference changes and rollback on a failed update. Its eleven exact SVG assets
were nonempty with matching natural/rendered dimensions; desktop/mobile, empty
and signed-out views were visually inspected. One initial checkbox-state failure
was fixed before the recorded two-test passing run.

## Root integration checks

The final point-in-time chat test verifies that a selected historical item loads
its original run, another fund cannot select it, future-run evidence is rejected,
and the read creates no decision packet. The database independently rejects an
item whose availability exceeds its run cutoff.

From the build worktree, the following commands completed successfully:

```text
docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm -e P50K_DB_NAME=p50k_dev -e P50K_TEST_ENDPOINTS=true -e P50K_TEST_DATABASE=1 --volume ./tests:/app/tests:ro --volume ./services:/app/services:ro worker python -m unittest tests.unit.test_product_evidence_detail tests.unit.test_product_watchlists tests.unit.test_product_chat tests.unit.test_product_api -q
Ran 42 tests in 3.234s; OK; zero skips

P50K_DB_NAME=p50k_dev docker compose -p p50k-smoke -f compose.yaml run --no-deps --rm -e P50K_TEST_DATABASE=1 --volume ./tests:/app/tests:ro --volume ./services:/app/services:ro --volume ./db:/app/db:ro migrate python -m unittest tests.unit.test_product_migrations -q
Ran 16 tests in 1.255s; OK; zero skips

cd web
npm run typecheck
Exit 0
npm test
4 test files, 16 tests passed
```

Review also corrected shared detector names, prevented negative values from
appearing as positive comparison bars, keyed chat/feedback state to evidence,
and verified keyboard focus when reopening a busy chat drawer. The first full
browser run passed 13 tests and failed one stale stock-navigation selector. The
selector was adapted to the supplied account menu; its targeted rerun passed.

## Data mode and remaining work

Product data is local DELAYED source data, with UNREVIEWED redistribution rights.
Tests and browser artifacts use synthetic data. Every detector result remains a
development result, with no accuracy, prediction, advance-warning or fraud claim.

Final available fund import contains 2,133 funds, 1,755,010 price rows, 3,304
snapshots and 12,111 KAP document entries. Run
`4dcee718-6c5b-4506-b251-2ed563260b60` has 17,064 results using the original single
calibration. Real stock support contains 30 current BIST 30 members, 870 daily
closes and five corporate-action observations; there is no stock classifier/AI.

Seven paid live model/decision/chat calls have completed. The read-only ledger
check around 20:02 Istanbul recorded USD 0.0615725 conservatively booked, 11,701 input
tokens and 3,232 output tokens, with zero reservations and no queued/running
jobs. This smoke does not replace measured tuning quality or authorize an
ungated batch.

The successful backup/restore rehearsal covered a consistent snapshot of 34
tables and eight migrations. It predates the final refresh and migrations
009/010; repeat it after final data and review changes. Final integration tests,
leak scan, merge/push, runtime verification, freeze backup/tag and cold-boot/demo
rehearsals remain distinct completion steps. Optional challenger/committee work
is not represented as implemented.
