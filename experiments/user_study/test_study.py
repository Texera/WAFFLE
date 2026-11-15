import tempfile
from pathlib import Path
import unittest
from model import make_data, scores, expected, compare, check_evidence
import waffle


class StudyTests(unittest.TestCase):
    def test_native_readers_and_aggregate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); meta=make_data(root/'data','A')
            for task in ('sweep-starter','sweep','adapt'):
                graph=waffle.graph(root/'data/visible',root/'audit',task,meta['target'])
                kinds=[n['operatorType'] for n in graph['operators']]
                self.assertIn('CSVFileScan',kinds)
                self.assertEqual(kinds[-1],'Sort')
                body=next(n for n in graph['operators'] if n['customDisplayName']=='K-means and score - prepared')
                self.assertNotIn('DictReader',body['operatorProperties']['code'])
            for task in ('files-starter','files'):
                graph=waffle.graph(root/'data/visible',root/'audit',task,meta['target'])
                aggregate=next(n for n in graph['operators'] if n['operatorType']=='Aggregate')
                self.assertEqual(aggregate['operatorProperties']['aggregations'][0]['aggFunction'],'average')
                reader=next(n for n in graph['operators'] if n['operatorType']=='FileScan')
                if task=='files':
                    self.assertEqual(reader['operatorProperties']['fileName'],'$file')
                    self.assertTrue(any(e['target']['operatorID']==reader['operatorID'] and e['target']['portID']=='control-variables' for e in graph['links']))
                else:
                    self.assertNotEqual(reader['operatorProperties']['fileName'],'$file')

    def test_both_packs_and_stopping(self):
        with tempfile.TemporaryDirectory() as tmp:
            for pack in ['A','B']:
                root=Path(tmp)/pack; meta=make_data(root,pack)
                values=scores(root/'visible/points.csv')
                self.assertEqual([r['K'] for r in values],[2,3,4])
                self.assertLess(values[0]['score'],meta['target'])
                self.assertGreater(values[1]['score'],meta['target'])
                self.assertEqual(len(expected(root/'visible','adapt',meta['target'])),2)
                self.assertEqual(len(expected(root/'first','adapt',meta['target'])),1)
                self.assertEqual(len(expected(root/'cap','adapt',meta['target'])),3)
                self.assertEqual(len(expected(root/'extra','files',meta['target'])),4)
                self.assertEqual(len(expected(root/'visible','files-starter',meta['target'])),1)

    def test_checks_exact_visits_and_outputs(self):
        want=[{'K':2,'score':-10.0},{'K':3,'score':-2.0}]
        self.assertTrue(check_evidence(want,want,want,0))
        self.assertFalse(check_evidence(want,want+[{'K':4,'score':-1.0}],want,0))
        self.assertFalse(check_evidence(want,want,want,5))
        self.assertFalse(check_evidence(want,want,None,0))
        self.assertFalse(check_evidence(want,list(reversed(want)),want,0))
        self.assertFalse(compare(want,want+want))
        self.assertFalse(compare(want,[{'K':2,'score':float('nan')},{'K':3,'score':-2}]))
        self.assertFalse(compare(want,[{'K':2,'score':-9},{'K':3,'score':-2}]))


if __name__=='__main__':unittest.main()
