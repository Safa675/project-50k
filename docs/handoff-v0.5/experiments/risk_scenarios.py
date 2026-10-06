"""Authored arithmetic sensitivity scenarios; no fitted rates, vendor quotes or market data."""
from fractions import Fraction as F
from decimal import Decimal, localcontext
from pathlib import Path
import argparse, json, hashlib

ROOT = Path(__file__).resolve().parents[1]
def number(x):
    with localcontext() as ctx:
        ctx.prec = 30
        return str(Decimal(x.numerator)/Decimal(x.denominator))
def precision_case(prevalence, sensitivity, false_positive_rate, decisions=100000):
    p, s, f = map(F, [prevalence, sensitivity, false_positive_rate])
    if not all(0 <= x <= 1 for x in [p, s, f]) or decisions < 0:
        raise ValueError('Rates must be in [0,1] and opportunity count nonnegative')
    tp = decisions*p*s
    fn = decisions*p*(1-s)
    fp = decisions*(1-p)*f
    tn = decisions*(1-p)*(1-f)
    assert tp+fn+fp+tn == decisions
    positive_probability = p*s+(1-p)*f
    ratio = p*s/positive_probability if positive_probability else None
    return {'prevalence': number(p), 'sensitivity': number(s), 'false_positive_rate': number(f), 'decision_opportunities': decisions, 'expected_true_positive_count':number(tp), 'expected_false_positive_count':number(fp), 'expected_false_negative_count':number(fn), 'population_positive_predictive_value':number(ratio) if ratio is not None else None}
def run():
    rates = ['0.0001','0.001','0.01','0.05']
    cases=[precision_case(p,'0.8',f) for p in rates for f in rates]
    invariants=[]
    def check(name, value):
        assert value, name
        invariants.append({'name':name, 'passed':True})
    check('Zero population positive probability is undefined precision, not perfect or zero',precision_case('0','0.8','0')['population_positive_predictive_value'] is None)
    check('Zero sample opportunities do not change defined population PPV',precision_case('.001','.8','.01',0)['population_positive_predictive_value']==precision_case('.001','.8','.01',100000)['population_positive_predictive_value'])
    check('Zero false-positive rate with positive sensitivity gives precision one',precision_case('.001','.8','0')['population_positive_predictive_value']=='1')
    check('Zero sensitivity with nonzero false positives gives precision zero',precision_case('.001','0','.01')['population_positive_predictive_value']=='0')
    for p in rates:
        values=[F(precision_case(p,'.8',f)['population_positive_predictive_value']) for f in rates]
        check('Precision decreases with FPR at prevalence '+p, all(a>b for a,b in zip(values,values[1:])))
    for f in rates:
        values=[F(precision_case(p,'.8',f)['population_positive_predictive_value']) for p in rates]
        check('Precision increases with prevalence at FPR '+f, all(a<b for a,b in zip(values,values[1:])))
    point_burden=[]
    for assets in [100,1000]:
        for bars in [1,78]:
            for f in ['.001','.01']:
                n=assets*bars
                point_burden.append({'eligible_assets':assets, 'eligible_completed_observations_per_asset_day':bars, 'all_null_assumption':True, 'false_positive_rate_assumption':number(F(f)), 'eligible_observation_decisions':n, 'expected_false_point_candidates':number(n*F(f)), 'event_or_notification_count':None})
    ceiling, upfront, reserve = F(5000), F(1000), F(500)
    recurring=[]
    for monthly in [0,200,1000,3000]:
        remaining=ceiling-upfront-reserve
        runway=remaining/monthly if monthly else None
        recurring.append({'ceiling_TRY':number(ceiling), 'invented_upfront_TRY':number(upfront), 'invented_reserved_TRY':number(reserve), 'remaining_for_recurring_TRY':number(remaining), 'invented_all_in_monthly_TRY':str(monthly), 'modeled_fractional_months':number(runway) if runway is not None else None, 'whole_months_fundable':int(runway) if runway is not None else None, 'zero_burn_interpretation':'No finite modeled limit from this term alone; not free-operation proof' if monthly==0 else None})
    quota=[]
    for users in [10,100]:
        for daily in [2,10]:
            turns=users*daily*30
            remaining=ceiling-upfront-reserve
            quota.append({'active_users_assumption':users, 'daily_turns_per_user_assumption':daily, 'days_assumption':30, 'turns':turns, 'remaining_after_invented_setup_reserve_TRY':number(remaining), 'max_average_cost_TRY_per_turn_if_ALL_remaining_were_used_for_chat':number(remaining/turns), 'excluded_further_expenses_warning':'This maximum leaves no remaining recurring data/hosting/email costs unless already included in assumptions; event investigations and retries are additional workload.'})
    check('100 users at quota cap produce 30000 monthly turns',quota[-1]['turns']==30000)
    check('Cumulative budget is not reset per month',recurring[2]['whole_months_fundable']==3)
    check('Zero recurring term does not assert actual unlimited lifetime',recurring[0]['modeled_fractional_months'] is None and bool(recurring[0]['zero_burn_interpretation']))
    return {'experiment':'Project risk arithmetic sensitivity', 'origin':'SYNTHETIC', 'rates_are_assumptions':True, 'prices_are_assumptions':True, 'actual_provider_quotes':False, 'real_observations':0, 'external_calls':0, 'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'assumptions':'A binary target and population conditional rates are specified by hand; PPV is a ratio of expected counts/Bayes population quantity, not mean realized finite-sample precision. No temporal independence is needed for expected point counts; dependence and episode grouping matter for distribution and event/notification counts, which are not inferred.', 'precision_cases':cases, 'point_candidate_burden':point_burden, 'cumulative_budget_scenarios':recurring, 'chat_quota_pressure':quota, 'arithmetic_invariants':invariants, 'not_established':['Real prevalence, sensitivity or false-positive rate','Notification precision or expected user harm','Unseen detector validity','Market-data rights or provider eligibility','Actual price, tokens, latency or project runway','Customer demand or willingness to pay']}
if __name__ == '__main__':
    a=argparse.ArgumentParser()
    a.add_argument('--output',type=Path,default=ROOT/'research/risk_review/risk_scenario_results.json')
    args=a.parse_args()
    result=run()
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'precision_cases':len(result['precision_cases']), 'point_burden_scenarios':len(result['point_candidate_burden']), 'budget_scenarios':len(result['cumulative_budget_scenarios']), 'quota_scenarios':len(result['chat_quota_pressure']), 'arithmetic_invariants':len(result['arithmetic_invariants']), 'status':'PASS arithmetic only'},indent=2))
