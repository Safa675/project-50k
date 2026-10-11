# DEC-036 — Admit the official Borsa İstanbul daily equity bulletin as a stock source

**Date:** 2026-10-11 (Europe/Istanbul)
**Source:** Mirza asked "where is stock data?" for the 12 September view and approved downloading the official daily
bulletins for 1 August to 9 October 2026 (relayed through the build workflow). Earlier context: the 2026-10-10 resume
handoff ("New official stock-source discovery") and DEC-025 (Borsa İstanbul data-distribution terms).

## Why

The only stock source so far is ForInvest v1: 30 current BIST 30 members and 870 daily closes, captured on
2026-10-10 15:34:41 UTC. Its availability is the capture time, so the 12 September view correctly shows no stock
prices. Borsa İstanbul publishes a daily equity bulletin at a fixed public path; the server's `Last-Modified` header
dates each file. That gives dated closes and a dated BIST 30 membership without backdating anything.

## Decision

- **Source.** `https://borsaistanbul.com/data/thb/YYYY/MM/thbYYYYMMDDS.zip`, session `S = 1` only. Registered as
  `source_id = 'borsaistanbul-thb'`, `source_version = 'thb-v1'`, label "Borsa İstanbul günlük bülteni".
- **Admitted per bulletin.** Only the rows whose `BIST 30 INDEX` column is `1` on that trade date: they are the dated
  BIST 30 membership of that day. For each row: trade date (`TRADE DATE`), symbol (`INSTRUMENT SERIES CODE` without the
  `.E` suffix), name (`INSTRUMENT NAME`), closing price (`CLOSING PRICE`), previous close (`PREVIOUS LAST PRICE`),
  the bulletin's own change (`CHANGE TO PREVIOUS CLOSING (%)`), shares traded (`TOTAL TRADED VOLUME`), traded value in
  TRY (`TOTAL TRADED VALUE`), `VWAP`, `SUSPENDED` and `CORPORATE ACTION`. Column names are checked against the English
  header row of each CSV. Other rows of the bulletin are not admitted.
- **Validation (fail closed per file).** The ZIP holds exactly one CSV named like the ZIP; every row's trade date equals
  the file-name date; exactly 30 distinct equity rows (`EQT`) carry the BIST 30 flag; every flagged close is decimal
  text; the file's SHA-256 equals the capture record. A zero close is stored as missing, never as a price.
- **Availability.** The publisher's HTTP `Last-Modified`, captured at download, is the availability time. It is
  evidence of when the file was on the server, not proof of first publication. The archive's inner CSV timestamp is a
  consistency check: it must fall on the trade date and no later than `Last-Modified` plus ten minutes. When the
  header is absent or unparsable, falls before the trade date, lies after the capture, or fails the consistency
  check, the capture time is used instead (rule `thb_capture_time_fallback`). Nothing is ever dated earlier than the
  evidence allows.
- **Origin and prices.** Origin `DELAYED`, the same as dated TEFAS rows. Closes are the exchange's unadjusted closes
  (`price_adjustment = 'UNADJUSTED'`); no split or dividend adjustment is applied.
- **Instruments.** A dated member that is missing from `ref.stock_instruments` is inserted with the bulletin's symbol
  and name and marked `dated_bulletin_member`. Existing instrument rows (ForInvest names) are never overwritten. An
  instrument row alone never enters the current catalog: the current list stays the ForInvest catalog.
- **Views.** The 12 September (and any retrospective) view lists the latest bulletin available at its cutoff, labelled
  as membership on that trade date, not today's list. The live view keeps the ForInvest current catalog. Where both
  sources have a close for the same day, the official bulletin is preferred and every value names its source.
- **ForInvest v1 is kept as is.** No row is rewritten, re-dated or deleted; there is no backfill of earlier
  availability for any source.
- **Rights.** Data rights are not reviewed (`rights_status = 'UNREVIEWED'`). Local product use only; no publication or
  redistribution. DEC-025 records that Borsa İstanbul requires a Data Distribution Agreement for redistribution and
  non-display use. Bulletin files stay outside git under `~/.local/share/project-50k/`; tests use synthetic files.

## Effect

`services/p50k/product/stock_bulletin.py` imports one bulletin (`--zip` and `--capture-json`) or a downloaded folder
with its `manifest.json` (`--folder`); re-runs insert nothing new. No migration is needed: the bulletin uses the
existing `obs.stock_prices` and `ref.stock_instruments` tables and registers itself in `ref.sources`.
