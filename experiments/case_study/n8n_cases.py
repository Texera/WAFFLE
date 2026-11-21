"""Build and execute n8n translations of KNIME examples 09–16."""
import argparse
import csv
import hashlib
import json
import subprocess
from pathlib import Path

from check import compare, expected_rows

HERE = Path(__file__).resolve().parent
INPUT = HERE / "results"
IMAGE = "n8nio/n8n@sha256:fabce3e9678a07d2dde83bd8f5124017f3ec457d0a3fc6b63bb4cec465d63861"


def read_input(name, numeric_fields):
    with (INPUT / name).open(encoding="utf-8-sig", newline="") as stream:
        return [{key: None if value == "" else float(value) if key in numeric_fields else value
                 for key, value in row.items() if key != "row ID"}
                for row in csv.DictReader(stream)]


PREPARE = {
    9: """const batches = [];
for (let offset = 0; offset < rows.length; offset += 3)
  batches.push({rows: rows.slice(offset, offset + 3), i: batches.length});
return batches;""",
    10: "return Array.from({length: 5}, (_, i) => ({rows, i}));",
    11: """const groups = new Map();
for (const row of rows) {
  if (!groups.has(row.Class)) groups.set(row.Class, []);
  groups.get(row.Class).push(row);
}
return [...groups].map(([group, rows]) => ({group, rows}));""",
    12: "return rows.map(row => ({number: row.Number}));",
    13: "return [{source: rows, collected: [], i: 0}];",
    14: "return Array.from({length: 5}, (_, i) => ({rows, value: i * 0.25}));",
    15: "return Array.from({length: 5}, (_, i) => ({rows, i}));",
    16: "return Array.from({length: 5}, (_, i) => ({rows, i}));",
}

BODY = {
    9: """const counts = new Map();
for (const row of input.rows) counts.set(row.Text, (counts.get(row.Text) || 0) + 1);
return [{rows: [...counts].map(([value, count]) => ({value, count, Iteration: input.i}))}];""",
    10: "return [{rows: input.rows.map(r => ({...r, 'Counting Column': input.i, Iteration: input.i}))}];",
    11: """const rows = ['X', 'Y'].map(column => {
  const cells = input.rows.map(row => row[column]);
  const values = cells.filter(Number.isFinite);
  const n = values.length;
  const sum = values.reduce((a, b) => a + b, 0);
  const mean = sum / n;
  const moment = power => values.reduce((a, b) => a + (b - mean) ** power, 0);
  const variance = moment(2) / (n - 1);
  const sd = Math.sqrt(variance);
  const nan = {__float__: 'NaN'};
  return {Column: column, Min: Math.min(...values), Max: Math.max(...values), Mean: mean,
    'Std. deviation': sd, Variance: variance,
    Skewness: n < 3 ? nan : n * moment(3) / ((n-1)*(n-2)*sd**3),
    Kurtosis: n < 4 ? nan : n*(n+1)*moment(4)/((n-1)*(n-2)*(n-3)*sd**4)
      - 3*(n-1)**2/((n-2)*(n-3)),
    'Overall sum': sum, 'No. missings': cells.filter(v => v === null).length,
    'No. NaNs': cells.filter(Number.isNaN).length,
    'No. +∞s': cells.filter(v => v === Infinity).length,
    'No. -∞s': cells.filter(v => v === -Infinity).length,
    Median: null, 'Row count': cells.length, Class: input.group};
});
return [{rows}];""",
    12: "return [{rows: points.map(r => ({...r, 'Appended Number': input.number}))}];",
    13: """const result = input.source.map(r => ({...r, 'Counting Column': input.i, Iteration: input.i}));
return [{source: input.source, collected: input.collected.concat(result), i: input.i + 1}];""",
    14: """return [{rows: input.rows.map(r => {
  const x = r.X * input.value;
  return {...r, X: x, Y: -x * input.value};
})}];""",
    15: "return [{rows: input.rows.map(() => ({i: input.i, value: input.i}))}];",
    16: "return [{rows: [{currentIteration: input.i}]}];",
}


