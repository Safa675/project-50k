# Price-only detectors on the top 100 funds: pre-registration

Written on 2026-10-07 and committed before any of these detectors was run. Every threshold comes from data dated before the evaluation window, by the rules below. Nothing is tuned on the liquidated funds.

## Question

Do price-only detectors flag the liquidated funds among the top 100 before SPK's order of 17 September 2026? How often do they flag the other funds?

## Already seen before writing this

- THF's and TP2's prices (`../NOTES.md`, stage 1), including TP2's excess over seven money-market funds widening in autumn 2025.
- THF's and TP2's KAP reports (units outstanding and size).

THF and TP2 are therefore not independent evidence for D1, D2 or D5. The other six targets (TLY, DFI, DOH, PRY, KHA, PNU) have not been looked at.

## Data

- **Universe:** `../top100_funds.txt`, the 100 funds with the most investors in the 2026-10-06 TEFAS snapshots.
- **Targets:** the 8 universe funds in SPK's list: THF, TP2, TLY, DFI, DOH, PRY, KHA, PNU.
- **Prices:** TEFAS `fonFiyatBilgiGetir` with periyod 60 (the 5-year maximum), retrieved on 2026-10-07 and kept in `../raw/prices/` (gitignored). A missing or zero price counts as no price.
- **Category:** TEFAS `fonKategori` in the 2026-10-06 snapshots. This is today's category, not a dated one; see Limits.
- **Availability:** a row dated d is used from day d on, because TEFAS publishes it on d by about 11:05.

## Definitions

- **Calendar:** every date in any fund's rows. All 100 funds share one calendar of 1,258 business days.
- **Return:** r(d) = ln(P(d) / P(d−1)), where d−1 is the previous calendar date. It is defined only when both prices exist.
- **Peer median:** m(d) for a fund is the median of r(d) over the other universe funds in its category that have a return on d. It is defined only with at least 10 such peers, as in catalog AN-FND-001.
- **Excess:** e(d) = r(d) − m(d).
- **Windows:** a window counts calendar dates up to and including d. Nothing after d is used.

| ID | Idea | Statistic on date d | Needs | Alarm when |
|---|---|---|---|---|
| D1 | Persistent excess return | Median of e over the last 60 dates | ≥ 50 values | Above the category's 99th percentile |
| D2 | Change in excess return | Median of e over the last 60 dates, minus the median of e over the 120 dates before them | ≥ 50 and ≥ 100 values | Above the category's 99th percentile |
| D3 | Too smooth: returns follow themselves | Lag-1 autocorrelation of r over the last 120 dates | ≥ 100 pairs | Above the category's 99th percentile |
| D4 | Too smooth: does not move with peers | Correlation of r with m over the last 120 dates | ≥ 100 pairs | Below the category's 1st percentile |
| D5 | Young fund | Days since the fund's first price | A first price | Under 730 days |

D1 to D3 are one-sided because the hypothesis is returns that are too good or too smooth, not poor returns.

**Thresholds:**
- For each detector and category, the threshold is the stated percentile of every value of the statistic, over the category's universe funds and over dates before 2025-10-06.
- A category with fewer than 1,000 values, or fewer than 5 funds, abstains.
- D1, D2 and D4 also abstain for a category with fewer than 11 universe funds, because there cannot be 10 peers.
- A correlation over a window with zero variance is undefined; the detector abstains rather than reading it as smooth.

D5's 730 days is a round number, chosen before the other six targets were looked at. 365 and 1,095 days are reported as sensitivity, not as alternatives to choose from.

## Evaluation

- **Window:** rows dated 2025-10-06 to 2026-09-16. It stops the day before the order, because a row dated 17 September may already reflect the order day.
- **Evaluable and flagged:** a fund is evaluable for a detector when the statistic is defined on at least one window date. It is flagged when it has at least one alarm.
- **Per detector, report:**
  - Targets flagged out of targets evaluable, with each target's first alarm date and the days left before 17 September.
  - Non-targets flagged out of non-targets evaluable.
  - Alarm days per evaluable non-target day.
  - The number of targets expected if the same number of funds were flagged at random.
- **Composite (descriptive):** how many of D1 to D5 flag each fund, for targets and for non-targets.
- **Reference:** the fund-level flag rate in the 250 dates before the window. This is in-sample for the thresholds.
- **History sensitivity:**
  - Thresholds taken only from the 250 dates before the window.
  - The first window date on which each detector could run if no price before 2025-10-06 were used.
- **Naming:** results name only targets. Non-targets are counted and never named in committed files, because a flag is not an allegation.

## Limits

- **Selection after the event:** the universe is chosen by investor counts from after the order, and categories are today's. Funds that closed are missing from TEFAS (survivorship).
- **Few, linked targets:** the 8 targets come from 4 companies, and 4 of them are Tera funds. This is a case study, not a statistical test.
- **Peers:** only universe funds serve as peers, not each category's full membership.
- **Price only:** KAP fundamentals, such as units outstanding and size, are a separate next step.
