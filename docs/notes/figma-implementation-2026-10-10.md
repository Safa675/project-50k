# BlackSwan Figma implementation request, 2026-10-10

Mirza requests all 22 linked designs, implemented against real product data while
backend work continues in parallel. Preserve interactions/auth/evidence/integrity
labels. Insurance remains deferred under DEC-032. Design sample values must not
become fake product data or committed real observation fixtures.

**Access fixed.** The connected Figma tools became available in this session.
All 22 requested design contexts and screenshots were read using the installed
`figma-design-to-code` skill, with its required `skillNames` argument. These are
ten base pages/states and twelve hover/context variants, not 22 separate routes.
No further installation, account action or token is required from Mirza.

Four agents implemented independent areas in parallel: shared shell/landing/method
(two frames), catalog/fund detail and contextual variants (ten), watchlist and
notifications (four), and development detail/chat plus variants (six). Final
integrated verification is in progress; the [completion report](blackswan-figma-completion.md)
records actual checks and limits.

Figma dark tokens, typography, spacing and radii are implemented in project-native
CSS. Exact SVGs and the logo are local, with intrinsic sizes retained; Google Sans
Flex is bundled locally with its OFL license. Screenshot exports are visual review
artifacts outside git, never implementation assets. Light theme is a functional
adaptation; the supplied dark frames are the verified design references.

Interactions use real sessions, persisted watchlists and notification preferences,
source-backed evidence, human review and bounded contextual chat. Design sample
financial values, invented confidence/rankings, Google OAuth and insurance flows
are not introduced. See the adaptation notes in the completion report.

| Requested node | Link |
|---|---|
| 25:456 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=25-456&m=dev) |
| 27:508 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=27-508&m=dev) |
| 21:206 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=21-206&m=dev) |
| 22:382 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=22-382&m=dev) |
| 29:904 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=29-904&m=dev) |
| 45:1605 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=45-1605&m=dev) |
| 28:647 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=28-647&m=dev) |
| 28:832 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=28-832&m=dev) |
| 28:946 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=28-946&m=dev) |
| 44:1554 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=44-1554&m=dev) |
| 84:1696 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=84-1696&m=dev) |
| 84:2000 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=84-2000&m=dev) |
| 84:2310 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=84-2310&m=dev) |
| 84:2622 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=84-2622&m=dev) |
| 84:2926 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=84-2926&m=dev) |
| 84:3230 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=84-3230&m=dev) |
| 84:3534 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=84-3534&m=dev) |
| 84:3838 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=84-3838&m=dev) |
| 87:3297 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=87-3297&m=dev) |
| 87:3561 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=87-3561&m=dev) |
| 87:3825 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=87-3825&m=dev) |
| 87:4089 | [Open frame](https://www.figma.com/design/ZUnoLpfJ5MSq2ZFeLoQBMJ/Black-Swan-%E2%80%94-Ekranlar?node-id=87-4089&m=dev) |

## Route and interaction mapping

| Node | Working route/state |
|---|---|
| 25:456 | `/`: public landing and authenticated real-evidence example |
| 27:508 | `/funds`: category/search controls, evidence feed and alphabetical catalog |
| 21:206 | `/funds/[code]`: daily NAV, sources, evidence, review and chat entry |
| 22:382 | `/developments/[id]?fund=...`: actual detector evidence detail |
| 29:904 | Fund/development contextual chat drawer, validated answers and evidence references |
| 45:1605 | `/method`: source/method explanations and working section anchors |
| 28:647 | `/watchlist`: saved funds with actual triggered-evidence feed |
| 28:832 | `/watchlist`: saved funds without triggers; insufficient/abstained evidence explicit |
| 28:946 | `/notifications`: persisted preferences and read/unread state |
| 44:1554 | `/watchlist`, signed out: real login entry and feature explanation |
| 84:1696 | Fund data-mode/availability tooltip |
| 84:2000 | Published KAP document marker hover/focus/click on the fund chart |
| 84:2310 | Chart point hover and keyboard-selected observation |
| 84:2622 | Missing investor-history explanation |
| 84:2926 | Actual NAV source, availability and publication-date explanation |
| 84:3230 | Units term explanation with absent historical series stated |
| 84:3534 | Deterministic detector-trigger explanation |
| 84:3838 | Source-provenance count explanation |
| 87:3297 | Development data-mode tooltip |
| 87:3561 | Development importance/trigger explanation |
| 87:3825 | Development evidence-provenance tooltip |
| 87:4089 | Development term explanation |

The KAP document marker is implemented using actual `published_at` records, but
its populated state is not verified by the current synthetic THF browser fixture
because that fixture contains no KAP document. Other interaction checks and
remaining coverage limits are recorded in the completion report.
