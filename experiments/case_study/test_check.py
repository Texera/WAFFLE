import unittest
from check import compare

class CheckTests(unittest.TestCase):
    def test_multiset_and_float_tolerance(self):
        compare([{'v':1.,'x':'a'},{'v':2.,'x':'a'}],[{'x':'a','v':2.},{'x':'a','v':1.+1e-11}])
        for bad in [[{'v':1.,'x':'a'}],[{'v':1.,'x':'a'},{'v':1.,'x':'a'}],[{'v':1.1,'x':'a'},{'v':2.,'x':'a'}]]:
            with self.assertRaises(AssertionError):compare([{'v':1.,'x':'a'},{'v':2.,'x':'a'}],bad)
    def test_types_columns_and_missing(self):
        compare([{'v':None}],[{'v':None}])
        for bad in [[{'v':0}],[{'other':None}],[{'v':'1'}]]:
            with self.assertRaises(AssertionError):compare([{'v':None}],bad)
    def test_undefined_statistic_is_not_missing_or_zero(self):
        compare([{'v':{'__float__':'NaN'}}],[{'v':{'__float__':'NaN'}}])
        for value in [None,0,'NaN']:
            with self.assertRaises(AssertionError):compare([{'v':{'__float__':'NaN'}}],[{'v':value}])

if __name__=='__main__':unittest.main()
