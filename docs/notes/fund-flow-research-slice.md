# B1: conditional fund-flow arithmetic and private archive screen

Owner approved implementation and named local findings on 2026-10-08.
Scope: DEC-024, Turkish investment funds, only the already opened top-100 universe.
The protocol was locally committed before the new real-data calculation:
`867ed8c370c87c49cd13930191a46a4d0ac410a8`, SHA-256
`a395bddd00c26ab74d6bfe51da49aba9cab900bd7b4f6ff28753c3c555cea9e6`.

## Resulting behavior and requirement coverage

**FR-037 (partial), AN-FND-002:** calculate the return-adjusted endpoint residual
`A1 - A0*(P1/P0)` and its opening-asset ratio with deterministic Decimal arithmetic.
Missing/nonfinite numbers, invalid asset signs and nonpositive NAV produce no
metric. The amount is not reported investor cash. The fixed absolute 10% catalog
heuristic is conditional on eligible evidence and an explicit baseline record.

**NFR-038 (partial):** production evaluation reads only an immutable ReplayCursor.
Unknown/future availability, incompatible scope/units/actions/rights, ambiguous
revisions or an unverified baseline return ABSTAINED without numeric metrics or
future evidence IDs. A later eligible history revision cannot rewrite the baseline
used for an earlier check. Tests use synthetic evidence only.

The research runner separately computes labeled exploratory archive arithmetic
on the existing selected KAP files. Its 10% screen is not a production TRIGGERED
decision. Every real pair retains ABSTAINED and unresolved financial assumptions.
It does not relax the cursor, admit unverified KAP versions, create FR-064 events,
train a model or change any frozen requirement status.

## Changed files

- `services/p50k/detectors/__init__.py` and `fund_flow.py`: pure arithmetic and
  provenance-bound production admission.
- `tests/unit/test_fund_flow.py`: arithmetic, dimensional/action/rights guards,
  baseline version binding and future-invariance regressions.
- `research/events/2026-09-17-spk-liquidations/fund_flows/PROTOCOL.md`: the fixed
  monthly window, universe, threshold, count/ranking rules and interpretation.
- Its `run.py`: committed-input/code checks, selected-source reads, record
  pointers/hashes, signed summaries and immutable private output.
- `tests/unit/test_fund_flow_research.py`: synthetic runner integration, strict
  input selection, gaps/duplicates/latest-period missingness, precision and output
  preservation.
- This note: implementation boundary and executed verification.

## Production input and baseline contract

The two stored observations contain Decimal `total_value` and `nav`, with units
matching the explicit currency and currency-per-unit. Required attributes include
matching fund scope, share class, currency and valuation timezone; consecutive
monthly periods; net assets and raw transaction NAV; field valuation instants
equal to the row's month-end instant; and `VERIFIED_NONE` distribution, unit-change
and merger status. Actual corporate-action adjustments are not implemented.
Both source timing and rights must be admitted. Current imported KAP data lacks
these guarantees and is excluded from production replay.

`BaselineCheck` defaults to UNVERIFIED. A passed declaration needs a configuration
ID and eligible stored check keys. Each check carries `baseline_status`,
`baseline_config_id`, `baseline_input_keys` and exact `baseline_input_versions`.
Check creation is no later than the opening valuation instant; check/history
effective times precede it. History versions must be available in a separate
ReplayCursor at the check's creation time and match the recorded version map.
This is structural evidence admission, not an implementation or empirical
validation of the still-undefined historical baseline policy. No generic sample
minimum is invented.

## Local research execution

