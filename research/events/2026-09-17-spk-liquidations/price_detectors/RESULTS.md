# Price-only detectors on the top 100 funds: results

Run once on 2026-10-07 under the rules in `PREREGISTRATION.md`, committed in b01da35 before the run. No rule was changed after the results were seen. All numbers are in `results.json`. That file names only the eight targets; per-fund detail stays in `../raw/price_detectors/` (gitignored).

## Main result

Window: rows dated 2025-10-06 to 2026-09-16. A fund counts as flagged when it has at least one alarm in the window.

| Detector | Targets flagged | Expected at random | Other funds flagged | Other funds flagged, year before the window |
|---|---|---|---|---|
| D1 persistent excess return | 5 of 8 | 1.1 | 5 of 63 | 6 of 63 |
| D2 change in excess return | 3 of 7 | 0.8 | 5 of 63 | 4 of 63 |
| D3 return autocorrelation | 0 of 8 | 0.4 | 4 of 83 | 7 of 83 |
| D4 correlation with peers | 0 of 8 | 0.5 | 4 of 63 | 5 of 63 |
| D5 young fund (under 730 days) | 6 of 8 | 0.9 | 5 of 92 | 11 of 92 |

"Expected at random" is the number of targets flagged if the same number of funds had been picked at random. D1, D2 and D4 cover fewer funds because they need 10 peers, so they run only for money-market, equity, debt and hedge (serbest) funds.

| Target | Company | Category | D1 first alarm (days before 17 Sep) | D2 first alarm | D5 | Detectors firing |
|---|---|---|---|---|---|---|
| TP2 | Tera | Money market | 2025-10-06 (346); above the threshold since 2025-03-20 | 2025-11-10 (311) | yes | 3 |
| PRY | Pusula | Money market | 2025-10-06 (346); above since 2025-08-06 | 2025-11-03 (318) | yes | 3 |
| DFI | Atlas | Hedge (serbest) | 2025-11-20 (301) | 2025-11-10 (311) | no | 2 |
| KHA | Pardus | Equity | 2026-08-10 (38) | none | yes | 2 |
| PNU | Pusula | Money market | 2026-06-01 (108) | too young | yes, from its first price on 2026-03-12 | 2 |
| THF | Tera | Equity | none | none | yes | 1 |
| DOH | Tera | Hedge (serbest) | none | none | yes | 1 |
| TLY | Tera | Hedge (serbest) | none | none | no | 0 |

TP2 and PRY are dated 2025-10-06 because they were already above the threshold on the window's first day. They then stayed above it on every window date.

**Combined:**
- Two or more detectors fired for 5 of the 8 targets and for 5 of the 92 other funds. Three or more fired for 2 targets and 2 other funds.
- The other fund with the most alarms (4 of 5) belongs to one of the seven companies. Its TEFAS price has also stopped, but it is not in SPK's list.

## What it shows

- **D1 is the price signal that worked here, mostly in money-market funds.**
  - All three liquidated money-market funds (TP2, PRY, PNU) earned persistently more than their peers. None of the 16 other money-market funds did.
  - For TP2 this held from March 2025, 18 months before the order.
  - Outside money-market funds, D1 flagged one target in each of the equity and hedge categories. It also flagged 3 of 21 other equity funds and 2 of 13 debt funds.
- **The smoothness detectors (D3, D4) caught no target.**
- **THF shows nothing in prices before the order except its age.** Its KAP report for August, published on 2 September, shows units outstanding up 54-fold in one month (see `../NOTES.md`). A price-only system misses THF; KAP does not.
- **D5 is partly an artefact of the fund selection.**
  - The universe is today's top 100 by investors, so a young fund in it is one that gathered investors very fast. With a 365-day limit, D5 flags 4 targets and none of the 92 other funds.
  - At the window start, though, PNU did not exist yet, and other young targets may not have been in a top 100.
  - "Young and already very popular" can be tested at the time only with dated investor counts. TEFAS keeps no history of them; the daily snapshot job records them from 2026-10-06 on.
- **On the six targets not seen before the pre-registration** (all but TP2 and THF), D1 flagged 4 and D5 flagged 4.

## What the longer history did

- **Thresholds from only the last 250 dates before the window gave similar results:**
  - D1: 4 of 8 targets and 4 of 63 other funds.
  - D2: 2 of 7 targets and 5 of 63 other funds.
  - D3: 1 of 8 targets and 9 of 83 other funds.
  - D4: 0 of 8 targets and 6 of 63 other funds.
- **The earlier history matters most as a "before".** With no price before 2025-10-06, the median fund loses this many of the window's 238 dates before a detector can run:

  | Detector | Window dates lost |
  |---|---|
  | D1 | 50 |
  | D2 | 160 |
  | D3 | 101 |
  | D4 | 100 |

  There is also nothing before the window to set thresholds on. D2's alarms for TP2, PRY and DFI in November 2025 would not exist, and D5 could not tell a five-year-old fund from a new one.

## Limits

- **Selection and timing:**
  - The universe and the categories were chosen with data from after the order.
  - Peers are top-100 funds only.
  - Funds that closed are missing from TEFAS.
- **Few, linked targets:**
  - The eight targets come from four companies, four of them Tera funds. This is a case study, not a statistical test.
  - TP2 and THF shaped the ideas behind D1, D2 and D5.
- **A flag is not evidence of wrongdoing.** The other funds D1 flagged may have ordinary explanations, such as strategy or duration. The common timing of D2's November alarms across three companies may be a market move, for example rate changes that favour longer-dated holdings.

## Next

1. Run the same rules on all 2,133 funds and all 131 liquidated funds, with each category's full membership as peers. This removes the top-100 selection and costs about an hour of TEFAS requests.
2. Add KAP fundamentals: month-to-month units outstanding (flows) and size, joined with D1. The parser first needs Tera's next-line values and the Ziraat, Garanti and Yapı Kredi layouts.
