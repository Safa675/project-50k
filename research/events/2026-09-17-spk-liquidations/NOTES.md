# SPK liquidation order of 17 September 2026

The case this project is measured against: on 17/09/2026 SPK ordered 131 funds of seven portfolio management companies liquidated (decisions 57/1707 and 57/1708; list in Bulletin 2026/61, section C). SPK later put the number of unique affected investors at 455,758. Companies: Pardus (42 funds), Hedef (31), Atlas (16), Bulls (15), Pusula (12), A1 Capital (9) and Tera (6).

Files here:

| File | What |
|---|---|
| `extract.py`, `liquidated_funds.json` | The 131 funds from the bulletin, each mapped to its TEFAS code (130 by exact name, KSA by closest name) |
| `stage1_funds.txt` | The first stage's funds: the top ten by investor count plus TP2 |
| `top100_funds.txt` | The 100 funds with the most investors (2026-10-06), in rank order |
| `price_detectors/` | Pre-registered price-only detectors on the top 100: rules, code, results |
| `raw/` | Gitignored: the bulletin PDF and downloaded TEFAS price files. Data rights for TEFAS and KAP have not been reviewed, so no real fund values are committed. |

## Where the 131 funds rank

Ranked by investor count in the 2026-10-06 TEFAS snapshots of all 2,133 listed investment funds. Whether the counts of the funds with no price are frozen since the order is not verified.

| Top N by investors | Liquidating funds inside | Share of the 131 funds' investor holdings |
|---|---|---|
| 10 | 1 | 29.5% |
| 50 | 6 | 85.0% |
| 100 | 8 | 91.3% |
| 500 | 20 | 98.3% |

The eight in the top 100, by rank: THF 9, TP2 11, TLY 21, DFI 40, DOH 44, PRY 49, KHA 77, PNU 90. Four are Tera funds (THF, TP2, TLY, DOH), two Pusula (PRY, PNU), one Atlas (DFI) and one Pardus (KHA). Holdings are shares of investor records: a person in two funds counts twice, unlike SPK's unique count.

Most of the 131 are small: 87 have fewer than 100 investors.

## What TEFAS shows for them today

- 21 of the 131 funds have a price of 0, which is TEFAS's placeholder for "no price". Five of the eight top-100 funds are among them (THF, TP2, TLY, DOH, DFI). Their size and units outstanding are also 0 (DFI shows a size of 0.01 and units outstanding), while the investor count remains. The other 110 still show a real price, size and investor count.
- 112 other funds also have a price of 0. Almost all are not traded on TEFAS: special-purpose funds, matured series and funds without history. A zero price therefore does not identify a liquidation. Two funds with a zero price are flagged as traded on TEFAS and belong to Pusula (PBR, PHE), one of the seven companies, but are not in SPK's list. That is an observation only.

## Stage 1: the top ten funds plus TP2 (eleven funds)

Prices (five years, TEFAS dates) and a year of KAP monthly reports are downloaded. The KAP download took 316 requests at one every six seconds, with no failures. Which report layouts parse is in `../../spikes/2026-10-06-tefas/REPORT.md`.

What the prices show for the two liquidating funds in this stage, described without any detector:

- **TP2** (money market): for over a year it earned about 0.03 to 0.05 percentage points a day more than the median of the stage's seven other money-market funds, roughly 7 to 9 points a year. Those seven are large bank-affiliated funds, not the whole category, so this does not show an outlier within the category. The gap did not change before the order: in its last 20 priced days it stayed inside its earlier range. TEFAS shows no price from 17 September.
- **THF** (equity): its price rose about 115% over the year to 16 September. It rose 1.8% and 1.0% on 9 and 10 September, then moved by under half a percent a day from 11 to 16 September. On 17 September it fell about 8%, then by 12% to 39% on each of the next five trading days, and from 25 September it has no price.
- **KAP reports show what the prices don't.**
  - **TP2:** units outstanding rose 4.3-fold from October 2025 to August 2026, by 26% to 37% a month from November to February. Three bank-affiliated money-market funds in this stage (TKM, TI1, DLY) ended the same period at 0.7 to 1.0 times their October units, although DLY swung by up to 30% in single months.
  - **THF in July:** the July report shows nothing comparable.
  - **THF in August:** the August report was published on KAP on 2 September 2026 at 11:02, fifteen days before the order. It shows units outstanding up 54-fold in one month and size up about 70-fold, with the month-end price about 28% above July's. The portfolio is valued at about 112% of the fund's total value, with payables of about 17%; these may be purchases not yet settled. The report does not mention a merger.
- Neither shows a change in price behaviour before 17 September. Because TEFAS dates a price one business day after its valuation date, the first drop in THF's series reflects the 16th at the earliest. On this evidence price alone gives no lead time for these two; an early signal would have to come from elsewhere: flows (monthly units outstanding in KAP reports), the portfolio, disclosures, or patterns across a company's funds.

## Method rules for the measurement

1. Fix the funds before looking at outcomes, by a rule (top N by investors, or all funds), not by whether they were liquidated.
2. Use the thresholds in the anomaly catalog as written. Do not tune them on these funds, and do not report these funds as independent validation of thresholds tuned on them.
3. Use only what was knowable on the day: a price when TEFAS published it, a KAP report from its publish time.
4. Count false alarms: the same detectors on the funds that were not liquidated.
5. These are four companies and eight funds that move together: a case study, not statistical evidence. A fund with no visible warning in public data is a finding too.

## KAP report cadence

Seen so far in the KAP report lists of 54 funds, including 6 of the 8 top-100 targets (KHA and PNU are not downloaded yet):

- **Three liquidated funds (TLY and DOH of Tera, DFI of Atlas) switched from monthly to weekly reports.** Their last monthly report is for July (published 3 August for TLY and DOH, 10 August for DFI). Weekly reports followed on 2 and 9 September (DFI also on 16 September), with no August monthly report. KAP's period code changes from `AB` to `HB`.
- THF, TP2 and PRY, the other liquidated funds read so far, stayed monthly. None of the 48 other funds read so far has a weekly report.
- Why they switched is not known. It is a pattern found in funds already examined, so it is a hypothesis to test on funds never looked at, not a validated signal. The KAP report list alone is enough to test it, at about 3 requests per fund, without downloading any PDF.

## Top 100: price-only detectors

Five years of prices for all 100 funds were downloaded on 2026-10-07. Five price-only detectors were pre-registered and run once; see `price_detectors/RESULTS.md`.

In short:
- Persistent excess return over category peers (D1) flagged 5 of the 8 targets and 5 of 63 other funds. This includes all three liquidated money-market funds, and no other money-market fund.
- The smoothness detectors flagged no target.
- THF was caught only by its age, which is itself inflated by choosing the universe with today's investor counts.

## Open

- KAP reports for the other 89 top-100 funds are not downloaded (needs the owner's go-ahead), and three report layouts are not parsed yet.
- The same detectors on all 2,133 funds and all 131 liquidated funds, without the top-100 selection.
- Fund-versus-category detection (AN-FND-001) needs peer sets. Today's category membership leaves out funds that closed during the year.
- Whether other KAP disclosures (not the monthly report) existed for these companies before 17 September.
