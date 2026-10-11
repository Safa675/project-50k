"""Pure checks for the after-the-fact comparison of the 12 September scan with the SPK list (synthetic codes only)."""
from __future__ import annotations

import unittest

from p50k.product import evaluation
from p50k.product.evaluation import FundSignals


def fund(code: str, triggered=(), assessed=None) -> FundSignals:
    """Triggered detectors are assessed too, as in stored output; extra assessed ids are NOT_TRIGGERED rows."""
    return FundSignals(code, 'Synthetic fund ' + code, frozenset(triggered), frozenset(set(triggered) | set(assessed or ())))


class FamilyTests(unittest.TestCase):
    def test_families_and_regulatory_exclusion(self):
        self.assertEqual([evaluation.family(item) for item in ('D1', 'D4', 'AN-DQ-002', 'AN-FND-005', 'D5')],
                         ['price', 'price', 'data_quality', None, None])
        for view in evaluation.VIEWS:
            self.assertFalse(evaluation.counts_in('AN-FND-005', view))
        self.assertTrue(evaluation.counts_in('AN-DQ-001', 'all'))
        self.assertFalse(evaluation.counts_in('AN-DQ-001', 'price'))
        self.assertFalse(evaluation.counts_in('D2', 'data_quality'))
        with self.assertRaisesRegex(ValueError, 'VIEW_INVALID'):
            evaluation.counts_in('D1', 'everything')


class OutcomeTests(unittest.TestCase):
    def test_outcome_matrix_keeps_abstentions_apart_from_quiet_funds(self):
        cases = [
            (fund('A', {'D1'}), True, {'all': 'caught', 'price': 'caught', 'data_quality': 'listed_not_assessable'}),
            (fund('B', {'AN-FND-005'}, {'D2'}), True, {'all': 'missed', 'price': 'missed', 'data_quality': 'listed_not_assessable'}),
            (fund('C', (), {'AN-DQ-002'}), True,
             {'all': 'listed_not_assessable', 'price': 'listed_not_assessable', 'data_quality': 'missed'}),
            (fund('D', {'AN-DQ-002'}, {'D1'}), True, {'all': 'caught', 'price': 'missed', 'data_quality': 'caught'}),
            (fund('E', {'D3'}), False, {'all': 'flagged_outside', 'price': 'flagged_outside', 'data_quality': 'other_not_assessable'}),
            (fund('F', (), {'D1', 'AN-DQ-001'}), False, {'all': 'quiet', 'price': 'quiet', 'data_quality': 'quiet'}),
            (fund('G'), False, {'all': 'other_not_assessable', 'price': 'other_not_assessable', 'data_quality': 'other_not_assessable'}),
        ]
        for item, listed, expected in cases:
            self.assertEqual({view: evaluation.outcome(item, listed, view) for view in evaluation.VIEWS}, expected, item.fund_code)

    def test_regulatory_trigger_alone_never_counts_as_a_detection(self):
        self.assertEqual(evaluation.outcome(fund('R', {'AN-FND-005'}), True, 'all'), 'listed_not_assessable')
        self.assertEqual(evaluation.fund_rows([fund('R', {'AN-FND-005'})], set()), [])


