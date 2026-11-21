"""Verify all native graphs and ordered results before exporting Table 2 evidence."""

import argparse
import csv
from itertools import product
import json
from xml.etree import ElementTree as E
from inputs import HERE, RUN, POLICIES, SCALES, VISITS, model

ENGINES = ("waffle", "knime", "n8n", "rapidminer")
ALLOWED = {
    "waffle": {"CSVFileScan", "LoopStart", "LoopEnd"},
    "n8n": {"manualTrigger", "set", "splitOut", "splitInBatches", "noOp", "if"},
    "rapidminer": {
        "process",
        "set_macros",
        "loop",
        "loop_until",
        "generate_data_user_specification",
        "extract_macro",
        "generate_macro",
        "filter_examples",
    },
    "knime": {
        "TableCreator2NodeFactory",
        "LoopStartVariable3NodeFactory",
        "VariableToTableNodeFactory",
        "LoopEndDynamicNodeFactory",
        "LoopEndConditionDynamicNodeFactory",
        "RecursiveLoopStartNodeFactory",
        "JEPNodeFactory",
        "RowFilterNodeFactory",
        "RecursiveLoopEndNodeFactory",
        "CSVWriterNodeFactory",
    },
}


def node_types(engine, folder):
    if engine == "waffle":
        return [
            op["operatorType"]
            for op in json.loads((folder / "workflow.json").read_text())["operators"]
        ]
    if engine == "n8n":
        return [
            op["type"].split(".")[-1]
            for op in json.loads((folder / "workflow.json").read_text())["nodes"]
        ]
    if engine == "rapidminer":
        return [
            op.attrib["class"]
            for op in E.parse(folder / "workflow.rmp").iter("operator")
        ]
    workflow = folder / "workflow"
    nodes = E.parse(workflow / "workflow.knime").find(".//{*}config[@key='nodes']")
    paths = [
        node.find("{*}entry[@key='node_settings_file']").attrib["value"]
        for node in nodes
    ]
    return [
        E.parse(workflow / path)
        .find("{*}entry[@key='factory']")
        .attrib["value"]
        .split(".")[-1]
        for path in paths
    ]


def actual(engine, folder):
    if engine == "waffle":
        assert (folder / "exit-code.txt").read_text().strip() == "0"
        assert (
            "PASS native materialized results"
            in (folder / "engine-result.txt").read_text()
        )
        with (folder / "results.csv").open(newline="") as f:
            return [dict(K=int(k), score=float(score)) for k, score in csv.reader(f)]
    if engine == "knime":
        assert "executed sucessfully" in (folder / "engine.log").read_text(
            encoding="utf-8"
        )
        with (folder / "result.csv").open(newline="") as f:
            return [
                dict(K=float(row["K"]), score=float(row["score"]))
                for row in csv.DictReader(f)
            ]
    if engine == "rapidminer":
        result = json.loads((folder / "output.json").read_text())
        assert result["iterations"] == len(result["rows"])
        return result["rows"]
    raw = (folder / "engine.log").read_text(encoding="utf-8")
    result, _ = json.JSONDecoder().raw_decode(raw[raw.index("{\n") :])
    assert (
        result["status"] == "success"
        and result["data"]["resultData"]["lastNodeExecuted"] == "Result"
    )
    trace = result["data"]["resultData"]["runData"]
    visited = [
        {k: call["data"]["main"][0][0]["json"][k] for k in ("K", "score")}
        for call in trace["Body"]
    ]
    items = trace["Result"][0]["data"]["main"][0]
    rows = [x["json"] for x in items] if "Loop" in trace else items[0]["json"]["rows"]
    assert model.compare(visited, rows)
    return rows


def extract():
    records = []
    for engine, rule, fixture in product(ENGINES, POLICIES, SCALES):
        folder = RUN / engine / f"{rule}-{fixture}"
        records.append(
            dict(
                engine=engine,
                rule=rule,
                fixture=fixture,
                operator_types=json.dumps(node_types(engine, folder)),
                output=json.dumps(actual(engine, folder)),
            )
        )
    return records


def check(records):
    expected_cases = set(product(ENGINES, POLICIES, SCALES))
    seen = set()
    scores = {
        f: {
            r["K"]: r
            for r in model.scores(HERE.parent / "results/inputs" / f / "points.csv")
        }
        for f in SCALES
    }
    for record in records:
        engine, rule, fixture = key = tuple(
            record[name] for name in ("engine", "rule", "fixture")
        )
        assert key not in seen and key in expected_cases, key
        seen.add(key)
        nodes = json.loads(record["operator_types"])
        assert nodes and set(nodes) <= ALLOWED[engine], (key, nodes)
        visits = VISITS[rule][list(SCALES).index(fixture)]
        assert model.compare(
            [scores[fixture][k] for k in visits], json.loads(record["output"])
        ), key
    assert seen == expected_cases, expected_cases - seen


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Read the native run directory and replace the saved CSV after validation",
    )
    args = parser.parse_args()
    path = HERE / "observations.csv"
    if args.extract:
        records = extract()
        check(records)
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)
    with path.open(newline="", encoding="utf-8") as f:
        check(list(csv.DictReader(f)))
    print(
        "Verified 64 rule/fixture/system combinations, including their native operator types and ordered (K, score) outputs."
    )
