import unittest
from defusedxml import ElementTree

from collect import has_cycle, n8n_graph
from knime_plans import reachable
from package_plans import reverse_path, verify_cycle, verify_subprocess
from rapidminer import graph


class LoopScreens(unittest.TestCase):
    def test_knime_direction_and_components(self):
        g = {
            "node_ids": ["1", "2", "3"],
            "roles": {"1": "LoopStart", "3": "LoopEnd"},
            "edges": [["1", "0", "2", "0"], ["3", "0", "2", "0"]],
        }
        for connected in (False, True):
            self.assertEqual(reachable(g, {"1"}, {"3"}), connected)
            self.assertEqual(reverse_path(g), connected)
            g["edges"][1] = ["2", "0", "3", "0"]

    def test_n8n_only_enabled_main_edges(self):
        def to(name):
            return [[{"node": name, "type": "main", "index": 0}]]

        w = {
            "nodes": [
                {"name": "a", "type": "example"},
                {"name": "b", "type": "example"},
            ],
            "connections": {"a": {"main": to("b")}, "b": {"aux": to("a")}},
        }

        def check(expected):
            g = n8n_graph(w)
            self.assertEqual(has_cycle(g), expected)
            self.assertEqual(verify_cycle(g), expected)

        check(False)
        w["connections"]["b"] = {"main": to("a")}
        check(True)
        w["nodes"][0]["disabled"] = True
        check(False)
        w["connections"]["a"] = {"main": to("missing")}
        self.assertEqual(n8n_graph(w)["unresolved_edges"], 1)

    def test_rapidminer_disabled_ancestry_and_missing_body(self):
        xml = '<process><operator name="p" class="process"><process><operator name="l" class="loop"><process/></operator></process></operator></process>'
        doc = ElementTree.fromstring(xml)
        self.assertTrue(verify_subprocess(graph(doc)))
        doc[0].set("activated", "false")
        self.assertFalse(verify_subprocess(graph(doc)))
        doc[0].set("activated", "true")
        loop = doc.find(".//operator[@class='loop']")
        loop.remove(loop.find("process"))
        self.assertFalse(verify_subprocess(graph(doc)))


if __name__ == "__main__":
    unittest.main()
