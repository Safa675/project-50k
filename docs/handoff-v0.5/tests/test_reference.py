import math
import unittest
from decimal import Decimal, Inexact, ROUND_UP, localcontext
from reference.engine import (InvalidEvidence, allocation_distance, delivery_key,
    eligible_evidence, email_eligible, estimated_fund_flow, evidence_strength,
    normalize_borsapy_fund_history, parse_timestamp, relative_volume, robust_return_signal)

class MarketTests(unittest.TestCase):
    def test_volume_candidate(self):
        r=relative_volume(600,[100]*20,final_bar=True,same_feed=True)
        self.assertEqual(r.outcome,'CANDIDATE'); self.assertEqual(r.metric,6)
    def test_volume_normal(self):
        self.assertEqual(relative_volume(120,[100]*20,final_bar=True,same_feed=True).outcome,'NOT_FLAGGED')
    def test_incomplete_bar(self):
        self.assertEqual(relative_volume(600,[100]*20,final_bar=False,same_feed=True).outcome,'ABSTAINED')
    def test_mixed_feed(self):
        self.assertEqual(relative_volume(600,[100]*20,final_bar=True,same_feed=False).outcome,'ABSTAINED')
    def test_short_baseline(self):
        self.assertEqual(relative_volume(600,[100]*19,final_bar=True,same_feed=True).outcome,'ABSTAINED')
    def test_zero_volume(self):
        self.assertEqual(relative_volume(600,[0]*20,final_bar=True,same_feed=True).outcome,'ABSTAINED')
    def test_negative_volume(self):
        self.assertEqual(relative_volume(-1,[100]*20,final_bar=True,same_feed=True).outcome,'ABSTAINED')
    def test_nan_volume(self):
        self.assertEqual(relative_volume(float('nan'),[100]*20,final_bar=True,same_feed=True).outcome,'ABSTAINED')
    def test_boolean_rejected(self):
        self.assertEqual(relative_volume(True,[100]*20,final_bar=True,same_feed=True).outcome,'ABSTAINED')
    def test_return_candidate(self):
        self.assertEqual(robust_return_signal(math.log(1.08),[-.001,.001]*10,adjustment_verified=True).outcome,'CANDIDATE')
    def test_return_zero_mad(self):
        self.assertEqual(robust_return_signal(.1,[0]*20,adjustment_verified=True).outcome,'ABSTAINED')
    def test_return_unadjusted(self):
        self.assertEqual(robust_return_signal(.1,[-.001,.001]*10,adjustment_verified=False).outcome,'ABSTAINED')
    def test_absolute_floor(self):
        self.assertEqual(robust_return_signal(.002,[-.0001,.0001]*10,adjustment_verified=True).outcome,'NOT_FLAGGED')
    def test_infinite_return(self):
        self.assertEqual(robust_return_signal(float('inf'),[-.001,.001]*10,adjustment_verified=True).outcome,'ABSTAINED')

class FundTests(unittest.TestCase):
    def flow(self,*args,**kw):return estimated_fund_flow(*args,dates_aligned=kw.get('aligned',True),distribution_adjustment_verified=kw.get('adjusted',True))
    def test_price_only_decline(self): self.assertEqual(self.flow('1000','900','10','9'),Decimal('0'))
    def test_outflow(self): self.assertEqual(self.flow('1000','700','10','9'),Decimal('-200'))
    def test_inflow(self): self.assertEqual(self.flow('1000','1200','10','11'),Decimal('100'))
    def test_misaligned_dates(self):
        with self.assertRaises(InvalidEvidence):self.flow('1000','900','10','9',aligned=False)
    def test_distribution_unknown(self):
        with self.assertRaises(InvalidEvidence):self.flow('1000','900','10','9',adjusted=False)
    def test_zero_nav(self):
        with self.assertRaises(InvalidEvidence):self.flow('1000','900','0','9')
    def test_nan_aum(self):
        with self.assertRaises(InvalidEvidence):self.flow('NaN','900','10','9')
    def test_placeholders_missing(self):
        r=normalize_borsapy_fund_history({'Price':'1.2','FundSize':float('nan'),'Investors':0})
        self.assertIsNone(r['FundSize']);self.assertIsNone(r['Investors']);self.assertEqual(r['Price'],'1.2')
    def test_allocation_shift(self):self.assertEqual(allocation_distance({'stocks':'40','cash':'60'},{'stocks':'80','cash':'20'},complete_category_map=True),Decimal('.4'))
    def test_signed_allocation_rejected(self):
        with self.assertRaises(InvalidEvidence):allocation_distance({'stocks':'100'},{'stocks':'114','repo':'-14'},complete_category_map=True)
    def test_incomplete_allocation_rejected(self):
        with self.assertRaises(InvalidEvidence):allocation_distance({'stocks':'40'},{'stocks':'80'},complete_category_map=True)
    def test_unknown_category_map(self):
        with self.assertRaises(InvalidEvidence):allocation_distance({'stocks':'100'},{'cash':'100'},complete_category_map=False)

