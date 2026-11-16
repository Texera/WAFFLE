import tempfile
from pathlib import Path
import unittest
from model import make_data, scores, expected, compare, check_evidence
import waffle
import knime
import study
import xml.etree.ElementTree as E
import zipfile


class StudyTests(unittest.TestCase):
    def test_short_study_has_working_loop_scaffolds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); meta=make_data(root/'data','A')
            graph=waffle.graph(root/'data/visible',root/'audit','sweep-starter',meta['target'],short=True)
            kinds=[n['operatorType'] for n in graph['operators']]
            self.assertEqual(kinds,['CSVFileScan','LoopStart','PythonUDFV2','LoopEnd','Sort'])
            self.assertEqual(len(graph['links']),4)
            end=next(n for n in graph['operators'] if n['operatorType']=='LoopEnd')
            self.assertEqual(end['operatorProperties']['condition'],'False')
            for task in ('sweep-starter','sweep','adapt'):
                dest=root/task
                knime.workflow(dest,root/'data/visible',root/'audit',task,meta['target'],short=True)
                settings=[E.parse(p) for p in dest.glob('*/settings.xml')]
                entries={e.get('key'):e.get('value') for tree in settings for e in tree.iter() if e.tag.endswith('entry')}
                self.assertEqual(entries['loops'],'1' if task.endswith('starter') else '3')
                self.assertEqual(entries['variableName'],'score')
                self.assertEqual(entries['value'],str(meta['target']) if task=='adapt' else '0.0')

    def test_short_package_excludes_file_activity_and_solutions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'package'; study.prepare(root,short=True)
            import json
            manifest=json.loads((root/'manifest.json').read_text())
            self.assertEqual(manifest['protocol'],'35-minute')
            self.assertEqual(len(manifest['runs']),24)
            self.assertFalse(any(r['task'].startswith('files') for r in manifest['runs']))
            self.assertEqual(sorted(p.name for p in (root/'cards/A').iterdir()),['1-configure.txt','2-adapt.txt'])
            self.assertEqual(sorted(p.name for p in (root/'participants/A/knime').iterdir()),['START-HERE.txt','sweep-starter.knwf'])
            with zipfile.ZipFile(root/'participants/A/knime/sweep-starter.knwf') as archive:
                source='\n'.join(archive.read(n).decode() for n in archive.namelist() if n.endswith('.xml'))
                self.assertNotIn(root.as_posix(),source)
                self.assertIn('java.io.tmpdir',source)
                self.assertIn('java.util.Arrays.asList',source)
            for pack in ('A','B'):
                fallback=root/'facilitator/fallbacks'/pack
                with zipfile.ZipFile(fallback/'knime/sweep-fallback.knwf') as archive:
                    source='\n'.join(archive.read(n).decode() for n in archive.namelist() if n.endswith('.xml'))
                    self.assertNotIn(root.as_posix(),source)
                    self.assertIn('key="loops" type="xint" value="3"',source)
                graph=json.loads((fallback/'waffle/sweep-fallback.json').read_text())
                end=next(n for n in graph['operators'] if n['operatorType']=='LoopEnd')
                self.assertEqual(end['operatorProperties']['condition'],'K <= 4')

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