From the repository root, after the runner and its dependencies are committed:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services /home/safa/miniforge3/bin/python3 research/events/2026-09-17-spk-liquidations/fund_flows/run.py --protocol-sha256 a395bddd00c26ab74d6bfe51da49aba9cab900bd7b4f6ff28753c3c555cea9e6
```

Monthly closing periods are October 2025 through September 2026; September 2025
can only provide the first opening endpoint. Actual consecutive reports are used;
gaps, weekly periods and duplicate monthly endpoints are not silently resolved.
Latest reported month, latest valid earlier pair and historical peak are distinct.
The through-August subset is a nominal-period view, not historical alert evidence.

The output is under `raw/kap/flow-analysis/{fingerprint}/results.json`, Git-ignored.
It embeds exact code/protocol/source hashes and per-record references. An identical
rerun reuses its original output; foreign/conflicting files and input aliases are
refused. Input JSON, provider caches and external SQLite files are not modified.
No raw input or named non-target result is committed. The owner's private result
view may show all selected codes and their research screen values.

## Verification record

The three regression commands are:

```sh
# Repository root
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services /home/safa/miniforge3/bin/python3 -m unittest discover -s tests -t . -v
# research/events/2026-09-17-spk-liquidations/price_detectors
PYTHONDONTWRITEBYTECODE=1 /home/safa/miniforge3/bin/python3 -m unittest test_detectors -v
# docs/handoff-v0.5
PYTHONDONTWRITEBYTECODE=1 /home/safa/miniforge3/bin/python3 -m unittest discover -s tests -v
```

Executed on 2026-10-08 with exit status 0 for each command:

- Repository suite: `Ran 196 tests in 1.616s`, `OK`.
- Existing price-detector suite: `Ran 9 tests in 0.436s`, `OK`.
- Frozen handoff reference suite: `Ran 88 tests in 0.004s`, `OK`.
- Total: 293 passing tests, including 67 new detector and runner tests.

The real runner command above was executed twice after code commit
`ef2e9f8a23a6acf257040dc80c12e8cfbe30d393`. Both runs exited 0, returned
fingerprint `82ba645c95d67010cee517e96f8c2071dbd13269129754f277353181e80753dd`,
and reused the same byte-identical private result with its original metadata.

Of 100 selected funds, 98 had source files and calculable monthly pairs. There
were 1,099 pair attempts: 1,046 valid calculations and 53 noncomputable attempts
(51 missing previous months and two missing-value pairs). The latest reported
monthly pair crossed the fixed absolute 10% screen in 30 of 98 funds: six of
eight known liquidation-list targets and 24 of 90 other selected funds. Across
any month in the fixed window, 75 of 98 crossed: eight of eight targets and
67 of 90 others. The broad crossing frequency does not establish selectivity,
accuracy or a false-positive rate. All real production decisions remain
`ABSTAINED`; these are private exploratory screen findings.

Independent exact-fraction recalculation confirmed every valid ratio and
threshold decision. A separate review verified all 98 source-file hashes,
2,147 endpoint report references, summary counts and both rankings without a
discrepancy. The 98 consumed KAP JSON files and two external database files
matched their before-run hashes and sizes. All 3,906 original archive files
also matched the migration audit; unopened price files were hashed only.
All 216 frozen manifest entries matched, and the frozen price detector files
matched `origin/main`. New Python modules compiled and `git diff --check` passed.

The original six PDF reports for three selected high-crossing pairs were checked
read-only. All 12 endpoint asset/NAV values matched the extracted inputs exactly;
disclosure IDs matched the PDF filenames. Independent Decimal calculation
reproduced all three residuals and rates exactly. This rules out a parser label
or decimal-separator mismatch in these inputs, but does not establish accounting
validity or misconduct. Dividend tables for securities held by a fund are not
proof of distributions to fund holders; merger/unit-action status remains unknown.

A private Turkish review canvas lives outside Git. Its strict TypeScript check
and in-memory JSX smoke check exited 0; all 100 funds and 1,099 pair values and
classifications matched the result. App rendering and visual layout were not
verified. No runtime trading, external alerts, live feed or validated historical
baseline policy was tested or enabled.
The canvas smoke command was `/home/safa/.local/bin/node
/tmp/p50k-fund-flow-canvas-smoke.cjs`; it used SDK stubs rather than a host render.

## Limits and next task

Origins remain HISTORICAL_REPLAY for real source files and SYNTHETIC for explicit
test fixtures; the calculation view is EXPLORATORY_ARCHIVE. Provider rights are
UNKNOWN. Currency/scope/action comparability and archive availability are not
established by a numeric screen crossing. A below-threshold or unavailable result
does not mean safe. The eight known targets are liquidation-list membership,
not fraud labels; other funds are not known-clean controls.

No detector accuracy, real cash flow, current fund safety or pre-order detection
claim follows. The next useful research task is to inspect the largest crossings
against the original reports and distinguish ordinary fund lifecycle changes from
unexplained changes, then specify a baseline policy without opening the holdout.
