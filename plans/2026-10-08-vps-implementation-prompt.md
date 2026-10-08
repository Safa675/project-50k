# VPS session prompt: implement the top-100 fund research app

Copy the prompt below into the new VPS session. Run it in the Project-50K
repository checkout. Machine-specific laptop paths in the plan are references,
not paths to assume exist on the VPS.

---

Implement the first Project-50K fund research app on this VPS, following
`plans/2026-10-08-top100-fund-research-app.md`.

This is my authorization to implement the plan in small verified slices and make
local commits. The plan's earlier "planning only" status describes the preceding
session; do not ask me to authorize implementation again solely because of that
old status. Preserve the unresolved design gate: produce a concrete scaffold or
wireframe with the required states for review before full UI implementation, and
continue independent data/backend work while that review is pending. Do not
pretend designer approval, data rights or competition eligibility are cleared.

Reply to me in simple Turkish. Keep code, documentation, commits and technical
prompts in English. Do not modify the Bilun repository or copy its health data.

## 1. Verify the checkout and read the instructions

- Locate the actual Project-50K checkout and inspect its branch, HEAD, remotes
  and working tree. Preserve existing user changes; no destructive reset.
- The required baseline is commit
  `81bdfe8bed2fd217d62dcfdd1d8452b2cf19f012` or a descendant, on the source branch
  `codex/thf-holdings-divergence`. It contains the app plan and market brief.
  Verify the commit and plan are present. If the branch has not been transferred
  or pushed, report that prerequisite rather than recreate the missing history.
- Work on a `codex/` implementation branch based on the verified baseline.
- Read `AGENTS.md`, `docs/notes/codex-context-2026-10-07.md`, the app plan,
  `docs/handoff-v0.5/AGENTS.md`, `DESIGN.md`, the relevant requirements and anomaly
  catalog, and the provider report required by the repository instructions.
- Read `docs/notes/evidence-store-replay-slice.md`,
  `docs/notes/fund-flow-research-slice.md` and the frozen price-detector
  preregistration/results. The market brief is historical background, not
  authority to add auth, AI chat, email, public release or additional markets.
- Run the three existing regression suites using a verified compatible Python
  interpreter on this VPS; do not assume the laptop's Miniforge path. Report
  exact commands, counts, failures and environment limitations. Do not claim a
  missing dependency is a passing test.

## 2. Inventory prerequisites without replacing history

A Git clone does not include the private raw archive or snapshot database.
Verify availability and provenance of:

- `research/events/2026-09-17-spk-liquidations/top100_funds.txt`.
- The selected funds' `raw/tefas/prices/`, `raw/kap/series/` and original
  `raw/kap/reports/` files, including report lists and acquisition metadata.
- The original fund snapshot SQLite database or an exact validated private
  export for selected fund names/categories. Its laptop location was
  `~/.local/share/project-50k/fund_snapshots.sqlite3`; locate the VPS equivalent.
- The committed original D1 thresholds in
  `research/events/2026-09-17-spk-liquidations/price_detectors/results.json`.
  Do not run the frozen price-detector runner to recalibrate or overwrite them.
- A Bilun source checkout containing commit
  `cafa27bc9d7f6fe4c6a75f1eaea431fed90e2f52`, applicable notices and `LICENSE`.
  Find the actual VPS path; do not assume `/home/safa/Documents/Bilun`.

Missing private data or source code is a transfer prerequisite. List exactly
what is missing and continue with contracts, synthetic tests and the scaffold
where possible. Do not fabricate prices, categories, dated publications or
real results. Do not silently substitute current downloads, reuse Bilun health
datasets, inspect unopened funds or perform a new broad data acquisition.
No private data or database enters Git.

## 3. Build the agreed first prototype

- All **100 selected funds** appear, including unavailable records.
- Fixed nominal cutoff: `2026-09-16T23:59:59+03:00`, Europe/Istanbul.
- Two screens: searchable/filterable fund list and fund detail with metrics,
  charts, deterministic Turkish comments and source evidence.
- The date selector is a later slice. Do not promise arbitrary dates here.
- Preserve D1's frozen formula, stored thresholds and minimum coverage. Its
  lookback is 60 positions in the shared TEFAS date calendar, not 60 consecutive
  calendar days. Calculate the cutoff-date state, not an annual ever-fired flag.
