import unittest
from graphlib import CycleError

from analyze import count_reconvergence
from loop_paths import classify


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

    def test_paths_between_one_boundary_pair(self):
        scope = {"roles": {"a": "LoopStart", "e": "LoopEnd"}, "connected": True,
                 "node_ids": list("abcde"), "edges": []}

        def check(links, expected):
            scope["edges"] = [(a, 0, b, 0) for a, b in links]
            self.assertEqual(classify(scope), expected)

        check(["ab", "ab", "be", "bc", "bd"], "one-path")
        check(["ab", "bc", "ce", "be"], "several-paths")
        check(["ab", "bc", "cb", "ce"], "cyclic-body")
        check(["ab", "ce"], "disconnected")
        scope["roles"]["d"] = "LoopStart"
        check(["ab", "be"], "multiple-boundaries")

    def test_invalid_graphs(self):
        with self.assertRaises(CycleError):
            count_reconvergence(plan("ab", ["ab", "ba"]))
        with self.assertRaisesRegex(ValueError, "endpoint"):
            count_reconvergence(plan("ab", ["ac"]))
        with self.assertRaisesRegex(ValueError, "duplicate operator"):
            count_reconvergence(plan("aa", []))
