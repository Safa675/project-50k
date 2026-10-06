#!/usr/bin/env python3
"""Seeded synthetic counterexamples for market statistics; never a backtest.

Standard library only. Thresholds/scenarios/default seeds are fixed in source;
no parameter optimization uses evaluation observations or reported outcomes.
OLS coefficients use an independent earlier prefix. No provider/model calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from pathlib import Path
import random
from statistics import mean, median, stdev
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reference.engine import relative_volume, robust_return_signal  # noqa: E402

DEFAULT_SEEDS = (17011, 17021, 17033, 17041, 17053, 17077,
                 17093, 17107, 17117, 17123, 17137, 17147)
Z_THRESHOLD = 4.0
RETURN_FLOOR = .01
VOLUME_THRESHOLD = 3.0
Q = .05


def summary(values):
    """Monte Carlo uncertainty across independent seeds, not financial CI."""
    values = list(values)
    n = len(values)
    # Default n=12: two-sided Student t .975, df=11. Other n use a clearly
    # labeled normal approximation; do not pretend a dozen points is large n.
    critical = 2.200985 if n == 12 else 1.96
    se = stdev(values) / math.sqrt(n) if n > 1 else 0.0
    center = mean(values)
    return {"mean": center, "seed_min": min(values), "seed_max": max(values),
            "mc_se": se, "mc_95_interval": [center-critical*se, center+critical*se],
            "interval_method": "t_df11" if n == 12 else "normal_approximation",
            "independent_seeds": n}


def aggregate(rows, keys, metrics):
    grouped = {}
    for row in rows:
        grouped.setdefault(tuple(row[key] for key in keys), []).append(row)
    out = []
    for values, group in sorted(grouped.items()):
        out.append({**dict(zip(keys, values)),
                    **{metric: summary(row[metric] for row in group) for metric in metrics}})
    return out


def volume_experiment(seed):
    """Same observations and injected events for all comparison methods."""
    profiles = {
        "equity_session_U": (6., 2., 1.2, 1., 1., 1.2, 2., 6.),
        "crypto_UTC_cycle": tuple(1+.7*math.cos(2*math.pi*s/24) for s in range(24)),
        "crypto_flat_control": (1.,)*24,
    }
    prefix, days, assets = 80, 80, 6
    rows = []
    for scenario, profile in profiles.items():
        rng = random.Random(seed + 1000 + list(profiles).index(scenario)*100000)
        slots = len(profile)
        counts = {method: {"tp": 0, "fp": 0, "events": 0, "null": 0}
                  for method in ("pooled20", "same_slot20", "same_slot60")}
        for asset in range(assets):
            # Constructed multiplier and schedule, independent of data noise.
            events = {(prefix+8+13*k, (asset+3*k) % slots) for k in range(6)}
            series = [[1000*profile[slot]*math.exp(rng.gauss(0, .5))
                       for slot in range(slots)] for _ in range(prefix+days)]
            for day, slot in events:
                series[day][slot] *= 4
            for day in range(prefix, prefix+days):
                for slot in range(slots):
                    histories = {
                        # Matched 20 distinct previous sessions, one rotating
                        # slot per session, to isolate time-of-day matching.
                        "pooled20": [series[d][(slot+day-d) % slots]
                                     for d in range(day-20, day)],
                        "same_slot20": [series[d][slot] for d in range(day-20, day)],
                        "same_slot60": [series[d][slot] for d in range(day-60, day)],
                    }
                    event = (day, slot) in events
                    for method, history in histories.items():
                        candidate = relative_volume(series[day][slot], history,
                                                    final_bar=True, same_feed=True,
                                                    threshold=VOLUME_THRESHOLD).outcome == "CANDIDATE"
                        count = counts[method]
                        count["events" if event else "null"] += 1
                        count["tp" if event else "fp"] += int(candidate)
        for method, count in counts.items():
            rows.append({"seed": seed, "scenario": scenario, "method": method,
                         **count, "asset_days": assets*days,
                         "false_flags_per_100_asset_days": 100*count["fp"]/(assets*days),
                         "null_bar_flag_rate": count["fp"]/count["null"],
                         "injected_event_recall": count["tp"]/count["events"]})
    return rows


def fit_market_model(market, asset):
    center_x, center_y = mean(market), mean(asset)
    beta = sum((x-center_x)*(y-center_y) for x, y in zip(market, asset)) / sum((x-center_x)**2 for x in market)
    return center_y-beta*center_x, beta


def return_flag(value, history):
    result = robust_return_signal(value, history, adjustment_verified=True,
                                  threshold=Z_THRESHOLD, absolute_return_floor=RETURN_FLOOR)
    return result.outcome == "CANDIDATE"


def market_context_experiment(seed):
    rows = []
    train_n, eval_n, assets = 120, 90, 12
    event_dates = (10, 24, 35, 49, 65, 79)
    market_dates = (10, 20, 35, 50, 65, 80)
    for scenario in ("stable_beta", "beta_regime_change"):
        rng = random.Random(seed + 2000)
        market_train = [rng.gauss(0, .002) for _ in range(train_n)]
        market_eval = [rng.gauss(0, .002) for _ in range(eval_n)]
        for day in market_dates:
            market_eval[day] += .04 if day % 2 else -.04
        counts = {method: {"idio_tp": 0, "idio_total": 0, "market_only_flags": 0,
                           "market_only_total": 0, "ordinary_fp": 0, "ordinary_total": 0}
                  for method in ("raw", "beta_one_residual", "prior_OLS_residual")}
        errors = []
        for asset in range(assets):
            beta = .4+1.4*asset/(assets-1)
            beta_eval = beta + (.8 if scenario == "beta_regime_change" else 0)
            values_train = [beta*x+rng.gauss(0, .003) for x in market_train]
            values_eval = [beta_eval*x+rng.gauss(0, .003) for x in market_eval]
            idio = {day for index, day in enumerate(event_dates) if index % assets == asset}
            for day in idio:
                values_eval[day] += .03
            alpha_hat, beta_hat = fit_market_model(market_train, values_train)
            errors.append(abs(beta_hat-beta))
            histories = {
                "raw": values_train,
                "beta_one_residual": [y-x for x, y in zip(market_train, values_train)],
                "prior_OLS_residual": [y-alpha_hat-beta_hat*x for x, y in zip(market_train, values_train)],
            }
            for day in range(eval_n):
                values = {"raw": values_eval[day],
                          "beta_one_residual": values_eval[day]-market_eval[day],
                          "prior_OLS_residual": values_eval[day]-alpha_hat-beta_hat*market_eval[day]}
                label = "idio" if day in idio else "market_only" if day in market_dates else "ordinary"
                for method, value in values.items():
                    hit = return_flag(value, histories[method])
                    count = counts[method]
                    count[label+"_total"] += 1
                    count["idio_tp" if label == "idio" else label+"_flags" if label == "market_only" else "ordinary_fp"] += int(hit)
        for method, count in counts.items():
            rows.append({"seed": seed, "scenario": scenario, "method": method, **count,
                         "idio_recall": count["idio_tp"]/count["idio_total"],
                         "market_only_asset_flag_rate": count["market_only_flags"]/count["market_only_total"],
                         "ordinary_flag_rate": count["ordinary_fp"]/count["ordinary_total"],
                         "beta_mean_absolute_error": mean(errors)})
    return rows


def step_up(sorted_p, level):
    cutoff = -1.0
    m = len(sorted_p)
    for rank, p in enumerate(sorted_p, 1):
        if p <= level*rank/m:
            cutoff = p
    return cutoff


def multiple_testing_experiment(seed, batches, assets):
    rows = []
    harmonic = sum(1/i for i in range(1, assets+1))
    scenarios = ("Gaussian_independent_all_null", "Gaussian_correlated_all_null",
                 "Gaussian_independent_10pct_shift", "t3_wrong_Gaussian_all_null")
    for scenario_index, scenario in enumerate(scenarios):
        rng = random.Random(seed + 3000 + scenario_index*100000)
        null_count = assets if "all_null" in scenario else assets-assets//10
        stats = {method: {"fdp": [], "false_count": [], "true_count": [], "any_false": []}
                 for method in ("per_test_q", "BH", "BY")}
        for _ in range(batches):
            common = rng.gauss(0, 1)
            p_values = []
            for asset in range(assets):
                if scenario == "t3_wrong_Gaussian_all_null":
                    # Student t3 normalized to variance1. Still NON-Gaussian.
                    z = rng.gauss(0, 1)/math.sqrt(sum(rng.gauss(0, 1)**2 for _ in range(3)))
                elif scenario == "Gaussian_correlated_all_null":
                    z = math.sqrt(.3)*common+math.sqrt(.7)*rng.gauss(0, 1)
                else:
                    z = rng.gauss(0, 1)+(3.5 if asset >= null_count else 0)
                p_values.append(math.erfc(abs(z)/math.sqrt(2)))
            sorted_p = sorted(p_values)
            cutoffs = {"per_test_q": Q, "BH": step_up(sorted_p, Q), "BY": step_up(sorted_p, Q/harmonic)}
            for method, cutoff in cutoffs.items():
                false = sum(p <= cutoff for p in p_values[:null_count])
                true = sum(p <= cutoff for p in p_values[null_count:])
                stat = stats[method]
                stat["fdp"].append(false/(false+true) if false+true else 0.)
                stat["false_count"].append(false)
                stat["true_count"].append(true)
                stat["any_false"].append(int(false > 0))
        for method, stat in stats.items():
            blocks = [stat["any_false"][i:i+90] for i in range(0, batches-89, 90)]
            rows.append({"seed": seed, "scenario": scenario, "method": method,
                         "batch_count": batches, "nulls_per_batch": null_count,
                         "alternatives_per_batch": assets-null_count,
                         "batch_FDR": mean(stat["fdp"]),
                         "false_rejections_per_batch": mean(stat["false_count"]),
                         "probability_any_false_in_batch": mean(stat["any_false"]),
                         "power": mean(stat["true_count"])/(assets-null_count) if assets > null_count else 0.,
                         "probability_any_false_in_90_batches": mean(int(any(block)) for block in blocks),
                         "ninety_batch_blocks": len(blocks),
                         "p_value_validity": "INVALID_NORMAL_TAIL_ASSUMPTION" if scenario.startswith("t3") else "VALID_KNOWN_GAUSSIAN_MARGINALS"})
    return rows


def contamination_experiment(seed):
    rng = random.Random(seed + 4000)
    rows = []
    trials = [([rng.gauss(0, .002) for _ in range(40)], .03+rng.gauss(0, .002))
              for _ in range(200)]
    for fraction in (0., .1, .3, .5, .6):
        robust_hits = classic_hits = abstentions = 0
        for clean, x in trials:
            count = int(40*fraction)
            history = [.03]*count+clean[count:]
            result = robust_return_signal(x, history, adjustment_verified=True)
            robust_hits += int(result.outcome == "CANDIDATE")
            abstentions += int(result.outcome == "ABSTAINED")
            scale = stdev(history)
            classic_hits += int(abs(x-mean(history))/scale >= Z_THRESHOLD and abs(math.expm1(x)) >= RETURN_FLOOR)
        rows.append({"seed": seed, "contamination_fraction": fraction, "trials": 200,
                     "robust_detection": robust_hits/200, "mean_sd_detection": classic_hits/200,
                     "robust_abstention": abstentions/200})
    past = [rng.gauss(0, .002) for _ in range(20)]
    current = .03
    leaky = past[-4:]+[current]*16
    return rows, {"seed": seed, "current_log_return": current,
                  "causal_prior20_outcome": robust_return_signal(current, past, adjustment_verified=True).outcome,
                  "forbidden_current_and_future_window_outcome": robust_return_signal(current, leaky, adjustment_verified=True).outcome,
                  "past_count_in_leaky_window": 4, "current_future_count": 16}


def policy_counterexamples(seed):
    rng = random.Random(seed + 5000)
    history = [rng.gauss(0, .002) for _ in range(60)]
    split_raw = robust_return_signal(math.log(.5), history, adjustment_verified=True)
    split_unknown = robust_return_signal(math.log(.5), history, adjustment_verified=False)
    split_adjusted = robust_return_signal(0., history, adjustment_verified=True)
    feed_unguarded = relative_volume(500, [100]*20, final_bar=True, same_feed=True)
    feed_guarded = relative_volume(500, [100]*20, final_bar=True, same_feed=False)
    # Nine persistent bars and three EXACTLY dependent representations of the
    # same market-price family, across20 assets: no new independent evidence.
    episode = [(asset, bar, feature) for asset in range(20)
               for bar in range(100, 109) for feature in ("return", "momentum", "volatility")]
    merged = sorted({(asset, bar) for asset, bar, _ in episode})
    cooldown = []
    last = {}
    for asset, bar in merged:
        if bar-last.get(asset, -1000) >= 4:
            cooldown.append((asset, bar)); last[asset] = bar
    # Different supported events in same asset/family within one hour: a pure
    # cooldown suppresses the second; an event-ID/material-update policy must
    # independently decide whether it qualifies, rather than treating it as a retry.
    distinct_events = [(0, 200, "event-A"), (0, 202, "event-B")]
    sent = []
    last = {}
    for asset, bar, event in distinct_events:
        if bar-last.get(asset, -1000) >= 4:
            sent.append(event); last[asset] = bar
    return {"seed": seed, "corporate_action": {"unadjusted_asserted_valid": split_raw.outcome,
            "unknown_adjustment": split_unknown.outcome, "verified_adjusted": split_adjusted.outcome},
            "provider_switch": {"unchecked_switch": feed_unguarded.outcome, "mixed_feed_guard": feed_guarded.outcome},
            "alert_flood": {"raw_correlated_feature_flags": len(episode), "same_bar_asset_merges": len(merged),
            "four_bar_cooldown_records": len(cooldown), "oracle_asset_episode_records": 20,
            "oracle_shared_market_context_records": 1, "distinct_events_inside_cooldown": len(distinct_events),
            "distinct_events_delivered_by_naive_cooldown": len(sent),
            "clustering_scope": "ORACLE_CONSTRUCTED_EPISODE_IDENTITIES; no learned or production clustering"}}


def run(seeds, batches, assets):
    volume_rows, market_rows, multiple_rows, contam_rows, leakage_rows, policy_rows = [], [], [], [], [], []
    for seed in seeds:
        volume_rows.extend(volume_experiment(seed))
        market_rows.extend(market_context_experiment(seed))
        multiple_rows.extend(multiple_testing_experiment(seed, batches, assets))
        contamination, leakage = contamination_experiment(seed)
        contam_rows.extend(contamination); leakage_rows.append(leakage)
        policy_rows.append(policy_counterexamples(seed))
    harmonic = sum(1/i for i in range(1, assets+1))
    volume_pairs = []
    for seed in seeds:
        for scenario in sorted({row['scenario'] for row in volume_rows}):
            paired = {row['method']: row for row in volume_rows if row['seed'] == seed and row['scenario'] == scenario}
            volume_pairs.append({'seed': seed, 'scenario': scenario,
                                 'pooled20_minus_slot20_false_flags_per100': paired['pooled20']['false_flags_per_100_asset_days']-paired['same_slot20']['false_flags_per_100_asset_days'],
                                 'slot20_minus_pooled20_recall': paired['same_slot20']['injected_event_recall']-paired['pooled20']['injected_event_recall']})
    return {"metadata": {"experiment_version": "market-statistics-synthetic-v1", "origin": "SYNTHETIC",
            "real_financial_observations": 0, "seeds": list(seeds), "python": platform.python_version(),
            "dependencies": "Python standard library and local offline reference.engine only",
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "reference_sha256": hashlib.sha256((ROOT/'reference/engine.py').read_bytes()).hexdigest(),
            "thresholds": {"robust_z": Z_THRESHOLD, "simple_return_floor": RETURN_FLOOR,
            "RVOL": VOLUME_THRESHOLD, "multiple_testing_q": Q},
            "design": "Fixed scenarios and thresholds; no evaluation-seed tuning. OLS fitted on disjoint prior120 observations.",
            "uncertainty": "Seed-level Monte Carlo variability conditional on this simulator; NOT a confidence interval for real markets.",
            "parameters": {"multiple_testing_batches_per_seed_scenario": batches, "multiple_testing_assets": assets}},
            "volume": {"per_seed": volume_rows, "paired_per_seed": volume_pairs,
            "paired_summary": aggregate(volume_pairs, ['scenario'], ['pooled20_minus_slot20_false_flags_per100', 'slot20_minus_pooled20_recall']),
            "summary": aggregate(volume_rows, ['scenario', 'method'],
            ['false_flags_per_100_asset_days', 'null_bar_flag_rate', 'injected_event_recall'])},
            "market_context": {"per_seed": market_rows, "summary": aggregate(market_rows, ['scenario', 'method'],
            ['idio_recall', 'market_only_asset_flag_rate', 'ordinary_flag_rate', 'beta_mean_absolute_error'])},
            "multiple_testing": {"per_seed": multiple_rows, "summary": aggregate(multiple_rows, ['scenario', 'method'],
            ['batch_FDR', 'false_rejections_per_batch', 'probability_any_false_in_batch', 'power', 'probability_any_false_in_90_batches'])},
            "contamination": {"per_seed": contam_rows, "summary": aggregate(contam_rows, ['contamination_fraction'],
            ['robust_detection', 'mean_sd_detection', 'robust_abstention'])},
            "leakage_counterexamples": leakage_rows, "policy_counterexamples": policy_rows,
            "rank_p_resolution": {"formula": "p_min=1/(n+1), for nonrandomized calibration rank p-value",
            "calibration_n20_p_min": 1/21, "calibration_n60_p_min": 1/61,
            "BH_first_rank_cutoff": Q/assets, "BY_first_rank_cutoff": Q/(assets*harmonic),
            "BH_min_calibration_n_for_one_sparse_rejection": math.ceil(assets/Q)-1,
            "BY_min_calibration_n_for_one_sparse_rejection": math.ceil(assets*harmonic/Q)-1,
            "scope": "Resolution arithmetic only; no implemented conformal validity claim."}}


def cli_lines(results):
    lines = ['MARKET STATISTICS LAB — SYNTHETIC ONLY',
             f"seeds={len(results['metadata']['seeds'])}; real_financial_observations=0; tuning=none"]
    for section, metrics in [('volume', ('false_flags_per_100_asset_days', 'injected_event_recall')),
                             ('market_context', ('market_only_asset_flag_rate', 'idio_recall')),
                             ('multiple_testing', ('batch_FDR', 'power'))]:
        for row in results[section]['summary']:
            lines.append(f"{section} {row['scenario']} {row['method']}: " + ', '.join(f"{metric}={row[metric]['mean']:.4f}" for metric in metrics))
    for row in results['contamination']['summary']:
        lines.append(f"contamination={row['contamination_fraction']:.1f}: robust_detection={row['robust_detection']['mean']:.4f}; mean_sd_detection={row['mean_sd_detection']['mean']:.4f}")
    lines.append('All outcomes are conditional synthetic stress tests; no real-market performance/calibration claim.')
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seeds', default=','.join(map(str, DEFAULT_SEEDS)))
    parser.add_argument('--batches', type=int, default=500)
    parser.add_argument('--assets', type=int, default=200)
    parser.add_argument('--output', type=Path, default=ROOT/'research/engine_lab/market_results.json')
    args = parser.parse_args()
    seeds = tuple(int(value) for value in args.seeds.split(','))
    if len(seeds) < 2 or len(set(seeds)) != len(seeds) or args.batches < 90 or args.assets < 10:
        parser.error('Need >=2 distinct seeds, >=90 batches, >=10 assets')
    results = run(seeds, args.batches, args.assets)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2, allow_nan=False)+'\n')
    log = '\n'.join(cli_lines(results))+'\n'
    args.output.with_name('market_run.log').write_text(log)
    print(log, end='')


if __name__ == '__main__':
    main()
