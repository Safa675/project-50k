# SPK liquidation order of 17 September 2026

The case this project is measured against: on 17/09/2026 SPK ordered 131 funds of seven portfolio management companies liquidated (decisions 57/1707 and 57/1708; list in Bulletin 2026/61, section C). SPK later put the number of unique affected investors at 455,758. Companies: Pardus (42 funds), Hedef (31), Atlas (16), Bulls (15), Pusula (12), A1 Capital (9) and Tera (6).

Files here:

| File | What |
|---|---|
| `extract.py`, `liquidated_funds.json` | The 131 funds from the bulletin, each mapped to its TEFAS code (130 by exact name, KSA by closest name) |
| `stage1_funds.txt` | The first stage's funds: the top ten by investor count plus TP2 |
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

Prices (five years, TEFAS dates) are downloaded. KAP monthly reports are downloaded slowly (one request every six seconds); results will be added when they are in.

What the prices show for the two liquidating funds in this stage, described without any detector:

- **TP2** (money market): for over a year it earned about 0.03 to 0.05 percentage points a day more than the median of the stage's seven other money-market funds, roughly 7 to 9 points a year. Those seven are large bank-affiliated funds, not the whole category, so this does not show an outlier within the category. The gap did not change before the order: in its last 20 priced days it stayed inside its earlier range. TEFAS shows no price from 17 September.
- **THF** (equity): its price rose about 115% over the year to 16 September. It rose 1.8% and 1.0% on 9 and 10 September, then moved by under half a percent a day from 11 to 16 September. On 17 September it fell about 8%, then by 12% to 39% on each of the next five trading days, and from 25 September it has no price.
- Neither shows a change in price behaviour before 17 September. Because TEFAS dates a price one business day after its valuation date, the first drop in THF's series reflects the 16th at the earliest. On this evidence price alone gives no lead time for these two; an early signal would have to come from elsewhere: flows (monthly units outstanding in KAP reports), the portfolio, disclosures, or patterns across a company's funds.

## Method rules for the measurement

1. Fix the funds before looking at outcomes, by a rule (top N by investors, or all funds), not by whether they were liquidated.
2. Use the thresholds in the anomaly catalog as written. Do not tune them on these funds, and do not report these funds as independent validation of thresholds tuned on them.
3. Use only what was knowable on the day: a price when TEFAS published it, a KAP report from its publish time.
4. Count false alarms: the same detectors on the funds that were not liquidated.
5. These are four companies and eight funds that move together: a case study, not statistical evidence. A fund with no visible warning in public data is a finding too.

## Open

- The other six top-100 targets (TLY, DFI, DOH, PRY, KHA, PNU) are not downloaded yet (stage 2).
- Fund-versus-category detection (AN-FND-001) needs peer sets. Today's category membership leaves out funds that closed during the year.
- Whether other KAP disclosures (not the monthly report) existed for these companies before 17 September.