- Use only the July-to-August 2026 monthly pair for flow context, subject to the
  recorded publication cutoff and the plan's comparability/missing rules.
- Keep D1 and signed estimated flow separate. Use the plan's freshness gate for
  the descriptive two-finding comment. No new fraud probability or target tuning.
- Comments are template-derived from inspectable metrics and reasons. Unknown
  or stale input must not become "normal", "safe", zero return or invented cash.
- Commit the new joining protocol **before** any new real joined calculation.

Follow P0 through P5 in the plan with source/code hashes, synthetic acceptance
tests and review of each slice. Use self-review for ordinary verified data/API
work; ask me only for genuinely required missing information or a concrete
design approval, not repeated implementation permission.

## 4. Keep the research and production boundaries intact

Use the separate internal `/research/v1` contract. Keep `ReplayCursor` and
production detector admission unchanged. Real production decisions remain
`ABSTAINED`; archive screen crossings are not public `TRIGGERED` events.

Every response retains `origin: HISTORICAL_REPLAY`,
`analysis_mode: EXPLORATORY_ARCHIVE`, `point_in_time_verified: false`,
`historical_availability: UNKNOWN`, `rights_status: UNKNOWN`, the immutable
bundle ID, fixed cutoff and recorded-source-date filtering semantics.
Disclose the retrospective universe and category snapshot basis.

Recorded publication filtering does not verify historical source versions.
Do not admit unknown availability into strict replay, claim real pre-crisis
alerts, infer fraud labels from liquidation membership, or report fraud accuracy.
Future prices/reports/outcome labels must not affect cutoff metrics or comments.
Known unsupported actions disable the flow finding; unknown action evidence
remains visibly conditional rather than verified.

## 5. Reuse only the approved Bilun building blocks

Use the generic DataTable, Toolbar, Chip, Stat, EmptyState, form styles and cn
helper, with only their required tokens/CSS. Adapt the narrow JSON transport and
same-origin API proxy patterns. Validate response shapes at runtime.

Build a new thin FastAPI/Pydantic API around Project-50K data and a new
Next.js/TypeScript/Tailwind/next-intl frontend. Use the handoff's Lightweight
Charts choice for fund/peer time-series charts.

Do not transplant Bilun's app/startup, caches, credentials, auth exceptions,
patient routes, full sidebar/layout, domain translations or whole lockfile.
Preserve authorship/notices. Resolve compatible supported dependencies from
official documentation and create fresh project lockfiles; do not assume the
source machine's installed packages match its manifests.

## 6. VPS execution is private development, not deployment

Bind frontend and API to loopback. Serve the private research bundle through
validated fund codes and opaque manifest-backed source IDs. Reject arbitrary
paths/URLs and traversal. Keep private responses out of shared/static caches and
tracked build assets. Document a private access method if browser review needs
an SSH tunnel; do not invent the host, port or expose a public listener.

This prompt does not authorize accounts, spending, public/LAN hosting, firewall
changes, reverse-proxy changes, systemd installation, production auth bypass,
external notifications, real-data publication, repository push or merge.
Use isolated development ports; preserve unrelated running VPS services.

## 7. Verify the actual result and hand it back

Run the plan's synthetic arithmetic, joining, future-invariance, bundle integrity,
API and browser checks. Verify all 100 records, filters/detail navigation,
missing states, chart gaps, source access, Turkish copy, keyboard/mobile behavior
and that displayed numbers match the selected immutable bundle.

Run relevant Python regressions plus the locked frontend typecheck, tests and
build. Report actual commands/results; distinguish SDK/static probes from real
browser rendering. Check frozen-file hashes, staged source values and secrets
before every local commit. No real financial values in fixtures, docs or Git.

At completion provide changed files, partial requirement coverage, local commits,
exact verification evidence, local startup/private access instructions, data
mode/rights, missing prerequisites and limitations. Do not declare the app done
while only synthetic scaffolding exists or private data is unavailable.
The first deliverable is the fixed-date 100-fund list and evidence detail; the
next proposed slice is the date selector after this result is reviewed.
