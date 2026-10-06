# Evaluation-metric counterexample

**Date:** 2026-10-02. **Origin:** SYNTHETIC. Sixteenth-paper additions are not implied; this primary reference is retained in the supplementary source file. Zero models were trained and zero real financial observations were used.

## Method context

Kim et al. (2022), *Towards a Rigorous Evaluation of Time-Series Anomaly Detection*, warns that label-aware point adjustment can overstate time-series detection performance. We read the official publisher metadata/abstract and selected PDF definition/discussion around the introduction and protocol; we did not reproduce its benchmarks or verify every proof. Original paper: https://ojs.aaai.org/index.php/AAAI/article/view/20680 ; PDF: https://cdn.aaai.org/ojs/20680/20680-13-24693-1-2-20220628.pdf . DOI: 10.1609/aaai.v36i7.20680. Our experiment below is a separately constructed counterexample, not those authors' reported result.

## Frozen experiment design

`experiments/evaluation_bias.py` uses 32 predeclared PRNG seeds, a 20,000-point sequence, four disjoint labeled intervals starting at 1000/6000/11000/16000, and three interval lengths (20,200,1000). Random flags have a fixed Bernoulli probability 0.0025 and never see labels. There is no tuning. Within each seed, the same flag stream is used for every duration and scoring protocol; duration comparisons also change positive prevalence, which is explicitly recorded.

The raw protocol scores every actual flag. The point-adjusted protocol retrospectively marks a whole true interval positive if any flag appeared anywhere in it. It deliberately uses the completed labeled interval, including future labels, and cannot act as a causal deployed warning system. Actual raw flags outside intervals remain false positives in both protocols. Separately measure whether an interval got any flag, and whether its first flag occurred within the first ten points. These are different targets; the metric does not backdate the first alert.

Run from the package root:

```sh
python experiments/evaluation_bias.py --output research/engine_lab/evaluation_results.json
```

## Executed result

Means over the 32 fixed seeds:

| Interval length | Positive prevalence | Raw point F1 | Retrospective adjusted F1 | Any-hit interval recall | First-ten-point recall |
|---|---:|---:|---:|---:|---:|
| 20 | 0.4% | 0.001391 | 0.024369 | 0.023438 | 0.007812 |
| 200 | 4.0% | 0.004848 | 0.549684 | 0.421875 | 0.007812 |
| 1000 | 20.0% | 0.004968 | 0.956449 | 0.937500 | 0.007812 |

The same uninformative process can receive nearly 0.96 adjusted F1 when intervals are long. It did not become an informative model. Raw recall remains small; only one of 128 interval starts received a flag within ten points across this fixed seed set. An “ever touched” target is legitimate if that is the operational goal, but it must be named and cannot substitute for timely warning or accurate point localization.

The exact independent Bernoulli probability of any hit is `1−(1−p)^L`; the early probability uses `min(L,10)`. Analytical values, per-seed confusion counts, raw flag counts, first-hit delays conditional on a hit, input/script hashes and approximate normal Monte Carlo intervals are retained in evaluation_results.json. Missed intervals are kept in recall; conditional delay is not averaged as zero for misses. Approximate rate intervals can extend outside [0,1]; they quantify simulator variability, not valid bounds or financial uncertainty. Thirty-two seeds do not establish a real-market sample size.

## Retain / reject

**KEEP:** raw point metrics when that target is meaningful; explicitly labeled interval recall, first-alert latency/misses, false flags per eligible observation and per asset-day, de-duplicated alert burden and prospective timing. Score the actual emitted decision record, not a reconstructed later event story.

**REJECT:** interpreting adjusted F1 as financial detection accuracy, hiding the target/prevalence/latency, using event labels to repair raw predictions before reporting the engine's actual behavior, or choosing a score threshold after viewing the held-out interval labels.

**DEFER:** real financial performance, usefulness, calibration and loss-prevention claims until a licensed point-in-time protocol, independent labels and untouched evaluation periods exist. This experiment is not a reason to discard all interval-level evaluation; it is a reason to define the user-relevant target and report what actually happened.
