"""Synthetic boundaries and look-ahead checks for the isolated monthly rule."""
from __future__ import annotations
from datetime import datetime,timedelta
from decimal import Decimal
from unittest import TestCase
from p50k.product.archive import ISTANBUL
from p50k.product.kap_experiment import Monthly,classify

CUTOFF=datetime(2030,9,12,23,59,59,tzinfo=ISTANBUL)
def row(period,value,units,**kwargs):
    return Monthly(period,Decimal(value) if value is not None else None,Decimal(units) if units is not None else None,
                   kwargs.get('published',CUTOFF-timedelta(days=10)),kwargs.get('available',CUTOFF-timedelta(days=10)),kwargs.get('ambiguous',False))

class MonthlyRuleTests(TestCase):
    def test_both_measures_must_cross_the_inclusive_same_direction_boundary(self):
        first=row('2030-07','100','100')
        for value,units,state in [('200','200','FLAGGED'),('50','50','FLAGGED'),('200','199','NOT_FLAGGED'),('200','50','NOT_FLAGGED'),('101','101','NOT_FLAGGED')]:
            self.assertEqual(classify([first,row('2030-08',value,units)],CUTOFF)['state'],state)

    def test_missing_nonpositive_ambiguous_and_period_gaps_abstain(self):
        first=row('2030-07','100','100')
        for last in [row('2030-08',None,'300'),row('2030-08','0','300'),row('2030-08','300','-1'),row('2030-08','300','300',ambiguous=True),row('2030-05','300','300')]:
            self.assertEqual(classify([first,last],CUTOFF)['state'],'ABSTAINED')
        self.assertEqual(classify([first],CUTOFF)['state'],'ABSTAINED')

    def test_future_unknown_availability_and_unfinished_period_never_change_output(self):
        pair=[row('2030-07','100','100'),row('2030-08','110','110')]
        original=classify(pair,CUTOFF)
        for future in [row('2030-08','300','300',available=CUTOFF+timedelta(seconds=1)),row('2030-08','300','300',published=CUTOFF+timedelta(seconds=1)),row('2030-09','300','300'),row('2030-08','300','300',published=None),row('2030-08','300','300',available=None)]:
            self.assertEqual(classify([*pair,future],CUTOFF),original)

    def test_year_boundary_is_consecutive_and_latest_missing_never_uses_older_value(self):
        self.assertEqual(classify([row('2029-12','100','100'),row('2030-01','200','200')],CUTOFF)['state'],'FLAGGED')
        self.assertEqual(classify([row('2030-06','100','100'),row('2030-07','200','200'),row('2030-08',None,None)],CUTOFF)['state'],'ABSTAINED')
