# Fund accounting research lab

Research date: 2026-10-02. Requirements: DR-002/004/005/006/007/008/009/010, FR-034/035/037/038; AN-FND-002/003/004/006 and AN-CMP-002. These are research findings and proposed capability gates. Shared specifications and configuration were not changed.

**Keep the return-adjusted endpoint residual as a conditional accounting estimate. Reject the claim that two AUM/NAV observations—or investor counts—identify actual subscription/redemption cash, securities sold, or withdrawal timing.** All calculations below use authored synthetic inputs. Nothing here evaluates real Turkish funds, reconstructs an incident, or validates detector accuracy or the project's thresholds.

## Reproduce and observed result

From `working/Project_50K_v0.5_research`:

```bash
python experiments/fund_accounting.py --output research/engine_lab/fund_results.json
```

Observed stdout on 2026-10-02:

```text
PASS: 49 named synthetic cases; 768 bounded accounting combinations; 48 uncertainty corner checks.
Observed: identical AUM/NAV endpoints give cash 100 or 120; zero residual can coexist with net cash -20.
Observed: raw split residual 500; distribution reinvestment residual 0/50/100; adjusted stylized controls zero.
Observed: investor count 2->1 gives net cash -100/0/+150; allocation TV can be positive with zero trades or zero with round trips.
Saved research/engine_lab/fund_results.json
```

The independent `Fraction` lifecycle ledger records actual synthetic subscription/redemption amounts at transaction prices and changes units. The endpoint estimator uses `Decimal`, precision 50, `ROUND_HALF_EVEN`, without intermediate currency quantization. The bounded grid varies opening units, prices, signed transactions, timing and splits, including recurring rational values. Its maximum observed absolute Decimal-versus-exact error was `3.33333E-48`, below the authored `1E-40` arithmetic tolerance. Forty-nine is a scenario count, not an empirical sample size or an assertion count. Missingness and comparability helpers are narrow executable examples, not complete production admission gates.

Additional observed verification: Python compilation, both JSON files parsed, saved code SHA matched the experiment, all six source-depth records had the research date, and a repeated execution produced byte-identical `fund_results.json`. Result SHA-256: `39fa46b9a858f964c4939fd36b7c7071679893f0b9ef5b30c1afe913c723d86a`. No shared production test suite was needed for this isolated standard-library lab.

## Primary evidence and its limits

Source details, exact URLs, access dates, extracted sections, web references and failures are in `fund_sources.json`.

SPK's [introductory guide](https://spk.gov.tr/kurumlar/fonlar/yatirim-fonlari/menkul-kiymet-yatirim-fonlari/tanitim-rehberi) defines unit NAV using net fund value divided by outstanding participation units at valuation. This supports the accounting identity, not historical API availability. `FUND-S01`, selected relevant HTML sections read.

