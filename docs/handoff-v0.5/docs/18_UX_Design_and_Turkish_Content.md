# Project 50K — UX Flows, Design System & Natural Turkish

**Version:** 0.4 audit revision · **Prepared:** 2026-10-02
**Status:** implementation specification / not a claim of deployed functionality.

## 1. Design intent
A quiet, precise financial intelligence product—not a crypto casino, an arbitrary neon terminal or a stock dashboard template. The user should understand “what changed / how strong is the evidence / where can I verify it?” before opening chat. Mobile is the consumer destination; the weekend web experience proves the same hierarchy.

`DESIGN.md`, `PRODUCT.md` and `config/design_tokens.json` supply initial design direction. Tokens are proposals for the designer, not an approved final identity. Impeccable is a review aid, not a substitute for design judgment. Check its current supported integration, review third-party installation instructions and pin the installed revision. Official documentation checked on 2026-10-02 describes PRODUCT.md / DESIGN.md and audit, critique and polish; Codex uses `$impeccable`, while slash-command integrations use `/impeccable` [S22]. Verify the installed integration before using command syntax. Do not claim these tools were installed/run here.

## 2. Information architecture
Public: `/` landing, `/kesfet` search/highlights, `/varlik/[id]`, `/gelisme/[id]`, `/yontem`, privacy/terms. Signed in: `/takip-listem`, `/bildirimler`, `/ayarlar`. Admin: `/admin` and bounded operations subpages. UI route words can be Turkish; internal components/contracts remain English.

## 3. Main screens and acceptance
| Screen | Primary job | Key acceptance conditions |
|---|---|---|
| Landing | Explain value in one screen | `Yatırımlarındaki önemli gelişmeleri kaçırma.`; one real product example labeled simulated if applicable; no fabricated testimonials/accuracy claims. |
| Discover | Find asset or understand major developments | Search keyboard/touch accessible; market/currency disambiguation; clear coverage state. |
| Personal feed | Prioritize followed changes | Two strongest developments, compact remainder; quiet state does not say safe; separate global events. |
| Asset | Understand one asset | Header identity, observation date/lag, chart, event timeline, evidence, contextual question entry. Fund page uses NAV publication language. |
| Event | Verify the warning | Separate importance and evidence strength; source dates, alternative explanations, methodology and feedback. |
| Chat | Investigate without learning a complex terminal | Three plain suggested questions, source links, bounded status, honest failure state. |
| Preferences | Control interruption | Personal/global email toggles, sensitivity, digest, clear unsubscribe; no prechecked marketing consent. |
| Admin | See operational truth | Freshness, jobs, quota/spend, pending releases, versioned settings; no secret values. |

## 4. Interaction flows
Anonymous search → asset page → “Takip listeme ekle” → Google login → return to same asset → follow confirmation. Cancellation returns safely; no fake local login bypass on public deployment.

Event card → evidence detail → source link or “Bu gelişmeyi sor” → asset-scoped chat with event selected. Chat never replaces the event feed. Not-followed global Critical alerts open the exact reviewed event, with a way to disable future global email.

## 5. Visual grammar
Light-first restrained surfaces, near-black text, one functional accent, deliberate separators and a small number of emphasized surfaces. Avoid beige-plus-italic-serif as a new template cliché. A complementary dark theme is later unless the designer can finish both with proper contrast.

Typography must support Turkish İ/ı/Ş/ş/Ğ/ğ/Ü/ü/Ö/ö/Ç/ç. Use a legible licensed system/font choice, tabular numerals, 16px body target, readable labels and controlled line lengths. Do not ship font binaries from this package. Select licensed webfonts separately with designer approval.

Main page: strong event title, two or three metrics, compact narrative, source/action. Confidence is not a glowing gauge. Financial gain/loss color is separate from severity. A falling price can be routine; a green price rise can carry a high-importance event.

## 6. Responsive and accessibility targets
Inspect 390px, 768px and 1440px widths. Keyboard focus visible; dialogs trap and restore focus; charts have accessible summaries/tabular alternatives; no hover-only evidence. Touch targets aim at 44px. Target WCAG 2.2 AA contrast and semantics; run automated checks plus human review, not claim certification [S28]. Respect reduced motion. Chart zoom must not trap mobile page scroll.

Every core component includes loading, empty, partial, stale, unavailable, offline/retry and error states. No endless skeleton while a provider is known down. Maintain stable layout when AI explanations arrive.

## 7. Turkish content dictionary
| Internal concept | Preferred UI | Avoid |
|---|---|---|
| watchlist | Takip listem | My Assets, Portföyüm when quantities are unknown |
| anomaly | Olağandışı hareket / belirgin değişim | Anomali tespit edildi everywhere |
| relative volume | İşlem hacmi olağanın 3,2 katında | Volume spike |
| confidence heuristic | Kanıt gücü: 78/100 | %78 doğruluk / %78 manipülasyon |
| NAV | Fon pay fiyatı | Fonun anlık borsa fiyatı |
| estimated flow | Tahmini net fon akışı; direction-specific giriş/çıkış only after sign validation | Kesin para kaçışı; çıkış for a positive inflow |
| allocation change | Varlık dağılımında değişim | Portföy yöneticisi bugün sattı |
| disclosure | KAP açıklaması | Disclosure |
| on-chain transfer | Zincir üstü transfer | Balina satışı without proof |
| no result | İzlediğimiz verilerde yeni bir uyarı yok. | Güvenli / risk yok |
| insufficient evidence | Bunu doğrulamak için yeterli veri yok. | AI başarısız oldu |
| lag | Veri 15 dakika gecikmeli. | Canlı when delayed |
| synthetic demo | Örnek senaryo — gerçek piyasa olayı değildir. | Historic proof for invented numbers |

Counts and money use `Intl.NumberFormat('tr-TR')`; timestamps use Istanbul but retain exchange-session metadata. Percentage-point difference uses `yüzde puan`, not percent. A 40%→60% weight shift is 20 percentage points, not a 20% relative increase.

## 8. Design quality gate
Designer sets direction → agent implements a single representative screen → screenshot review → Impeccable critique/audit if installed → fix hierarchy/contrast/content → designer approval → reuse patterns. No generate-every-page-first strategy. Use `prompts/DESIGN_REVIEW.md` for the review instructions and record screenshot filenames and issues in `templates/DESIGN_ACCEPTANCE.md`; `tools unavailable` is a valid status, not a fabricated pass.

## v0.5 research continuation
Proposed İzvanta identity, Mineral/Ink direction, alternative palettes and exact opaque color-pair checks are in research/brand_lab. BRAND_PREVIEW.html is a local static design exploration, not the application or a rendered/Impeccable/WCAG acceptance result. Current shared design tokens remain unchanged pending owner/designer selection.

## 2026-10-03 risk review

Comprehension of evidence score, date, unknown/quiet/partial and correction states is untested. Color arithmetic and the logo do not establish accessible or useful UI; see product risks. Current synthesis: reports/RISK_REVIEW.md; register: research/risk_review/RISK_REGISTER.json.
