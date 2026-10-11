# BlackSwan pitch metrics — real historical data

Verified against the real product database and the unchanged evaluation plus isolated monthly experiment on
2026-10-11. Use everyday language and keep the method label attached to each result.

## Correction: screening is not a completed agent investigation

Mirza challenged the earlier pitch framing on 2026-10-11. The 2,133 figure was too easy to read as completion of the
whole pipeline. It is the fixed-check screening universe, not a count of completed AI or human investigations.
The table below is a read-only runtime snapshot at approximately 12:54 Istanbul; activity counts can increase.

| Processing stage | Verified count |
|---|---:|
| Funds with stored fixed-check screening results for the September12 view | 2,133 |
| Funds with all four AI-review stages completed and a valid team report | 72 |
| Funds with a valid team report, including one without all four AI stages completed | 73 |
| Team proposals with a recorded human review in this analysis scope | 1 |

These are activity counts. Completing a report is not proof that its conclusion is correct, and a valid report is
not independent validation of detection quality. Do not describe 2,133 as fully processed through the agent team,
or 72 as successful predictions. Screening routes flagged or user-requested cases into deeper investigation.

## Product proof and historical study figures

| Slide figure | Plain-language meaning |
|---|---|
| **2,133 funds screened** | Funds processed by the fixed checks, before the AI-team review. |
| **72 completed AI investigations** | All four AI-review stages completed, at the snapshot above. This is workflow completion, not an accuracy score. |
| **1.75 million daily records** | Stored fund observations across 2,131 funds. This is archive size, not a claim that all records were available on the analysis date. |
| **7.6×** | In the historical comparison, funds later listed by SPK were flagged by the price checks 7.6 times as often as other funds: 17.6% versus 2.3%. |
| **5 of 8 case-study funds** | In a separately evaluated historical study, combined price and portfolio-report checks flagged five of the eight later-listed funds in the original 100-fund cohort. |
| **24 of 131 in the wider comparison** | The same combined historical method flags 24 funds in the wider SPK-list cohort (18.3%). |

The five-of-eight figure is a case-study subset. Show the wider 131-fund result alongside it; do not present it as
the result for the entire fund universe. The monthly rule is a separate evaluated component and is not yet an input
to the live agent workflow. Price changes and changes in a fund's size are different observations; describe the
combined method without a before/after story implying that the first method was erroneous.

## Useful supporting figures

- **1,977 of 2,133 funds (92.7%)** could be assessed by at least one price check at the chosen cutoff.
- **69 funds** were flagged by the price checks; **23 of those 69 (33.3%)** later appeared on the SPK list.
  The other 46 were outside this particular list; that does not establish that every one was an erroneous flag.
- The monthly experiment could assess **101 funds**, flagged **three**, and **two** of those were later listed.
  **KHA** is its additional case beyond the price checks. Its coverage is narrow.
- The comparison uses information eligible by **12 September 2026**, then compares it with the **17 September 2026**
  SPK liquidation orders. This date gap is not a measured or validated early-warning lead time.

## Suggested pitch wording

Lead with the demonstrated workflow:

"We screened 2,133 funds and completed 72 AI-team investigations, with findings linked to sources and ready for
human review. BlackSwan makes the path from a flagged observation to a reviewable report visible."

If the historical study is included:

"In a separate historical study, combined price and portfolio-report checks highlighted five of eight case-study
funds. The wider comparison identified 24 of the 131 funds later listed by SPK."

Do not lead with an accuracy claim: these results do not yet demonstrate reliable future prediction across the
whole product universe. Analyst agreement, review time saved and performance on genuinely new cases still need
to be measured before they can be claimed as success metrics.

Short slide footnote:

**Historical development study; not independently validated. Combined research method evaluated separately from the live agent workflow.**

Optional Turkish slide footnote: **Geçmiş verilerle geliştirme çalışması; bağımsız doğrulama değildir. Birleşik araştırma yöntemi canlı ajan akışından ayrı değerlendirilmiştir.**

## Keep the counts consistent

- 2,133 is the full analysis cohort; 131 is the later SPK liquidation-order subset; 8 is the subset in the original 100.
- The original 100 contribute 115,371 stored daily rows; their eight SPK-listed funds contribute 5,044 rows.
- The dashboard's **all checks** view has a different result: **25 of 131 (19.1%)**, including source-data quality checks.
  Do not label that as the price-only 23 or combine its count with the price-only 7.6× comparison.
- Do not call any of these figures "fraud accuracy," "predicted liquidations," "prevented losses," or validated
  performance. The methods were developed with knowledge of the historical case; no held-out test set exists.

These figures come from `/evaluation/retrospective`, `/evaluation/kap-scale-experiment`, the saved original
`top100_funds.txt` cohort and read-only database counts. The product presents the comparison at `/results`.