def workflow(n):
    rows = read_input(f"{n:02}-input.csv", {"X", "Y", "Number"})
    prepare = "const rows = " + json.dumps(rows) + ";\n" + PREPARE[n]
    body = "const input = $input.first().json;\n" + BODY[n]
    if n == 12:
        points = read_input("12-points.csv", {"X", "Y", "Class"})
        body = "const points = " + json.dumps(points) + ";\n" + body
    nodes, connections = [], {}

    def node(name, kind, version, x, y, parameters):
        nodes.append(dict(id=name, name=name, type="n8n-nodes-base." + kind,
                          typeVersion=version, position=[x, y], parameters=parameters))

    def connect(source, *outputs):
        connections[source] = {"main": [[dict(node=name, type="main", index=0)]
                                        for name in outputs]}

    def code(name, x, y, script):
        node(name, "code", 2, x, y, {"jsCode": script})

    node("Start", "manualTrigger", 1, 0, 0, {})
    code("Input", 220, 0, prepare)
    connect("Start", "Input")
    code("Body", 680, 120, body)
    if n == 13:
        node("Continue", "if", 1, 900, 120, {"conditions": {"number": [{
            "value1": "={{ $json.i }}", "operation": "smaller", "value2": 5}]}})
        connect("Input", "Body")
        connect("Body", "Continue")
        connect("Continue", "Body", "Result")
        collect = "return $input.first().json.collected;"
    else:
        node("Loop", "splitInBatches", 3, 450, 0, {"batchSize": 1, "options": {}})
        connect("Input", "Loop")
        connect("Loop", "Result", "Body")
        connect("Body", "Loop")
        collect = "const rows = $input.all().flatMap(item => item.json.rows);\n"
        collect += ("return [Object.fromEntries(rows.map(({i, value}) => "
                    "[i === 0 ? 'Counting Column' : 'Counting Column (Iter #' + i + ')', value]))];"
                    if n == 15 else "return rows;")
    code("Result", 1100, -100, collect)
    return dict(id=f"knimeCase{n:02}", name=f"KNIME loop example {n:02}", active=False,
                nodes=nodes, connections=connections, settings={"executionOrder": "v1"})


def execute(n, directory, version):
    graph = workflow(n)
    path = directory / f"{n:02}-n8n.json"
    path.write_bytes(json.dumps(graph, indent=2, ensure_ascii=False).encode("utf-8"))
    command = ["docker", "run", "--rm", "--network", "none",
               "-e", "N8N_DIAGNOSTICS_ENABLED=false",
               "-v", f"{path}:/cases/workflow.json:ro",
               "--entrypoint", "sh", IMAGE, "-ec",
               'n8n import:workflow --input=/cases/workflow.json >&2; exec n8n execute --id "$1" --rawOutput',
               "sh", graph["id"]]
    run = subprocess.run(command, capture_output=True, encoding="utf-8")
    if run.returncode:
        raise RuntimeError(run.stderr[-2000:] + run.stdout[-2000:])
    # Some versions print runner startup messages around the raw JSON object.
    start = run.stdout.index("{\n")
    record, _ = json.JSONDecoder().raw_decode(run.stdout[start:])
    data = record["data"]["resultData"]
    assert record.get("finished") and record.get("status") == "success", record.get("status")
    assert "error" not in data and data["lastNodeExecuted"] == "Result", data.get("error")
    trace = data["runData"]
    iterations = len(trace["Body"])
    expected_iterations = 4 if n == 9 else 13 if n == 11 else 5
    assert iterations == expected_iterations, (n, iterations)
    rows = [item["json"] for item in trace["Result"][0]["data"]["main"][0]]
    evidence = dict(case=n, version=version, image=IMAGE, iterations=iterations,
                    workflow_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), rows=rows)
    (directory / f"{n:02}-run.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    baseline = json.loads((INPUT / f"{n:02}-knime-run.json").read_text())
    assert baseline["exit_code"] == 0 and baseline["exports_present"]
    compare(expected_rows(INPUT, n), rows)
    return dict(case=n, iterations=iterations, rows=len(rows), status="match")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New directory for graphs and run evidence")
    parser.add_argument("--cases", nargs="+", type=int, default=list(PREPARE), choices=PREPARE)
    args = parser.parse_args()
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    version = subprocess.check_output(["docker", "run", "--rm", "--network", "none", IMAGE,
                                       "--version"], text=True).strip()
    results = []
    for n in args.cases:
        result = execute(n, directory, version)
        results.append(result)
        print(result, flush=True)
    (directory / "comparison.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
