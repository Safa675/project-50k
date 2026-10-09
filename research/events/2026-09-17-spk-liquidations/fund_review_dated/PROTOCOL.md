# Dated D1 view of the top-100 archive: month-end protocol

Registered on 2026-10-10 (Europe/Istanbul), before any dated output is computed.
Decision: [DEC-026](../../../../docs/decisions/DEC-026-dated-d1-research-view.md).
Scope: private, local archived research under DEC-024 (Turkish funds only).
This protocol neither amends `../fund_review_app/PROTOCOL.md` nor
`../fund_concentration_app/PROTOCOL.md`. Once the first real date index is sealed,
any change needs a new versioned protocol file.

## Already seen before writing this

- `../price_detectors/RESULTS.md` and `results.json`: the window results and the
  eight targets' D1 first-alarm dates. The frozen run computed every window-date D1
  state for all 100 funds in memory and kept per-fund first-alarm and alarm-day
  summaries in its private output under `raw/tefas/price-detectors/`. This protocol
  was written on a machine without that output; whether team members have opened
  it is not recorded.
- The fixed-date view's aggregates at 2026-09-16
  (`docs/notes/top100-fund-app-completion.md`) and the concentration extension's
  coverage (`docs/notes/fund-concentration-app-slice.md`).
- THF's and TP2's KAP report facts (`docs/notes/codex-context-2026-10-07.md`,
  section 6).

The dated view re-displays states that the preregistered run already computed. This
protocol therefore fixes which dates are shown and how they are presented; it does
not produce outcome-blind results. The date grid and the default date were chosen
by people who had read RESULTS.md, so they are justified only by the outcome-free
reasons given with them.

## Universe and inputs

The universe is exactly the 100 codes in `../top100_funds.txt`. Membership is
checked before any fund input is opened. Never list `raw/tefas/prices/` and never
read or compute anything on the other 1,922 downloaded price files.

Phase-1 inputs: `raw/tefas/prices/{CODE}.json` for the 100 codes; the bounded
snapshot projection below; the committed `../price_detectors/results.json`,
`detectors.py` and `PREREGISTRATION.md`. Phase 1 opens nothing under `raw/kap/`.
The phase-2 input is the `bundle.json` of one explicitly named sealed v1 bundle,
read only after phase 1 has finished (see Sealing). No downloads, recalibration or
changes to input bytes.

## Selectable dates

The grid is fixed by rule: for each calendar month from October 2025 to August 2026,
the latest date of the shared calendar in that month, plus the preregistered window
end 2026-09-16. That gives exactly 12 dates.

- The shared calendar is the union of row dates, never values, of the 100 price
  files. Each file is filtered to rows dated on or before 2026-09-16 before the
  union. Rows with a zero or missing price count.
- The window end is event-anchored. `../price_detectors/PREREGISTRATION.md` ends
  the window the day before SPK's order; this protocol inherits that date and does
  not choose it. The dated view labels it "Ön kayıtlı inceleme penceresinin son
  günü; sabit görünümle aynı tarih." and never presents it as a month end.
- The month-end rule is a fixed calendar rule, small enough for a native select and
  for verifying 12 sealed bundles, and it keeps 2026-09-16 as the anchor of the
  equivalence audit. No date is added, dropped or moved for any alarm, publication,
  outcome or coverage reason.
- The runner derives the grid once and seals it in the date index. All later code
  (assembly, loaders, API, browser) takes the grid from that index. The grid is
  ex-post calendar knowledge from the 2026-10-07 retrieval: value-free and
  outcome-free. On a weekday calendar the expected dates are 2025-10-31, 2025-11-28,
  2025-12-31, 2026-01-30, 2026-02-27, 2026-03-31, 2026-04-30, 2026-06-30,
  2026-07-31 and 2026-08-31; the May 2026 date depends on the holidays in the
  archive calendar. The runner reports the derived grid and refuses unless it has
  exactly 12 dates ending at 2026-09-16.
- The default date is 2026-09-16, fixed here because it is the fixed view's date.

## Range and temporal threshold bound

Every cutoff lies in [2025-10-06, 2026-09-16]; anything else is refused before any
input is opened. The stored D1 thresholds are 99th percentiles of values dated
before 2025-10-06 (`PREREGISTRATION.md`, "Thresholds"). An earlier cutoff would use
thresholds built partly from later data; a later cutoff enters the order day.

This bound is temporal only. The thresholds were pooled over the October 2026
universe and its 2026-10-06 categories, which include the evaluated funds and the
eight targets. Every dated bundle states this.

## Cutoff semantics

Date d maps to `cutoff_at = dT23:59:59+03:00` (a fixed offset, no time-zone
database) and an explicit `cutoff_date = d`. d is a TEFAS row-label date: rows
dated on or before d enter. TEFAS dates a price about one business day after its
valuation, and same-day availability rests on a single observation. Comparisons use
complete `YYYY-MM-DD` dates or parsed instants, never a `YYYY-MM` string against a
date.

## D1 at each date

