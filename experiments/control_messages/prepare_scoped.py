"""Generate paired two-branch merge workflows and their expected results."""
import argparse
import json
from pathlib import Path
from prepare import diamond, BRANCH
from scoped_orders import CASES

FIELDS = ["K", "ratio", "calls", "first", "rows_seen"]
MERGE = """from pytexera import *
import pandas as pd
class Merge(UDFTableOperator):
    def open(self):
        self.bindings_seen = []

    def process_state(self, state, port):
        self.bindings_seen.extend(name for name in state if name in ("K", "ratio"))
        return state

    def process_table(self, table, port):
        yield pd.DataFrame([dict(K=self.state["K"], ratio=self.state.get("ratio", 0.0),
                                 calls=len(self.bindings_seen), first=int(self.bindings_seen[0] == "K"),
                                 rows_seen=len(table))])
"""


def prepare(destination):
    destination.mkdir(parents=True, exist_ok=False)
    runs = []
    for case, branches in CASES.items():
        for direction, pair in (("LR", branches), ("RL", list(reversed(branches)))):
            wf = diamond(2, False)
            _, start, left, right, merge, _, result = wf["operators"]
            start["operatorProperties"]["initialization"] = "seed = 1"
            for branch, (_, values) in zip((left, right), pair):
                branch["operatorProperties"]["code"] = BRANCH + (
                    "    def produce_state_on_finish(self, port):\n"
                    f"        return State({values!r})\n"
                )
            merge["operatorProperties"]["code"] = MERGE
            for op in [merge, result]:
                op["operatorProperties"]["outputColumns"] = [
                    dict(attributeName=f, attributeType="double" if f == "ratio" else "integer")
                    for f in FIELDS
                ]
            name = f"{case}-{direction}"
            workflow = name + ".json"
            (destination / workflow).write_text(json.dumps(wf, indent=2) + "\n", encoding="utf-8")
            runs.append(dict(case=case, layout=direction, workflow=workflow, fields=FIELDS))
    repeated = json.loads((destination / "equal-LR.json").read_text(encoding="utf-8"))
    _, start, left, right, _, end, _ = repeated["operators"]
    start["operatorProperties"]["initialization"] = "turn = 0"
    end["operatorProperties"].update(update="turn += 1", condition="turn < 2")
    for branch in (left, right):
        branch["operatorProperties"]["code"] = BRANCH + (
            "    def produce_state_on_finish(self, port):\n"
            "        return State({'K': self.state['turn'] + 2})\n"
        )
    workflow = "new-iteration.json"
    (destination / workflow).write_text(json.dumps(repeated, indent=2) + "\n", encoding="utf-8")
    runs.append(dict(case="new-iteration", layout="LR", workflow=workflow, fields=FIELDS))
    (destination / "manifest.json").write_text(json.dumps({"runs": runs}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("destination", type=Path)
    prepare(p.parse_args().destination)