class TemporalTests(unittest.TestCase):
    def test_naive_rejected(self):
        with self.assertRaises(InvalidEvidence):parse_timestamp('2026-10-01T10:00:00')
    def test_offsets_equivalent(self):self.assertEqual(parse_timestamp('2026-10-01T10:00:00Z'),parse_timestamp('2026-10-01T13:00:00+03:00'))
    def test_replay_future_excluded(self):
        rows=[{'available_at':'2026-10-01T12:00:00Z','published_at':'2026-10-01T11:59:00Z','availability_provenance':'OBSERVED'}, {'available_at':'2026-10-01T12:01:00Z','availability_provenance':'OBSERVED'}]
        self.assertEqual(len(eligible_evidence(rows,'2026-10-01T12:00:00Z')),1)
    def test_future_publication_excluded(self):
        row={'available_at':'2026-10-01T11:00:00Z','published_at':'2026-10-01T13:00:00Z','availability_provenance':'OBSERVED'}
        self.assertEqual(eligible_evidence([row],'2026-10-01T12:00:00Z'),[])
    def test_unknown_availability_excluded(self):
        row={'available_at':'2026-10-01T11:00:00Z','availability_provenance':'UNKNOWN'}
        self.assertEqual(eligible_evidence([row],'2026-10-01T12:00:00Z'),[])

class ConfidenceTests(unittest.TestCase):
    c={'completeness':1,'freshness':1,'integrity':1,'corroboration':1}
    def test_not_probability(self):
        r=evidence_strength(self.c,hard_gates_pass=True);self.assertEqual(r['evidence_score'],100);self.assertIsNone(r['calibrated_probability'])
    def test_fatal_gate(self):self.assertIsNone(evidence_strength(self.c,hard_gates_pass=False)['evidence_score'])
    def test_out_of_range(self):
        with self.assertRaises(InvalidEvidence):evidence_strength({**self.c,'freshness':2},hard_gates_pass=True)
    def test_missing_component(self):
        with self.assertRaises(InvalidEvidence):evidence_strength({'freshness':1},hard_gates_pass=True)
    def test_nan_component(self):
        with self.assertRaises(InvalidEvidence):evidence_strength({**self.c,'freshness':float('nan')},hard_gates_pass=True)

class NotificationTests(unittest.TestCase):
    args=dict(origin='LIVE',severity='HIGH',follows_asset=True,personal_opt_in=True,global_opt_in=False,global_release_approved=False,current_subscription=True,evidence_valid=True,external_sending_enabled=True,evidence_origins=['LIVE'],dry_run=False)
    def eligible(self,**kw):return email_eligible(**{**self.args,**kw})
    def test_personal_high(self):self.assertTrue(self.eligible())
    def test_medium_no_immediate(self):self.assertFalse(self.eligible(severity='MEDIUM'))
    def test_replay_never_email(self):self.assertFalse(self.eligible(origin='HISTORICAL_REPLAY'))
    def test_synthetic_never_email(self):self.assertFalse(self.eligible(origin='SYNTHETIC'))
    def test_no_global_opt_in(self):self.assertFalse(self.eligible(follows_asset=False,severity='CRITICAL',global_release_approved=True))
    def test_no_global_release(self):self.assertFalse(self.eligible(follows_asset=False,severity='CRITICAL',global_opt_in=True))
    def test_global_approved(self):self.assertTrue(self.eligible(follows_asset=False,severity='CRITICAL',global_opt_in=True,global_release_approved=True))
    def test_unsubscribe_recheck(self):self.assertFalse(self.eligible(current_subscription=False))
    def test_no_evidence(self):self.assertFalse(self.eligible(evidence_valid=False))
    def test_disabled_sender(self):self.assertFalse(self.eligible(external_sending_enabled=False))
    def test_duplicate(self):self.assertFalse(self.eligible(already_sent=True))
    def test_daily_cap(self):self.assertFalse(self.eligible(under_daily_cap=False))
    def test_unknown_mode(self):self.assertFalse(self.eligible(origin='SOMETHING'))
    def test_stable_key(self):
        kw=dict(user_id='u',event_id='e',channel='EMAIL',origin='LIVE',delivery_class='PERSONAL')
        self.assertEqual(delivery_key(**kw),delivery_key(**kw))
        self.assertNotEqual(delivery_key(**kw),delivery_key(**{**kw,'origin':'SYNTHETIC'}))
    def test_update_needs_id(self):
        with self.assertRaises(InvalidEvidence):delivery_key(user_id='u',event_id='e',channel='EMAIL',origin='LIVE',delivery_class='UPDATE')