Use only the frozen `detectors.py` functions `log_returns`, `peer_median` and
`excess_level` on the shared calendar truncated at d: the last 60 calendar positions
up to d, at least 50 usable excess observations, at least 10 peers on each
contributing date, at least 11 selected category members, a finite stored threshold,
and a crossing only when the statistic is strictly above that threshold. No
recalibration, sensitivity thresholds or D2-D5.

Freshness is FRESH only when the latest contributing excess observation is dated d.
Otherwise it is STALE (`final_contributing_observation_before_cutoff`): the
statistic is kept but not eligible. Every grid date is a calendar date, so weekends
and holidays never cause staleness.

Row integrity follows v1: a structurally invalid row or a non-canonical date
anywhere in a file makes that fund unavailable at every date. Rows dated after d are
skipped before the duplicate check, so a duplicated date affects only cutoffs on or
after it. A dated statistic equals the frozen value at d's calendar index only when
every fund's validity is the same at d and at the reference date.

## Names and categories

Names and categories come from the 100 funds' snapshot rows whose offset-aware
`retrieved_at` is at or before results.json `run_at_utc`
(2026-10-07T08:52:12.470547+00:00), taking the newest such row per fund. A missing,
unparseable or offset-free `retrieved_at` refuses. The bound is assumed to reproduce
the categories behind the stored thresholds. At sealing, the eight targets' bounded
categories must equal their `results.json` categories, or sealing refuses.

These snapshots postdate the order. Each bundle records the bound and the latest
`retrieved_at` it used, and the view says "Ad ve kategoriler: {that date} anlık
görüntüsü." Rows appended after the bound never change a dated bundle; edited or
backdated rows before it make loading refuse.

## Records, comments and order

All 100 codes are records at every date, and no launch date is claimed. Each record
carries `has_positive_price_on_or_before_cutoff`, derived only from rows dated on or
before d, and the summary counts `no_price_at_cutoff`. Dated bundles contain no
estimated flow, no concentration and no KAP source. The view says "Bu tarih
görünümünde hesaplanmadı." and links to the fixed view with "Sabit 16 Eylül 2026
görünümüne geç (farklı tarih)".

Deterministic D1-only Turkish templates refer to "seçilen tarih". They contain no
month name, fixed date, fraud, safety, causality, prediction or advice wording.
Order: eligible crossing; not eligible (stale or unavailable); eligible no crossing;
then fund code. Summary: eligible crossing + eligible no crossing + stale +
unavailable = 100, and `no_price_at_cutoff` is at most unavailable.

Exact sentences:

- Guard, on every dated screen: "Her tarih ayrı bir arşiv kesitidir. Bu görünüm, o
  tarihte bir uyarı verildiğini ya da sonucun önceden bilinebileceğini göstermez."
- With every no-crossing comment: "Eşiğin aşılmaması bir güvenlik değerlendirmesi
  değildir."
- Survivorship, on the list: "Fon listesi Ekim 2026 yatırımcı sayılarına göre
  seçildi. Daha önceki tarihlerde henüz fiyatı olmayan ya da sonradan kapanan
  fonlar bu görünümde doğru temsil edilmeyebilir."
- "Neden yalnızca bu tarihler?": "Tarihler önceden belirlenmiş bir kurala göre
  seçildi: Ekim 2025–Ağustos 2026 arasında her ayın son TEFAS fiyat tarihi ve ön
  kayıtlı inceleme penceresinin son günü. Eşikler 6 Ekim 2025 öncesi verilerle
  hesaplandığı için daha önceki tarihler gösterilmez."

Denylist, checked over every other new Python template and UI string and over the
rendered text of every dated state: "erken uyarı", "ilk eşik aşımı", "gün önce",
"ay önce", "önceden", "tahmin", "öngör", "risk yok", "güvenli", "tasfiye", "SPK",
"dolandırıcılık". No date after the selected date may appear, except in the date
selector's options and the fixed-view link sentence. Only the exact sentences above
are exempt from the denylist.

No bundle, index, response, page or comment contains a cross-date view: no
ever-crossed flag, first-crossing date, per-fund timeline, counts across dates,
days-before-order figure, lead time, hit or false-alarm rate, step links or autoplay.
Each date shows only its own denominators. Outcome labels and the liquidation list
are never inputs. Committed files name only the eight targets.

## Labels and provenance

Every dated response keeps origin `HISTORICAL_REPLAY`, analysis_mode
`EXPLORATORY_ARCHIVE`, cutoff_semantics `RECORDED_SOURCE_DATE_FILTER`,
point_in_time_verified false, historical_availability and rights_status `UNKNOWN`,
universe_basis `OCTOBER_2026_INVESTOR_SNAPSHOT` and category_basis
`CURRENT_SNAPSHOT`. It adds `cutoff_date`, knowledge_basis
`RECORDED_SOURCE_DATE_RECONSTRUCTION`, findings_scope `D1_ONLY`, date rule
`MONTH_END_PLUS_WINDOW_END_V1`, the index ID and the bundle ID. Production status
stays `ABSTAINED`. The strict ReplayCursor is unchanged and unused.