class RateTests(unittest.TestCase):
    def test_percent_rate_and_times_are_exact_decimals_or_missing(self):
        self.assertEqual(evaluation.percent(1, 3), '33.3')
        self.assertEqual(evaluation.percent(2, 3), '66.7')
        self.assertIsNone(evaluation.percent(1, 0))
        self.assertEqual(evaluation.rate(1, 8), {'numerator': 1, 'denominator': 8, 'percent': '12.5'})
        self.assertEqual(evaluation.times(evaluation.rate(1, 4), evaluation.rate(1, 20)), '5.0')
        self.assertEqual(evaluation.times(evaluation.rate(1, 3), evaluation.rate(1, 7)), '2.3')
        self.assertIsNone(evaluation.times(evaluation.rate(1, 4), evaluation.rate(0, 20)))
        self.assertIsNone(evaluation.times(evaluation.rate(0, 0), evaluation.rate(1, 20)))


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.funds = [fund('A', {'D1', 'AN-FND-005'}), fund('B', (), {'D1'}), fund('C'), fund('D', {'AN-DQ-002'}, {'D2'}),
                      fund('E', {'D4'}), fund('F', (), {'D1'}), fund('G', (), {'D2'}), fund('H')]
        self.report = evaluation.build_report({'run_id': 'synthetic-run'}, self.funds,
                                              {'A': 'Synthetic fund A', 'B': 'Synthetic fund B', 'C': 'Synthetic fund C',
                                               'Z': 'Synthetic fund Z'}, {'source': 'SPK'})

    def test_summary_counts_and_rates(self):
        summary = self.report['summaries']['all']
        self.assertEqual(summary['counts'], {'caught': 1, 'missed': 1, 'listed_not_assessable': 1, 'flagged_outside': 2,
                                             'quiet': 2, 'other_not_assessable': 1, 'listed_funds': 3, 'other_funds': 5,
                                             'flagged': 3, 'scanned': 8})
        self.assertEqual(summary['detection_rate'], {'numerator': 1, 'denominator': 3, 'percent': '33.3'})
        self.assertEqual(summary['on_list_share'], {'numerator': 1, 'denominator': 3, 'percent': '33.3'})
        self.assertEqual(summary['other_flag_rate'], {'numerator': 2, 'denominator': 5, 'percent': '40.0'})
        self.assertEqual(summary['times_more_often'], '0.8')
        self.assertEqual(summary['assessed_detection_rate'], {'numerator': 1, 'denominator': 2, 'percent': '50.0'})
        price = self.report['summaries']['price']['counts']
        self.assertEqual((price['caught'], price['flagged_outside'], price['quiet'], price['other_not_assessable']), (1, 1, 3, 1))
        quality = self.report['summaries']['data_quality']['counts']
        self.assertEqual((quality['caught'], quality['flagged_outside'], quality['listed_not_assessable']), (0, 1, 3))

    def test_lists_ground_truth_and_method(self):
        rows = {row['fund_code']: row for row in self.report['funds']}
        self.assertEqual(sorted(rows), ['A', 'B', 'C', 'D', 'E'])
        self.assertEqual(rows['A']['detectors'], ['D1'])
        self.assertEqual(rows['A']['href'], '/funds/A')
        self.assertEqual(rows['C']['outcomes']['all'], 'listed_not_assessable')
        self.assertEqual(rows['D']['outcomes'], {'all': 'flagged_outside', 'price': 'quiet', 'data_quality': 'flagged_outside'})
        self.assertEqual(self.report['ground_truth']['listed_total'], 4)
        self.assertEqual(self.report['ground_truth']['outside_scan'], [{'fund_code': 'Z', 'name': 'Synthetic fund Z'}])
        self.assertEqual(set(self.report['detectors']), {'D1', 'D4', 'AN-DQ-002'})
        self.assertEqual(self.report['detectors']['D1']['family'], 'price')
        self.assertTrue(self.report['detectors']['D1']['label'])
        self.assertEqual(self.report['method']['excluded_detectors'], ['AN-FND-005'])
        self.assertFalse(self.report['method']['feeds_detectors_or_agents'])
        self.assertTrue(self.report['method']['after_the_fact'])

    def test_empty_run_has_no_rates(self):
        report = evaluation.build_report({'run_id': 'empty'}, [], {}, {})
        summary = report['summaries']['all']
        self.assertEqual(summary['counts']['scanned'], 0)
        self.assertIsNone(summary['detection_rate']['percent'])
        self.assertIsNone(summary['times_more_often'])
        self.assertEqual(report['funds'], [])

    def test_scan_cutoff_is_the_end_of_the_istanbul_day(self):
        cutoff = evaluation.scan_cutoff()
        self.assertEqual((cutoff.date().isoformat(), cutoff.hour, cutoff.minute), ('2026-09-12', 23, 59))
        self.assertEqual(cutoff.utcoffset().total_seconds(), 3 * 3600)


if __name__ == '__main__':
    unittest.main()