class MarketIntegrityTests(unittest.TestCase):
    def test_nonfinite_threshold_configuration_rejected(self):
        for threshold in (float('nan'), float('inf'), -float('inf'), True, '3'):
            with self.subTest(threshold=threshold):
                with self.assertRaises(ValueError):
                    relative_volume(600, [100]*20, final_bar=True, same_feed=True, threshold=threshold)
                with self.assertRaises(ValueError):
                    robust_return_signal(.1, [-.001, .001]*10, adjustment_verified=True, threshold=threshold)

    def test_nonfinite_absolute_floor_rejected(self):
        for floor in (float('nan'), float('inf'), True, '0.01'):
            with self.subTest(floor=floor), self.assertRaises(ValueError):
                robust_return_signal(.1, [-.001, .001]*10, adjustment_verified=True, absolute_return_floor=floor)

    def test_noninteger_baseline_configuration_rejected(self):
        for minimum in (True, 1, 2.5, '20'):
            with self.subTest(minimum=minimum), self.assertRaises(ValueError):
                relative_volume(600, [100]*20, final_bar=True, same_feed=True, min_observations=minimum)

    def test_provenance_flags_must_be_boolean_true(self):
        for flag in (1, 'false', None):
            with self.subTest(flag=flag):
                self.assertEqual(relative_volume(600, [100]*20, final_bar=flag, same_feed=True).outcome, 'ABSTAINED')
                self.assertEqual(relative_volume(600, [100]*20, final_bar=True, same_feed=flag).outcome, 'ABSTAINED')
                self.assertEqual(robust_return_signal(.1, [-.001, .001]*10, adjustment_verified=flag).outcome, 'ABSTAINED')

    def test_rvol_overflow_abstains(self):
        result = relative_volume(1e308, [1e-308]*20, final_bar=True, same_feed=True)
        self.assertEqual(result.outcome, 'ABSTAINED')
        self.assertIsNone(result.metric)

    def test_float_conversion_overflow_abstains(self):
        self.assertEqual(relative_volume(10**400, [100]*20, final_bar=True, same_feed=True).outcome, 'ABSTAINED')

    def test_return_derived_metric_overflow_abstains(self):
        for history in ([-1e-320, 1e-320]*10, [1e308]*20):
            with self.subTest(history=history):
                result = robust_return_signal(.1, history, adjustment_verified=True)
                self.assertEqual(result.outcome, 'ABSTAINED')
                self.assertIsNone(result.metric)


