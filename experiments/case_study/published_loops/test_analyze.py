import copy
import unittest

from analyze import analyze


def graph(names, links):
    return {"operators": [{"operatorID": str(i), "customDisplayName": name,
                           "operatorType": "Dummy", "operatorProperties": {}}
                          for i, name in enumerate(names)],
            "links": [{"source": {"operatorID": str(a), "portID": "out"},
                       "target": {"operatorID": str(b), "portID": "in"}} for a, b in links]}


class SourcePlans(unittest.TestCase):
    def test_side_edges_and_permutation(self):
        g = graph(["Counting Loop Start", "Filter", "Loop End", "Input", "Sink"],
                  [(0, 1), (1, 2), (3, 1), (1, 4)])
        status, record = analyze(g)
        self.assertEqual(status, "one connected pair")
        self.assertEqual(record[3:5], (1, 1))
        reordered = copy.deepcopy(g)
        reordered["operators"].reverse()
        reordered["links"].reverse()
        for node in reordered["operators"]:
            node["operatorID"] += "x"
        for edge in reordered["links"]:
            for endpoint in edge.values():
                endpoint["operatorID"] += "x"
        self.assertEqual(analyze(reordered), (status, record))
        reordered["links"][0]["source"]["portID"] = "other"
        self.assertNotEqual(analyze(reordered)[1][0], record[0])

    def test_unconnected_and_multiple_boundaries(self):
        g = graph(["Group Loop Start", "Loop End", "Other"], [(0, 2)])
        self.assertEqual(analyze(g), ("no connected pair", None))
        g = graph(["Group Loop Start", "Loop End", "Loop End"], [(0, 1), (1, 2)])
        status, (fingerprint, starts, ends, reachable) = analyze(g)
        self.assertEqual((status, starts, ends, reachable), ("multiple named boundaries", 1, 2, 2))
        # Two disjoint loops allow two start-to-end paths, not four.
        separate = graph(["Loop Start", "Loop End"] * 2, [(0, 1), (2, 3)])
        self.assertEqual(analyze(separate)[1][1:], (2, 2, 2))
        # In series the first start can also reach the second end.
        separate["links"].extend(graph(["x"] * 4, [(1, 2)])["links"])
        self.assertEqual(analyze(separate)[1][1:], (2, 2, 3))
        self.assertNotEqual(analyze(separate)[1][0], fingerprint)

    def test_bypass_outside_region(self):
        g = graph(["Input", "Loop Start", "Loop End", "Sink"], [(0, 1), (1, 2), (2, 3), (0, 3)])
        self.assertEqual(analyze(g)[1][3:5], (0, 0))
