import json
import tempfile
import unittest
from pathlib import Path

import experiment


class ComparisonTests(unittest.TestCase):
    def test_rejects_missing_extra_and_wrong_values(self):
        expected = [{'K': 2, 'score': -1.25}, {'K': 3, 'score': -0.5}]
        experiment.check_rows(expected, list(reversed(expected)))
        for actual in [expected[:1], expected + expected[:1],
                       [{'K': 2, 'score': 0.0}, expected[1]]]:
            with self.assertRaises(AssertionError):
                experiment.check_rows(expected, actual)

    def test_graphs_have_same_body_and_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'points.csv'
            experiment.write_points(p, 30)
            loop = experiment.graph(p, 4, 'loop')
            copies = experiment.graph(p, 4, 'copies')
            self.assertEqual(len(loop['operators']), 5)
            self.assertEqual(len(copies['operators']), 6)
            self.assertEqual(loop['operators'][0]['operatorProperties'],
                             copies['operators'][0]['operatorProperties'])
            body = loop['operators'][2]['operatorProperties']['code']
            for node in copies['operators'][1:-1]:
                code = node['operatorProperties']['code']
                self.assertEqual(body.split('    def process_state')[1],
                                 code.split('    def process_state')[1])
            self.assertEqual(loop['settings']['executionMode'], 'MATERIALIZED')

    def test_inputs_deterministic_and_invalid_counts_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/'a.csv', Path(tmp)/'b.csv'
            experiment.write_points(a, 30)
            experiment.write_points(b, 30)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            for n in [0, -1]:
                with self.assertRaises(ValueError): experiment.graph(a, n, 'loop')


if __name__ == '__main__': unittest.main()