Every bundle carries threshold provenance: calibration end (exclusive) 2025-10-06,
percentile 99, crossing STRICTLY_ABOVE, the calibration `run_at_utc`, the SHA-256 of
the committed results.json, of its D1 threshold map, of detectors.py and of
PREREGISTRATION.md, calibration universe basis `OCTOBER_2026_INVESTOR_SNAPSHOT`,
calibration category basis "2026-10-06 snapshot", and the statement that the
thresholds were computed over a post-event universe that includes the evaluated
funds. Loading rejects any digest mismatch, any record threshold that differs from
results.json and any cutoff before the calibration end.

## Registration and sealing

This protocol is committed alone, before any dated runtime commit and before any
real run. The runner then refuses unless:

1. No registered text file contains CRLF; the refusal names the file.
2. Working bytes equal `git show HEAD:` for this protocol, the dated runner and
   modules, the imported v1 runtime (`services/p50k/research_reviews/__init__.py`,
   `contracts.py`, `bundle.py`, `comments.py`, `services/p50k/detectors/fund_flow.py`,
   `evidence_store.py`, `replay.py`), `detectors.py`, `PREREGISTRATION.md`,
   `results.json` and `top100_funds.txt`.
3. results.json `detectors_sha256` and `preregistration_sha256` equal the digests
   of the committed blobs.
4. No sealed index in the canonical output records a different protocol SHA-256.

Phase 1 opens no KAP file and no v1 bundle. It reads the 100 price files and the
bounded snapshot, derives the grid, assembles the 12 payloads in memory and records
their canonical digests.

Phase 2 reads only the `bundle.json` of the v1 bundle named with `--v1-bundle`,
which `ops/local/run_app.py --check` verifies beforehand. At 2026-09-16 the dated
payload must equal it for every fund on the d1 object without input_refs, the chart,
the name and the category, and on input_refs mapped to (kind, fund code, sha256)
for PRICE, UNIVERSE and CALIBRATION sources. Any difference refuses: nothing is
written and only field names are reported. The phase-1 digests must be unchanged
after phase 2.

Then the runner writes 12 content-addressed bundles under
`raw/research/fund-review-dated/bundles/<fingerprint>/` and one index under
`raw/research/fund-review-dated/index/<fingerprint>/`, atomically and never
overwriting. The index binds the 12 (date, cutoff_at, bundle ID) entries in order,
the default date, the protocol SHA-256 and commit, the calendar digest, threshold
provenance, the snapshot bound and digest, and the audit result. Identical runs
reuse identical bytes. Any independent recomputation of sealed values is a
committed audit mode of the same runner under the same guards, writing only
pass/fail with field names.

## Serving and isolation

A separate loopback API process serves only GET `/research-dated/v1/dates` and
`/research-dated/v1/dates/{date}/summary`, `/funds` and `/funds/{code}`. The date is
checked by format, then by index membership, and the code against the universe,
before any bundle is loaded. A `bundle` parameter that differs from the index entry
returns 409. Error provenance is built per request. No route computes anything,
substitutes a nearest date or serves source files. The launcher takes the exact
index directory, never the newest; its check verifies the index, every bundle, the
response contract for every date and that the protocol commit is an ancestor of
HEAD. The browser fetches dated data only on the client, through a GET-only
same-origin proxy route.

No existing tracked file changes, except append-only sections in
`ops/local/README.md`, `ops/systemd/README.md`, `CLAUDE.md` and `AGENTS.md`. The
fixed-date app, its API and launcher, the sealed v1/v2 bundles and the existing
tests stay byte-identical. Merge with a merge commit, never a squash, so this
protocol's commit stays in main's history.

## Design review

The date control and every state are first shown on a labelled synthetic
`/preview/dates` page for owner review. The control is a labelled native select of
the sealed dates with an explicit "Tarihi göster" button, on the list page only.
That review approves the layout only; G09 stays open. Keyboard use, 390/768/1440 px
widths, contrast and Turkish wording are checked and recorded with it.

## Verification fixed before calculation

Before the first real run, these synthetic tests pass:

- grid derivation, and range and format refusal before any read;
- dated D1 at 2026-09-16 equal to v1, and the statistic equal to the frozen value at
  the cutoff's calendar index when validity is the same;
- later rows, outcome keys and later grid dates never change an earlier date's
  records with the grid held fixed, and they do change the later date;
- freshness against the selected date, unpriced funds kept, row integrity;
- threshold provenance enforced on load, and the snapshot bound;
- comments, order, summary and denylist;
- index and bundle tampering, and loaders rejecting each other's bundles;
- runner refusals, read scope and the two-phase audit;
- API date validation, 409 and per-request errors, with the fixed-date API
  unchanged, and the launcher checks;
- client contract, loaders, proxy and copy; browser states with date-keyed mocks;
  fixed-view labels unchanged;
- the existing root, frozen and frontend suites.

## Non-claims

This is a partial research contribution only. There is no completion of
FR-108/109/110, UR-078/079/080 or NFR-080, and no prediction, accuracy, lead time
or "would have caught" claim. G01, G03, G09 and G10 stay open, and all 284
requirement statuses stay NOT_IMPLEMENTED. No download, deployment, notification,
account, spending or public exposure is part of this work.
