# BIST 30 daily stock data, v1 — 2026-10-10

Recorded before product ingestion. Mirza requires stocks in the hackathon demo
and confirmed BIST 30 as the initial stock universe. DEC-032 sets the B2B
evidence-data/API product direction. This protocol is immutable after commit.

## Scope and source

- Current XU030 membership from the connected ForInvest symbol search. Membership
  is a current catalog snapshot; it is not historical index membership.
- Daily BIST equity candles, 2026-09-01 through 2026-10-09 inclusive. Only raw
  daily responses are eligible. Adaptive/weekly summaries are not daily bars and
  must be rejected. This initial slice uses the returned close in TRY; it does
  not present fund NAV or intraday observations as stock closing prices.
- Public company identity and observed corporate-action records from the same
  connection. A qualified symbol ending `.E.BIST` is normalized only when its
  exchange is explicitly BIST and the resulting code is in the captured catalog.
- Captures are exact saved MCP structured-response payloads, not original HTTP
  bodies. Their SHA-256 references must say so. Raw connector captures and
  normalized manifests remain outside git. Every selected file is hash-verified.

## Availability and missingness

All observations are admitted at the capture-completion time. Effective dates
do not establish historical publication or availability. Historical charts are
observations acquired now, with acquisition provenance; no replay claims that
the system knew these values in September. Cutoffs require a timezone and may
not be in the future. Queries exclude observations acquired after the cutoff.

Close values use Decimal strings, positive values only; source zero/null stays
unknown. No zero filling, synthetic daily rows, gap interpolation or invented
trading sessions. Tied conflicting revisions stay unknown. Later revisions are
append-only and do not replace the original observations or source references.

## Corporate actions and interpretation

Price-adjustment semantics are UNVERIFIED. Observed action records are retained
as source records, with capture availability. The v1 product does not infer
adjustment ratios, apply split/dividend arithmetic or classify raw price changes
as anomalies. Absence of a record is not evidence of full event coverage.

This is the stock data/API/chart slice. It has no stock anomaly threshold or
LLM stock materiality decision. A future stock detector requires a new versioned
protocol and its own tests; fund thresholds, categories and calibrated peer
universe must never be silently transferred to equities. Existing fund case
study detectors and all committed protocols remain unchanged.

## Product and verification

Protected catalog, daily chart, corporate-action evidence and source metadata
are exposed by bounded read-only API queries under existing session auth.
The UI labels current membership, daily close, unknown adjustment semantics,
DELAYED data and UNREVIEWED rights. There is no placeholder stock AI output.

Tests use synthetic data: source/hash mismatch, catalog membership, zero/null,
aware cutoffs, lookahead exclusion, conflicting revisions, append-only storage,
query bounds and authenticated browser flow. Real verification reconciles
catalog and input-row counts and verifies repeated imports are idempotent.

The selected data source supports local research use here; commercial
redistribution rights remain unreviewed. No trading, investment advice, fraud,
predictive accuracy or historical lead-time claim is authorized by this slice.
