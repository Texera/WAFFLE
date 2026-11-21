"""Run the K-means policy workflows through the native KNIME batch application."""

import argparse
from prepare import ROOT, ART, specs, save, model
import knime
import run_knime
import copy
import csv
import json
import os
from pathlib import Path
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

NS = {"k": knime.NS}


def find(element, tag, key):
    return element.find(f"k:{tag}[@key='{key}']", NS)


def run(spec):
    rule = spec["task"]
    directory = ROOT / "knime" / spec["id"]
    directory.mkdir(parents=True, exist_ok=False)
    graph = directory / "workflow"
    data = ROOT / "data" / spec["fixture"]
    knime.workflow(graph, data, directory, "adapt", -100, short=True)
    path = graph / "workflow.knime"
    doc = ET.parse(path).getroot()
    nodes = find(doc, "config", "nodes")
    links = find(doc, "config", "connections")

    def settings(index):
        return graph / find(nodes[index - 1], "entry", "node_settings_file").get(
            "value"
        )

    def change(i, edit):
        path = settings(i)
        tree = ET.parse(path).getroot()
        m = find(tree, "config", "model")
        edit(m)
        knime.write(path, tree)

    def replace_script(m, code, **kwargs):
        for x in list(m):
            m.remove(x)
        knime.snippet(m, code, **kwargs)

    def init(m):
        code = "if(false)throw new java.io.IOException(); candidate=2;"
        outs = [("candidate", "candidate", "Integer")]
        if rule == "history":
            code += "previous=0.0;"
            outs.append(("previous", "previous", "Double"))
        replace_script(m, code, out_vars=outs)

    change(2, init)
    change(3, lambda m: find(m, "entry", "loops").set("value", "8"))

    def body(m):
        code = (
            (ART / "experiments/user_study/KMeansBody.java.txt")
            .read_text()
            .replace("POINTS_PATH", json.dumps((data / "points.csv").as_posix()))
            .replace("int k=iteration+2;", "int k=candidate;")
        )
        code += (
            "\nFiles.writeString(Paths.get("
            + json.dumps((directory / "visits.csv").as_posix())
            + '),out_k + "," + out_score + "\\n",StandardCharsets.UTF_8,StandardOpenOption.CREATE,StandardOpenOption.APPEND);'
        )
        replace_script(
            m,
            code,
            in_vars=[("candidate", "candidate", "Integer")],
            out_cols=[("K", "out_k", "Integer"), ("score", "out_score", "Double")],
            out_vars=[("score", "score", "Double")],
            replace=["K"],
        )

    change(4, body)

    def stop(m):
        for k, v in {
            "variableName": "done",
            "variableType": "INTEGER",
            "value": "1",
            "operator": "GE",
            "propagateLoopVariables": "true",
        }.items():
            find(m, "entry", k).set("value", v)

    change(5, stop)
    # Insert a controller between the body and native Variable Condition Loop End.
    templ = copy.deepcopy(nodes[3])
    templ.set("key", "node_7")
    find(templ, "entry", "id").set("value", "7")
    find(templ, "entry", "node_settings_file").set("value", "Update/settings.xml")
    nodes.append(templ)
    settings(7).parent.mkdir()
    raw = ET.parse(settings(4)).getroot()
    for k in ["name", "node-name"]:
        find(raw, "entry", k).set("value", "Update")
    inputs = [("candidate", "k", "Integer"), ("score", "score", "Double")]
    outputs = [("candidate", "next", "Integer"), ("done", "done", "Integer")]
    code = (
        "if(false)throw new java.io.IOException();\nnext="
        + ("score < -250 ? 2*k : k+1" if rule == "adaptive" else "k+1")
        + ";\n"
    )
    test = {
        "sweep": "next<=4",
        "target": "next<=4 && score < -100",
        "adaptive": "next<=4 && score < -100",
        "history": "next<=4 && (k==2 || score-previous>=150)",
    }[rule]
    code += "done=(" + test + ") ? 0 : 1;"
    if rule == "history":
        inputs.append(("previous", "previous", "Double"))
        outputs.append(("previous", "updated", "Double"))
        code += "\nupdated=score;"
    replace_script(
        find(raw, "config", "model"),
        code,
        in_vars=inputs,
        out_vars=outputs,
        replace=["candidate", "previous"],
    )
    knime.write(settings(7), raw)
    ref = next(c for c in links if find(c, "entry", "sourceID").get("value") == "4")
    find(ref, "entry", "destID").set("value", "7")
    c = copy.deepcopy(ref)
    c.set("key", "connection_7")
    find(c, "entry", "sourceID").set("value", "7")
    find(c, "entry", "destID").set("value", "5")
    links.append(c)
    knime.write(path, doc)
    rc = run_knime.launch(
        Path(os.environ["KNIME_HOME"]).resolve(),
        [
            "-application",
            "org.knime.product.KNIME_BATCH_APPLICATION",
            "-reset",
            "-nosave",
            "-failonloaderror",
            "-workflowDir=" + str(graph),
            "-data",
            str(directory / "workspace"),
        ],
        directory / "engine.log",
    )
    if rc:
        raise RuntimeError(f"{spec['id']}: KNIME exited {rc}")

    def read(name):
        with (directory / name).open() as f:
            return [dict(K=int(k), score=float(v)) for k, v in csv.reader(f)]

    visits = read("visits.csv")
    rows = read("results.csv")
    assert model.compare(spec["expected"], visits) and model.compare(
        spec["expected"], rows
    ), (spec["id"], visits, rows)
    save(directory / "observed.json", dict(rows=rows, iterations=len(visits)))
    print(spec["id"], [r["K"] for r in rows], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", help="Run one rule/fixture ID from the manifest")
    args = parser.parse_args()
    if "KNIME_HOME" not in os.environ:
        parser.error("Set KNIME_HOME to the KNIME installation directory")
    selected = [s for s in specs() if args.case is None or s["id"] == args.case]
    if not selected:
        parser.error("No matching case")
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(run, selected))