The retrieved official [SPK guideline](https://spk.gov.tr/data/6a91fe7d8f95db1fb01ff366/Yat%C4%B1r%C4%B1m%20Fonlar%C4%B1na%20%C4%B0li%C5%9Fkin%20Rehber.pdf) distinguishes indicative prices, transaction pricing and instruction/unit accounting; Appendix EK/3 separates recognition from settlement and illustrates outstanding units. Sections 8.4 and 8.5 describe different indicative-price contexts. Consequently a daily reference price cannot automatically be treated as a daily executable NAV. Section 9.1 describes separately disclosed transaction-volume information. `FUND-S02`, selected sections of 88 pages read, including amendments observed through August 2026; no comprehensive legal interpretation.

[Morningstar's 2018 methodology](https://www.morningstar.com/content/dam/marketing/shared/research/methodology/765555_Estimated_Net_Cash_Flow_Methodology.pdf) includes distribution/reinvestment and merger corrections, and acknowledges a share-class approximation for whole-fund estimates. Its historical reinvestment assumptions must not become Turkish defaults or future information in replay. `FUND-S03`, all three extracted pages read; its present implementation was not verified. The [ICI glossary](https://www.ici.org/fb-glossary) distinguishes net new subscription/redemption money, total return with reinvestment, and portfolio turnover. `FUND-S04`, selected entries read in a US context.

Official unit-share **definitions and illustrative accounting evidence were obtained**. A dated, licensed historical Turkish outstanding-unit feed was not established. A failed NBER PDF retrieval is recorded as unread and supports no claim. No primary source reviewed validates the project's 10% flow or 20% allocation thresholds.

## What the formula actually identifies

Let `A` mean total **net** assets, `p` the unadjusted unit transaction NAV and `Q` the outstanding units of the same fund/share-class scope, currency and valuation instant. Under `A = Q p`, our algebra gives:

\[
F^*=A_1-A_0\frac{p_1}{p_0}=p_1(Q_1-Q_0).
\]

This is an exact endpoint unit-value residual under those identities. Its interpretation as external net cash is an additional assumption. With no distributions, unit changes, noncash transfers or accounting breaks, and transactions `c_i` booked at NAV `p_i`, the synthetic ledger gives:

\[
F^*=\sum_i c_i\frac{p_1}{p_i},\qquad C=\sum_i c_i.
\]

They agree if all relevant transactions use `p_1`, or in particular cases where the weighted differences cancel. Sparse endpoints cannot establish that condition. Even exact endpoint unit counts do not resolve missing transaction prices/timing. Our cash target means subscriptions less redemptions recognized at transaction NAV, excluding distributions; bank settlement cash is another quantity. Commissions and settlement lags need their own accounting conventions.

For a known split factor `s` (closing equivalent units per opening unit), the comparable residual is `A1 - A0*s*p1/p0 = p1*(Q1-s*Q0)`. Unknown splits require abstention. This is not a general merger or distribution correction. A total-return index must not be substituted for raw NAV without specifying its distribution/reinvestment convention.

## Executed counterexamples

| Synthetic observation | Ground truth/control | Inference blocked |
|---|---|---|
| AUM 1000→1200, NAV 10→12; or AUM 1000→800, NAV 10→8 | No external transaction; residual 0 | AUM decline alone means withdrawals |
| Identical endpoints AUM 1000→1320, NAV 10→12, units 100→110 | Add cash 100 at NAV 10 before return, or cash 120 at NAV 12 after return; both residuals 120 | Endpoint residual is exact cash |
| Subscribe 100 at NAV 10; redeem 120 at NAV 12 | Units unchanged; residual 0; subscription minus redemption cash −20 | Zero residual means zero cash flow |
| Distribute 1 per unit; raw NAV 10→9; reinvest 0%, 50%, 100% | External new subscription cash 0 throughout; raw residual 0, 50, 100 | Unit growth necessarily means external cash |
| Same distribution controls using known total-return factor 1 | Uncorrected residual −100, −50, 0; add known cash distributions to get 0 | Total return alone always corrects distributions |
| Two-for-one split, AUM unchanged | Raw residual +500, known split-adjusted residual 0 | Mechanical unit change means inflow |
| Noncash merger adds assets 500 | Residual +500; external subscription cash 0 | Asset transfer means new investor money |
| Same-currency FX translation, NAV and AUM both rise 20% | Residual 0; mismatched TRY AUM/USD NAV instead produces +200 | FX exposure explains a residual without checking matched inputs |
| Fund AUM unchanged; one class rises 20%, another falls 20% | Using whole-fund AUM with first-class NAV fabricates −200 | One class return exactly describes a multi-class fund |
| Previously booked redemption payable 100 is settled | Net assets/NAV/units unchanged; residual 0, bank cash −100 | Unit-flow estimate measures settlement cash |
| Investor count 2→1 | Remaining investor adds nothing, 100, or 250 while departing investor redeems 100: net cash −100, 0, +150 | Count decline identifies amount or sign of money moved |
| Fixed quantities, one asset doubles in price | Weights 1/2,1/2→2/3,1/3; TV=1/6; no trades | Allocation distance equals realized turnover |
| Identical opening/closing 50/50 weights | No trades, or buys 1000 and sells 1000 in round trips | Small allocation distance means low turnover |
| Identical 100 redemption and AUM/NAV endpoints | Fund pays from existing cash, or sells securities first | Even known redemption cash identifies asset sales |
| NAV published before AUM; revision published tomorrow | Earlier snapshot excludes future publication/receipt/revision | Valuation date makes every field available simultaneously |

The distribution adjustment controls deliberately have one immediate distribution and no other return/trading. They do not implement a general path-aware distribution engine. The stale-holdings scenario is an identifiability illustration: the same published snapshot permits different current exposures. It is not a live report freshness test. Actual zero investor count is distinct from a provider's placeholder zero; percentage change at an actual zero denominator remains undefined.

## Deterministic uncertainty and sensitivity

For positive, known bounds on four matched values, interval arithmetic gives conservative limits for `F*` and `rho = F*/A0`:

\[
F_{min}=A_{1,min}-A_{0,max}p_{1,max}/p_{0,min},\quad
F_{max}=A_{1,max}-A_{0,min}p_{1,min}/p_{0,max};
\]
\[
\rho_{min}=A_{1,min}/A_{0,max}-p_{1,max}/p_{0,min},\quad
\rho_{max}=A_{1,max}/A_{0,min}-p_{1,min}/p_{0,max}.
\]

These are deterministic bounds, **not confidence intervals**. They conservatively ignore input dependence. In the authored AUM ±5/NAV ±0.005 example around AUM 1000→1100 and NAV 10→10, the apparent 10% rate spans approximately **8.855%–11.155%**; threshold classification is unresolved. Controls around 15% span 13.830%–16.180% and around 4% span 2.885%–5.125%. All 16 corners per example were checked. These error bounds are not measured provider errors.

Local sensitivity is `dF/dA1=1`, `dF/dA0=-p1/p0`, `dF/dp1=-A0/p0`, `dF/dp0=A0*p1/p0²`. Small opening denominators magnify uncertainty. A zero, negative or nonfinite opening AUM/NAV is rejected by the executable helper. Real uncertainty must come from reported precision, corrections or documented valuation limitations. Timing/scope errors are admission failures, not ordinary rounding intervals. An interval wholly above a provisional threshold establishes arithmetic robustness only; it does not validate a detector or establish cause.

## Hypothesis decisions

| Decision | Hypothesis / useful capability | Basis and next condition |
|---|---|---|
| KEEP, conditional | Return-adjusted endpoint unit-value residual and signed fraction of opening net assets | Exact matched accounting identity; label as estimate and carry conventions/assumptions |
| KEEP | Separate dated investor-count change | Observable count statistic; never translate into cash or asset sales |
| KEEP | Published nonnegative allocation snapshot distance | Observable compositional change with price drift alternatives; signed/leverage model separate |
| KEEP | Conservative arithmetic uncertainty bounds and cutoff/revision provenance | Synthetic checks pass; provider-bound inputs and full adapters remain needed |
| REJECT | Exact subscription/redemption cash from two NAV/AUM/units endpoints | Matched endpoint counterexamples produce different cash |
| REJECT | Investor-count fall implies redemptions, capital flight, or security selling | Negative/zero/positive cash with same count change |
| REJECT | Allocation TV measures realized turnover or old holdings establish current exposure | Revaluation and round-trip counterexamples; disclosure lag |
| DEFER | Actual net subscription cash / cash settlement / securities turnover | Reported flow/trade/accounting evidence needed, with target definitions and rights |
| DEFER | Distribution/split/merger-aware production estimate | Fund-specific action chronology, reinvestment data and observed historical coverage needed |
| DEFER | Peer residuals, incident attribution, causal linkage, thresholds or accuracy claims | Licensed aligned data, fixed protocol, independent holdout evaluation and baseline calibration needed |

## Concrete proposed capability gates

These fields extend the existing DR contracts; no production schema migration is made here.

| Capability fields | Required interpretation / failure behavior |
|---|---|
| `fund_id`, `share_class_id`, `scope_id`, `fund_type`, `currency`, `asset_basis` | Verify same scope and net assets, not gross portfolio value, combined class AUM or another class NAV; unknown/mismatch abstains |
| Per field: `effective_at`, `valuation_timezone`, `valuation_basis`, `published_at`, `available_at`, `revision_id`, `source_document_id`, `source_url`, `raw_record_hash` | Independently date NAV/AUM/count/allocation/units; both publication and receipt eligible at cutoff; immutable earlier decisions; no inferred publication time |
| `nav_kind`, `price_used_for_transactions`, `expected_publication_calendar`, `cadence_evidence_id`, `last_valid_value_at`, `stale_reason` | Distinguish transaction NAV, indicative/reference price, total-return index and stale carried price; follow fund-specific prospectus/provider semantics rather than universal daily/intraday assumptions |
| `unit_definition`, `outstanding_units`, `unit_effective_at`, `unit_publication_at`, `unit_scope_id`, `unit_precision` | Units are participation shares, not investor accounts; observed historical units may cross-check `A≈Qp`, but derived `A/p` is not independent evidence |
| `split_factor`, `split_effective_at`, `distribution_per_unit`, `distribution_ex_date`, `distribution_pay_date`, `reinvestment_fraction`, `merger_transfer_assets`, `class_conversion`, `action_evidence_id` | Unknown action status abstains; do not assume no distributions/restructuring from absent wrapper fields or import foreign category defaults |
| `flow_target`, `order_at`, `share_recognition_at`, `transaction_NAV_at`, `cash_settlement_at`, `pending_redemption_liability`, `reported_net_subscriptions`, `flow_currency`, `subscription_fee_basis` | Separate share transactions, recognized liabilities and bank settlement; direct disclosed flows remain dated facts, not validation of sparse endpoint inference |
| `missing_reason`, `is_placeholder`, `reported_precision`, `value_lower`, `value_upper`, `bound_origin`, `identity_residual`, `identity_tolerance_origin` | No zero fill/forward fill; numeric uncertainty only from defensible bounds; `A≈Qp` failure quarantines, never repairs by guessed units |
| `count_definition`, `count_effective_at`, `count_definition_version`, `series_break_reason` | Investors versus accounts/holders distinct; comparable dated counts required; true zero permits absolute change only |
| `allocation_denominator`, `category_mapping_version`, `allocation_effective_at`, `allocation_publication_at`, `signed_exposure`, `holdings_security_id`, `holdings_report_age`, `lookthrough_status` | Comparable complete category universe; no silent normalization of short/leverage exposure; published allocation/holdings are dated snapshots, not current trades |
| `storage_allowed`, `replay_allowed`, `derived_use_allowed`, `display_allowed`, `redistribution_allowed`, `entitlement_evidence_id`, `source_capability_version` | Wrapper accessibility is not entitlement; retain existing rights release gate before real ingestion/replay/display |
| `estimate_method_version`, `configuration_version`, `assumption_flags`, `unresolved_alternatives`, `rate_bound`, `threshold_classification`, `baseline_sample_size`, `evidence_ids` | Separate point estimate, assumption uncertainty and unvalidated heuristic threshold; abstention is not a no-risk finding |

The executable `metadata_gate` tests only a subset: scope/class/currency/effective-time/valuation alignment, net assets, raw NAV kind, corporate-action resolution and missingness. The temporal helper tests fixture publication/receipt cutoffs and revisions. It does not implement provider entitlement, all revision tie cases, production calendar freshness, source authenticity, or complete action accounting.

## Scope and next step

Changed only the dedicated experiment and these three research artifacts. No deployment, account creation, spending, contact, shared-doc/config edits, real fund/API request, performance measurement, or migration. The experiment uses only the standard library. Primary document browsing established definitions and method context, not data entitlement.

The next authorized implementation step is to specify a source-specific offline raw-record contract and freeze explicit scope/time/price/action semantics. Production flow/count detectors stay conditional until actual historical field coverage, rights and aligned publication evidence are established. A genuine fund cash/trade ledger would enable cash/turnover validation; a current NAV page alone would not.
