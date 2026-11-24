import unittest
from graphlib import CycleError

from analyze import count_reconvergence


def plan(nodes, links):
    return {
        "operators": [{"operatorID": n} for n in nodes],
        "links": [{"source": {"operatorID": a}, "target": {"operatorID": b}}
                  for a, b in links],
    }


class RejoiningBranches(unittest.TestCase):
    def test_diamond_and_bypass(self):
        self.assertEqual(count_reconvergence(plan("abcd", ["ab", "ac", "bd", "cd"])), (4, 1))
        self.assertEqual(count_reconvergence(plan("abc", ["ab", "ac", "bc"])), (3, 1))

    def test_independent_inputs_parallel_links_and_empty_graph(self):
        self.assertEqual(count_reconvergence(plan("abc", ["ac", "bc"])), (3, 0))
        self.assertEqual(count_reconvergence(plan("ab", ["ab", "ab"])), (2, 0))
        self.assertEqual(count_reconvergence(plan("", [])), (0, 0))

    def test_invalid_graphs(self):
        with self.assertRaises(CycleError):
            count_reconvergence(plan("ab", ["ab", "ba"]))
        with self.assertRaisesRegex(ValueError, "endpoint"):
            count_reconvergence(plan("ab", ["ac"]))
        with self.assertRaisesRegex(ValueError, "duplicate operator"):
            count_reconvergence(plan("aa", []))
