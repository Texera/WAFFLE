"""Generate repeated two-iteration workflows for native Filter binding."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

from prepare import graph

WORKERS = (1, 2, 4, 8)
WIDE_WORKERS = (16, 32)
ROWS = 4096
REPEATS = 3


def workflow():
    base = graph(Path("unused"), 2, "loop")
    source, start, body, end, collector = base["operators"]
    source["operatorProperties"]["code"] = """from pytexera import *
import pandas as pd
class Values(UDFSourceOperator):
    def produce(self):
        yield pd.DataFrame({'x': range(4096)})
"""
    source["operatorProperties"]["columns"] = [{"attributeName": "x", "attributeType": "integer"}]
    predicate = deepcopy(body)
    predicate["operatorID"] = "binding-filter"
    predicate["operatorType"] = "Filter"
    predicate["customDisplayName"] = "Filter x >= $K"
    predicate["operatorProperties"] = {
        "predicates": [{"attribute": "x", "condition": ">=", "value": "$K"}]
    }
    body["customDisplayName"] = "Record iteration"
    body["operatorProperties"]["code"] = """from pytexera import *
class Record(UDFTableOperator):
    def process_table(self, table, port):
        yield table.assign(K=self.state['K'])[['K', 'x']]
"""
    fields = [{"attributeName": name, "attributeType": "integer"} for name in ("K", "x")]
    body["operatorProperties"]["outputColumns"] = fields
    collector["operatorProperties"]["outputColumns"] = fields
    base["operators"] = [source, start, predicate, body, end, collector]
    edge = base["links"][1]
    edge["target"]["operatorID"] = predicate["operatorID"]
    base["links"].append({
        "linkID": "filter-to-recorder",
        "source": {"operatorID": predicate["operatorID"], "portID": "output-0"},
        "target": {"operatorID": body["operatorID"], "portID": "input-0"},
    })
    base["operatorPositions"] = {
        op["operatorID"]: {"x": 160 * i, "y": 100}
        for i, op in enumerate(base["operators"])
    }
    return base


def prepare(destination, widths=WORKERS):
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "workflow.json").write_text(json.dumps(workflow(), indent=2) + "\n")
    manifest = {
        "rows": ROWS,
        "runs": [{"workers": workers, "repeat": repeat}
                 for repeat in range(REPEATS) for workers in widths]
    }
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--wide", action="store_true", help="Use 16 and 32 filter workers")
    args = parser.parse_args()
    prepare(args.destination, WIDE_WORKERS if args.wide else WORKERS)