class FundIntegrityTests(unittest.TestCase):
    def test_flow_independent_of_ambient_decimal_context(self):
        for precision in (6, 28):
            with self.subTest(precision=precision), localcontext() as context:
                context.prec = precision
                context.rounding = ROUND_UP
                context.traps[Inexact] = True
                flow = estimated_fund_flow('123456789', '900', '3', '10', dates_aligned=True, distribution_adjustment_verified=True)
                self.assertEqual(flow, Decimal('-411521730'))

    def test_flow_avoids_repeating_ratio_residual(self):
        self.assertEqual(estimated_fund_flow('3', '1', '3', '1', dates_aligned=True, distribution_adjustment_verified=True), Decimal('0'))

    def test_fund_validity_flags_must_be_boolean_true(self):
        for flag in (1, 'false', None):
            with self.subTest(flag=flag):
                with self.assertRaises(InvalidEvidence):
                    estimated_fund_flow('1000', '900', '10', '9', dates_aligned=flag, distribution_adjustment_verified=True)
                with self.assertRaises(InvalidEvidence):
                    estimated_fund_flow('1000', '900', '10', '9', dates_aligned=True, distribution_adjustment_verified=flag)
                with self.assertRaises(InvalidEvidence):
                    allocation_distance({'stocks': '100'}, {'cash': '100'}, complete_category_map=flag)

    def test_allocation_outside_fraction_range_rejected(self):
        with self.assertRaises(InvalidEvidence):
            allocation_distance({'stocks': '100.1'}, {'cash': '100.1'}, complete_category_map=True)

    def test_rounded_allocation_is_not_silently_normalized(self):
        self.assertEqual(allocation_distance({'stocks': '100'}, {'stocks': '99.95', 'cash': '.1'}, complete_category_map=True), Decimal('.00075'))

    def test_allocation_independent_of_ambient_decimal_context(self):
        for precision in (6, 28):
            with self.subTest(precision=precision), localcontext() as context:
                context.prec = precision
                context.traps[Inexact] = True
                distance = allocation_distance({'stocks': '99.999999', 'cash': '.000001'}, {'stocks': '80', 'cash': '20'}, complete_category_map=True)
                self.assertEqual(distance, Decimal('.19999999'))

    def test_invalid_allocation_category_id_rejected(self):
        for key in ('', 1):
            with self.subTest(key=key), self.assertRaises(InvalidEvidence):
                allocation_distance({key: '100'}, {'cash': '100'}, complete_category_map=True)

    def test_decimal_calculation_overflow_rejected(self):
        with self.assertRaises(InvalidEvidence):
            estimated_fund_flow('1e999999', '1', '1', '10', dates_aligned=True, distribution_adjustment_verified=True)


class TemporalIntegrityTests(unittest.TestCase):
    cutoff = '2026-10-01T12:00:00Z'
    row = {'available_at': '2026-10-01T11:00:00Z', 'availability_provenance': 'OBSERVED'}

    def test_invalid_row_does_not_abort_other_eligible_evidence(self):
        for invalid in ('bad', None, 42, '2026-10-01T11:00:00'):
            with self.subTest(invalid=invalid):
                self.assertEqual(eligible_evidence([{**self.row, 'available_at': invalid}, self.row], self.cutoff), [self.row])

    def test_malformed_optional_times_excluded(self):
        for key in ('published_at', 'observed_at', 'effective_at'):
            with self.subTest(key=key):
                self.assertEqual(eligible_evidence([{**self.row, key: 'bad'}], self.cutoff), [])

    def test_future_observation_and_effective_instants_excluded(self):
        for key in ('observed_at', 'effective_at'):
            with self.subTest(key=key):
                self.assertEqual(eligible_evidence([{**self.row, key: '2026-10-01T12:00:01Z'}], self.cutoff), [])

    def test_exact_cutoff_and_offset_comparison(self):
        row = {**self.row, 'available_at': '2026-10-01T15:00:00+03:00'}
        self.assertEqual(eligible_evidence([row], self.cutoff), [row])

    def test_later_source_revision_excluded_by_own_availability(self):
        original = {**self.row, 'source_version': 'v1', 'values': {'amount': '10'}}
        revision = {**original, 'source_version': 'v2', 'available_at': '2026-10-01T12:01:00Z', 'values': {'amount': '20'}}
        self.assertEqual(eligible_evidence([original, revision], self.cutoff), [original])

    def test_filter_does_not_claim_to_select_latest_revision(self):
        original = {**self.row, 'source_version': 'v1'}
        revision = {**self.row, 'source_version': 'v2', 'available_at': '2026-10-01T11:30:00Z'}
        self.assertEqual(eligible_evidence([original, revision], self.cutoff), [original, revision])

    def test_invalid_cutoff_raises(self):
        with self.assertRaises(InvalidEvidence):
            eligible_evidence([self.row], 'bad')

    def test_nonrecords_and_unknown_provenance_excluded(self):
        self.assertEqual(eligible_evidence([None, {**self.row, 'availability_provenance': []}], self.cutoff), [])

    def test_rfc3339_shape_unknown_offset_and_precision_rejected(self):
        for value in ('20261001T120000Z', '2026-10-01 12:00:00Z', '2026-10-01T12:00:00-00:00', '2026-10-01T12:00:00.0000001Z', '2026-10-01T12:00:00+0000'):
            with self.subTest(value=value), self.assertRaises(InvalidEvidence):
                parse_timestamp(value)


