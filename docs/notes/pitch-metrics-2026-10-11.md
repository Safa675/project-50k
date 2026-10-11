# BlackSwan pitch metrics — real historical data

Verified against the real product database and the unchanged evaluation plus isolated monthly experiment on
2026-10-11. Use everyday language and keep the method label attached to each result.

## Recommended figures

| Slide figure | Plain-language meaning |
|---|---|
| **2,133 funds** | Funds in the historical analysis universe. |
| **1.75 million daily records** | Stored fund observations across 2,131 funds. This is archive size, not a claim that all records were available on the analysis date. |
| **7.6×** | In the historical comparison, funds later listed by SPK were flagged by the price checks 7.6 times as often as other funds: 17.6% versus 2.3%. |
| **4 of 8 → 5 of 8** | Among the eight later-listed funds in the original 100-fund cohort, the price checks flagged four; adding the separate monthly-report experiment brings that to five. |
| **23 of 131 → 24 of 131** | In the wider SPK-list comparison, the original price checks flagged 23 funds; the separate price-plus-monthly experiment flags 24 (17.6% → 18.3%). |

The five-of-eight figure is a case-study subset. Show the wider 131-fund result alongside it; do not present it as
the result for the entire fund universe.

## Useful supporting figures

- **1,977 of 2,133 funds (92.7%)** could be assessed by at least one price check at the chosen cutoff.
- **69 funds** were flagged by the price checks; **23 of those 69 (33.3%)** later appeared on the SPK list.
  The other 46 were outside this particular list; that does not establish that every one was an erroneous flag.
- The monthly experiment could assess **101 funds**, flagged **three**, and **two** of those were later listed.
  **KHA** is its additional case beyond the price checks. Its coverage is narrow.
- The comparison uses information eligible by **12 September 2026**, then compares it with the **17 September 2026**
  SPK liquidation orders. This date gap is not a measured or validated early-warning lead time.

## Suggested pitch wording

"Our historical analysis covers 2,133 funds. In the development test, price checks flagged funds later listed by SPK
7.6 times as often as other funds. Adding a monthly-report check increased the flagged cases in our original
eight-case group from four to five; across the wider list, the combined result was 24 of 131."

Short slide footnote:

**Historical development results; not independently validated. Monthly-report rule shown as a separate experiment.**

Optional Turkish slide footnote: **Geçmiş verilerle geliştirme testi; bağımsız doğrulama değildir. Aylık rapor kuralı ayrı bir deneydir.**

## Keep the counts consistent

- 2,133 is the full analysis cohort; 131 is the later SPK liquidation-order subset; 8 is the subset in the original 100.
- The original 100 contribute 115,371 stored daily rows; their eight SPK-listed funds contribute 5,044 rows.
- The dashboard's **all checks** view has a different result: **25 of 131 (19.1%)**, including source-data quality checks.
  Do not label that as the price-only 23 or combine its count with the price-only 7.6× comparison.
- Do not call any of these figures "fraud accuracy," "predicted liquidations," "prevented losses," or validated
  performance. The methods were developed with knowledge of the historical case; no held-out test set exists.

These figures come from `/evaluation/retrospective`, `/evaluation/kap-scale-experiment`, the saved original
`top100_funds.txt` cohort and read-only database counts. The product presents the comparison at `/results`.
