"""Serialize accepted plans to native workflows without solving or repairing a task."""

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys
from protocol import FIELDS, HIDDEN, LIMIT, dump
from graphs import initial, expression, validate

EXP = Path(__file__).resolve().parents[1]
TEMPLATE = EXP / "case_study/recursive/results/sum-waffle.json"


def statements(pairs, names):
    return [f"{name} = {expression(expr, names)}" for name, expr in pairs]


def waffle(plan, data):
    graph = json.loads(TEMPLATE.read_text())
    source, start, body, end, _ = [
        op["operatorProperties"] for op in graph["operators"]
    ]
    source["columns"] = [dict(attributeName=k, attributeType="integer") for k in FIELDS]
    source["code"] = (
        "from pytexera import *\nclass Input(UDFSourceOperator):\n    def produce(self):\n        yield "
        + repr(initial(data))
        + "\n"
    )
    start["initialization"] = "\n".join(
        [f"{k} = int(D.iloc[0]['{k}'])" for k in FIELDS]
        + ["safety_round = 0"]
        + statements(plan[1][2], FIELDS)
    )
    start["output"] = "D"
    code = [
        "from pytexera import *",
        "class Emit(UDFOperatorV2):",
        "    def process_state(self, state, port):",
        "        return None",
        "    def process_tuple(self, row, port):",
    ] + [f"        {k} = self.state['{k}']" for k in FIELDS]
    for name, expr in zip(("out_x", "out_y"), plan[2][2:]):
        code.append(f"        self.{name} = int({expression(expr, FIELDS)})")
    code += [
        "        yield dict(x=self.out_x, y=self.out_y)",
        "    def produce_state_on_finish(self, port):",
        "        return State(dict(self.state, out_x=self.out_x, out_y=self.out_y))",
    ]
    body["code"] = "\n".join(code) + "\n"
    names = FIELDS + ["out_x", "out_y"]
    end["update"] = "\n".join(statements(plan[3][2], names) + ["safety_round += 1"])
    end["condition"] = f"safety_round < {LIMIT} and ({expression(plan[3][3], names)})"
    return graph


def knime(plan, data, folder):
    sys.path.insert(0, str(EXP / "loop_policies/native_controls"))
    from knime_native import Graph, BASE, entries, cfg

    graph = Graph(folder / "workflow")
    ids = []
    for node in plan:
        kind = node[0]
        if kind == "input":
            idx = graph.input([initial(data)])
        elif kind == "start":
            idx, _ = graph.node(
                "Recursive Loop Start",
                BASE + "meta.looper.recursive.RecursiveLoopStartNodeFactory",
            )
            graph.link(ids[node[1]], idx)
        elif kind == "set":
            idx = graph.formula(
                ids[node[1]], node[2], expression(node[3], FIELDS, True)
            )
        elif kind == "keep":
            idx, m = graph.node(
                "Filter " + node[2], BASE + "preproc.filter.row.RowFilterNodeFactory"
            )
            entries(
                cfg(m, "rowFilter"),
                dict(
                    RowFilter_TypeID="StringComp_RowFilter",
                    ColumnName=node[2],
                    include=True,
                    deepFiltering=False,
                    CaseSensitive=True,
                    hasWildCards=False,
                    isRegExpr=True,
                    Pattern="1([.]0+)?",
                ),
            )
            graph.link(ids[node[1]], idx)
        elif kind == "end":
            idx, m = graph.node(
                "Recursive Loop End",
                BASE + "meta.looper.recursive.RecursiveLoopEndNodeFactory",
            )
            entries(
                m,
                {
                    "Use Flow Variable": False,
                    "End Loop Variable Name": "",
                    "CFG_AddIterationColumn": False,
                    "CFG_End_Loop": "false",
                    "CFG_MaxNrIterations": LIMIT,
                    "CFG_MinNrOfRows": 1,
                    "CFG_OnlyLastData": False,
                    "CFG_PropagateVariables": False,
                },
            )
            graph.link(ids[node[1]], idx)
            graph.link(ids[node[2]], idx, inport=2)
        elif kind == "sink":
            graph.export(ids[node[1]], folder / "result.csv")
            idx = None
        ids.append(idx)
    graph.finish()


def prepare(trials, out, control=False):
    out.mkdir(parents=True, exist_ok=False)
    mapping = []
    manifest = []
    compiled = set()
    records = [
        json.loads(p.read_text(encoding="utf-8")) for p in sorted(trials.glob("*.json"))
    ]
    if len(records) != 24 and not control:
        raise ValueError(f"expected 24 full sessions, found {len(records)}")
    for rec in records:
        item = rec["attempts"][-1]
        if not item["public_pass"]:
            continue
        system = rec["system"]
        plan = validate(item["plan"], system)
        for index, data in enumerate(HIDDEN[rec["task"]]):
            key = (
                system
                + "-"
                + hashlib.sha256(json.dumps([plan, data]).encode()).hexdigest()[:16]
            )
            mapping.append(
                dict(
                    task=rec["task"],
                    seed=rec["seed"],
                    system=system,
                    fixture=index,
                    case=key,
                )
            )
            if key in compiled:
                continue
            compiled.add(key)
            if system == "waffle":
                dump(out / (key + ".json"), waffle(plan, data))
                manifest.append(
                    dict(
                        case=key,
                        strategy="authored",
                        pair=0,
                        warmup=False,
                        workflow=key + ".json",
                        fields=["x", "y"],
                    )
                )
            else:
                knime(plan, data, out / key)
    dump(out / "mapping.json", mapping)
    dump(out / "manifest.json", dict(runs=manifest))


def run_knime(out, runtime):
    sys.path.insert(0, str(EXP / "user_study"))
    from run_knime import launch

    keys = sorted(
        {
            r["case"]
            for r in json.loads((out / "mapping.json").read_text())
            if r["system"] == "knime"
        }
    )

    def run(key):
        folder = out / key
        code = launch(
            runtime,
            [
                "-application",
                "org.knime.product.KNIME_BATCH_APPLICATION",
                "-reset",
                "-nosave",
                "-failonloaderror",
                "-workflowDir=" + str(folder / "workflow"),
                "-data",
                str(folder / "workspace"),
            ],
            folder / "engine.log",
        )
        rows = None
        if code == 0 and (folder / "result.csv").exists():
            with (folder / "result.csv").open(newline="") as f:
                rows = [[float(r["x"]), float(r["y"])] for r in csv.DictReader(f)]
        dump(folder / "result.json", dict(case=key, exit=code, rows=rows))
        print(key, code, rows, flush=True)

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run, keys))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["prepare", "knime"])
    parser.add_argument("out", type=Path)
    parser.add_argument("--trials", type=Path)
    parser.add_argument("--runtime", type=Path)
    a = parser.parse_args()
    if a.command == "prepare":
        prepare(a.trials, a.out.resolve())
    else:
        run_knime(a.out.resolve(), a.runtime)
