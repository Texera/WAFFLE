"""Build one-iteration diamonds for the Section 5 merge experiment."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "loop_execution"))
from experiment import graph


SOURCE = """from pytexera import *
import pandas as pd
class Point(UDFSourceOperator):
    def produce(self):
        yield pd.DataFrame([{'x': 1.0, 'y': 2.0}])
"""
BRANCH = """from pytexera import *
class Branch(UDFOperatorV2):
    def process_tuple(self, row, port):
        yield row
"""
PUBLISH = """    def produce_state_on_finish(self, port):
        return State({'K': 3})
"""
MERGE = """from pytexera import *
import pandas as pd
class Merge(UDFTableOperator):
    callbacks = 0
    def process_state(self, state, port):
        self.callbacks += 1
        return state
    def process_table(self, table, port):
        yield pd.DataFrame([{'K': self.state['K'], 'callbacks': self.callbacks,
                             'rows_seen': len(table)}])
"""
FIELDS = ["K", "callbacks", "rows_seen"]
WIDTHS = [1, 2, 4, 8]


def diamond(width, publish):
    base = graph(Path("unused"), 1, "loop")
    source, start, model, end, result = base["operators"]
    source["operatorProperties"]["code"] = SOURCE
    end["operatorProperties"]["condition"] = "False"
    merge = deepcopy(model)
    merge["operatorID"] = "merge"
    merge["customDisplayName"] = "Merge"
    # Use the multi-input port declaration from the existing collector.
    merge["inputPorts"] = deepcopy(result["inputPorts"])
    merge["operatorProperties"]["code"] = MERGE
    fields = [dict(attributeName=k, attributeType="integer") for k in FIELDS]
    merge["operatorProperties"]["outputColumns"] = fields
    result["operatorProperties"]["outputColumns"] = fields
    result["inputPorts"] = deepcopy(model["inputPorts"])
    branches = []
    for i in range(width):
        op = deepcopy(model)
        op["operatorID"] = f"branch-{i}"
        op["customDisplayName"] = f"Branch {i + 1}"
        op["operatorProperties"]["code"] = BRANCH + (PUBLISH if publish and i == 0 else "")
        op["operatorProperties"]["outputColumns"] = deepcopy(source["operatorProperties"]["columns"])
        branches.append(op)
    base["operators"] = [source, start, *branches, merge, end, result]
    base["links"] = []
    def link(a, b):
        base["links"].append(dict(linkID=f"link-{len(base['links'])}",
                                  source=dict(operatorID=a["operatorID"], portID="output-0"),
                                  target=dict(operatorID=b["operatorID"], portID="input-0")))
    link(source, start)
    for op in branches:
        link(start, op)
        link(op, merge)
    link(merge, end)
    link(end, result)
    base["operatorPositions"] = {op["operatorID"]:dict(x=150*i, y=100) for i,op in enumerate(base["operators"])}
    return base


def prepare(dest):
    dest.mkdir(parents=True, exist_ok=True)
    runs = []
    for width in WIDTHS:
        for publish in [False, True]:
            condition = "update" if publish else "copies"
            name = f"width-{width}-{condition}"
            f = dest / (name + ".json")
            f.write_text(json.dumps(diamond(width, publish), indent=2) + "\n")
            runs.append(dict(case=name, strategy=condition, pair=0, warmup=False,
                             fields=FIELDS, workflow=f.name, expected=[dict(
                                 K=3 if publish else 2, callbacks=2 if publish else 1, rows_seen=width)]))
    (dest / "manifest.json").write_text(json.dumps({"runs": runs}, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    prepare(parser.parse_args().destination)
