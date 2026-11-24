import copy
import unittest
import json
from pathlib import Path

from corpus import cases, graph, FIXTURES
from oracle import expected, topology
from verify import check_native, verify_operators


class CorpusTests(unittest.TestCase):
    def test_all_graphs_are_distinct_without_names_or_values(self):
        signatures = set()
        for family, policy, arms in cases():
            g = graph(family, policy, arms, FIXTURES["mixed"])
            signature = topology(g)
            self.assertEqual(signature, arms)
            signatures.add(signature)
        self.assertEqual(len(signatures), sum(8**k for k in range(1, 5)))

    def test_rewired_graph_rejected(self):
        family, policy, arms = next(cases())
        g = graph(family, policy, arms, FIXTURES["mixed"])
        broken = copy.deepcopy(g)
        broken["links"].pop()
        with self.assertRaises(ValueError):
            topology(broken)

    def test_topology_ignores_labels_ids_and_serialization_order(self):
        family, policy, arms = list(cases())[59]
        g = graph(family, policy, arms, FIXTURES["mixed"])
        ids = {n["operatorID"]: f"v{300-i}" for i, n in enumerate(g["operators"])}
        g["operators"] = [dict(operatorID=ids[u]) for u in reversed(ids)]
        g["links"].reverse()
        for link in g["links"]:
            for end in ("source", "target"):
                link[end]["operatorID"] = ids[link[end]["operatorID"]]
        self.assertEqual(topology(g), arms)

    def test_single_fork_duplicate_rows_and_stop_boundary(self):
        # First motif has a bypass and a right arm subtracting one.
        # Values [0, 0, 0] expand to [0, -1] three times.
        data = (0, 0, 0)
        self.assertEqual(expected("aggregation", 0, ((0, 1),), data),
                         [(0, -1), (1, -1), (2, -1)])
        self.assertEqual(expected("stopping", 1, ((0, 1),), data), [(0, 6)])
        self.assertEqual(expected("search", 0, ((0, 1),), data),
                         [(-2, 9), (-1, 3), (0, 3), (1, 9), (2, 15)])

    def test_evidence_rejects_mutated_rows_and_counts(self):
        here = Path(__file__).parent
        operators = json.loads((here / "operators.json").read_text())
        hashes = verify_operators(operators)
        native = json.loads((here / "native.json").read_text())
        check_native(native, hashes)
        native["coordinator"][0]["rows"].pop()
        with self.assertRaisesRegex(ValueError, "native rows"):
            check_native(native, hashes)
        operators["families"]["stopping"]["visits"] += 1
        with self.assertRaisesRegex(ValueError, "operator evidence"):
            verify_operators(operators)