class ConfidenceIntegrityTests(unittest.TestCase):
    def test_half_up_rounding_at_display_boundary(self):
        for component, expected in ((.005, 1), (.025, 3), (.145, 15), (.285, 29), (.745, 75)):
            with self.subTest(component=component):
                result = evidence_strength(dict.fromkeys(ConfidenceTests.c, component), hard_gates_pass=True)
                self.assertEqual(result['evidence_score'], expected)

    def test_score_uses_decimal_values_before_float_rounding(self):
        components = {**ConfidenceTests.c, 'corroboration': Decimal('1.00000000000000000001')}
        with self.assertRaises(InvalidEvidence):
            evidence_strength(components, hard_gates_pass=True)

    def test_hard_gate_must_be_boolean(self):
        for gate in (1, 'false', None):
            with self.subTest(gate=gate), self.assertRaises(InvalidEvidence):
                evidence_strength(ConfidenceTests.c, hard_gates_pass=gate)

    def test_boolean_component_rejected(self):
        with self.assertRaises(InvalidEvidence):
            evidence_strength({**ConfidenceTests.c, 'freshness': True}, hard_gates_pass=True)

    def test_confidence_independent_of_ambient_decimal_context(self):
        with localcontext() as context:
            context.prec = 2
            context.traps[Inexact] = True
            self.assertEqual(evidence_strength(dict.fromkeys(ConfidenceTests.c, .745), hard_gates_pass=True)['evidence_score'], 75)


class NotificationIntegrityTests(unittest.TestCase):
    args = NotificationTests.args
    key_args = dict(user_id='u', event_id='e', channel='EMAIL', origin='LIVE', delivery_class='PERSONAL')

    def test_truthy_nonboolean_policy_flags_fail_closed(self):
        for field in ('follows_asset', 'personal_opt_in', 'global_opt_in', 'global_release_approved', 'current_subscription', 'evidence_valid', 'external_sending_enabled', 'already_sent', 'under_daily_cap', 'dry_run'):
            with self.subTest(field=field):
                self.assertFalse(email_eligible(**{**self.args, field: 'false'}))
                self.assertFalse(email_eligible(**{**self.args, field: 1}))

    def test_missing_evidence_origin_metadata_fail_closed(self):
        for origins in (None, [], 'LIVE', ['UNKNOWN'], ['LIVE', None]):
            with self.subTest(origins=origins):
                self.assertFalse(email_eligible(**{**self.args, 'evidence_origins': origins}))

    def test_live_event_with_synthetic_or_replay_evidence_never_email(self):
        for origin in ('SYNTHETIC', 'HISTORICAL_REPLAY'):
            with self.subTest(origin=origin):
                self.assertFalse(email_eligible(**{**self.args, 'evidence_origins': ['LIVE', origin]}))

    def test_known_live_and_delayed_evidence_can_qualify(self):
        self.assertTrue(email_eligible(**{**self.args, 'origin': 'DELAYED', 'evidence_origins': ['LIVE', 'DELAYED']}))

    def test_dry_run_is_default_and_blocks_eligibility(self):
        args = {key: value for key, value in self.args.items() if key != 'dry_run'}
        self.assertFalse(email_eligible(**args))
        self.assertFalse(email_eligible(**{**self.args, 'dry_run': True}))

    def test_initial_key_rejects_explanation_rewrite_id(self):
        with self.assertRaises(InvalidEvidence):
            delivery_key(**self.key_args, material_update_id='rewrite-2')

    def test_delivery_key_rejects_unknown_enum_or_empty_identity(self):
        for overrides in ({'channel': 'PUSH'}, {'origin': 'UNKNOWN'}, {'delivery_class': 'REWRITE'}, {'user_id': ''}, {'event_id': ' '}):
            with self.subTest(overrides=overrides), self.assertRaises(InvalidEvidence):
                delivery_key(**{**self.key_args, **overrides})

    def test_material_update_keys_stable_and_separate_from_correction(self):
        args = {**self.key_args, 'delivery_class': 'UPDATE', 'material_update_id': 'approved-1'}
        self.assertEqual(delivery_key(**args), delivery_key(**args))
        self.assertNotEqual(delivery_key(**args), delivery_key(**{**args, 'delivery_class': 'CORRECTION'}))
        self.assertNotEqual(delivery_key(**args), delivery_key(**{**args, 'material_update_id': 'approved-2'}))

if __name__=='__main__':unittest.main(verbosity=2)
