#!/usr/bin/env python3
"""Synthetic metric counterexample: no trained detector or real market data.
Label-aware adjustment deliberately uses the full future-labeled interval.
Random predictions never see labels. This is not a deployed scoring policy.
"""
from pathlib import Path
import argparse, hashlib, json, math, random, statistics
SEEDS=tuple(61001+977*i for i in range(32))
N=20000
STARTS=(1000,6000,11000,16000)
LENGTHS=(20,200,1000)
FLAG_PROBABILITY=.0025
EARLY_WINDOW=10

def metrics(predictions,labels):
    tp=sum(p and y for p,y in zip(predictions,labels));fp=sum(p and not y for p,y in zip(predictions,labels));fn=sum(not p and y for p,y in zip(predictions,labels))
    precision=tp/(tp+fp) if tp+fp else 0.;recall=tp/(tp+fn) if tp+fn else 0.
    return {'tp':tp,'fp':fp,'fn':fn,'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0.}

def summary(values):
    n=len(values);mean=statistics.mean(values);se=statistics.stdev(values)/math.sqrt(n)
    return {'mean':mean,'mc_standard_error':se,'approximate_mc_95_interval':[mean-1.96*se,mean+1.96*se],'scope':'Normal approximation across fixed independent PRNG seeds, conditional on constructed process; not financial uncertainty.'}

def run():
    per_seed=[]
    for seed in SEEDS:
        rng=random.Random(seed);flags=[rng.random()<FLAG_PROBABILITY for _ in range(N)]
        for length in LENGTHS:
            labels=[False]*N;adjusted=flags.copy();hits=early=0;delays=[]
            for start in STARTS:
                end=start+length;labels[start:end]=[True]*length;offsets=[j for j in range(length) if flags[start+j]]
                if offsets:
                    hits+=1;delays.append(offsets[0]);adjusted[start:end]=[True]*length;early+=offsets[0]<EARLY_WINDOW
            raw=metrics(flags,labels);pa=metrics(adjusted,labels)
            assert pa['fp']==raw['fp'] and pa['recall']>=raw['recall']
            per_seed.append({'seed':seed,'interval_length':length,'positive_points':sum(labels),'input_hash':hashlib.sha256(bytes(flags)+bytes(labels)).hexdigest(),'raw':raw,'point_adjusted':pa,'any_hit_interval_recall':hits/len(STARTS),'first_10_point_interval_recall':early/len(STARTS),'conditional_mean_first_hit_delay_points':statistics.mean(delays) if delays else None,'actual_raw_flag_count':sum(flags),'adjustment_uses_full_labeled_segment':True})
    rows=[]
    for length in LENGTHS:
        group=[r for r in per_seed if r['interval_length']==length]
        rows.append({'interval_length':length,'positive_fraction':len(STARTS)*length/N,'raw_f1':summary([r['raw']['f1'] for r in group]),'point_adjusted_f1':summary([r['point_adjusted']['f1'] for r in group]),'raw_point_recall':summary([r['raw']['recall'] for r in group]),'any_hit_interval_recall':summary([r['any_hit_interval_recall'] for r in group]),'first_10_point_interval_recall':summary([r['first_10_point_interval_recall'] for r in group]),'analytic_any_hit_probability':1-(1-FLAG_PROBABILITY)**length,'analytic_first_10_hit_probability':1-(1-FLAG_PROBABILITY)**min(length,EARLY_WINDOW)})
    return {'origin':'SYNTHETIC','design_frozen_before_run':True,'seeds':list(SEEDS),'sequence_length':N,'starts':list(STARTS),'interval_lengths':list(LENGTHS),'flag_probability':FLAG_PROBABILITY,'early_window_points':EARLY_WINDOW,'models_trained':0,'real_financial_observations':0,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scored_seed_length_pairs':len(per_seed),'summary':rows,'per_seed':per_seed,'claim_boundary':'Counterexample to retrospective point-adjusted F1 as proof of timely financial detection. Not paper replication, benchmark ranking, tuning or real detector performance.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=run();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    for row in r['summary']:print(f"length={row['interval_length']}: raw F1={row['raw_f1']['mean']:.6f}, adjusted F1={row['point_adjusted_f1']['mean']:.6f}, any-hit recall={row['any_hit_interval_recall']['mean']:.6f}, early recall={row['first_10_point_interval_recall']['mean']:.6f}")
    print('SYNTHETIC random flags; zero trained models/market observations; no financial performance claim.')
if __name__=='__main__':main()
