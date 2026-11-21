"""Translate the eight bounded KNIME examples to self-contained RapidMiner processes."""
import argparse
import csv
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent / "results"

# A single payload attribute preserves the distinction between missing and undefined
# statistics, matching the Texera case-study representation. Each example is one row.
TABLE = """
import com.rapidminer.example.table.AttributeFactory
import com.rapidminer.example.table.DoubleArrayDataRow
import com.rapidminer.example.table.MemoryExampleTable
import com.rapidminer.tools.Ontology
import groovy.json.JsonOutput
import groovy.json.JsonSlurper
def table(rows) {
    def col = AttributeFactory.createAttribute("payload", Ontology.STRING)
    def t = new MemoryExampleTable([col])
    for (row in rows) {
        double value = col.mapping.mapString(JsonOutput.toJson(row))
        t.addDataRow(new DoubleArrayDataRow([value] as double[]))
    }
    return t.createExampleSet()
}
def unpack(set) {
    def col = set.attributes.get("payload")
    return set.collect { new JsonSlurper().parseText(it.getValueAsString(col)) }
}
"""

PREPARE = {
    9: "rows.collate(3).collect { [rows: it] }",
    10: "(0..<5).collect { [rows: rows] }",
    11: "rows.groupBy { it.Class }.collect { key, group -> [group: key, rows: group] }",
    12: "rows.collect { [number: it.Number] }",
    13: "[[rows: rows]]",
    14: "(0..4).collect { [rows: rows, value: it * 0.25d] }",
    15: "(0..<5).collect { [rows: rows] }",
    16: "(0..<5).collect { [rows: rows] }",
}
COUNTING = "batch.rows.collect { it + ['Counting Column': i, Iteration: i] }"
BODY = {
    9: "batch.rows.countBy { it.Text }.collect { key, count -> [value: key, count: count, Iteration: i] }",
    10: COUNTING,
    11: "['X','Y'].collect { name -> stats(batch.rows, name, batch.group) }",
    12: "points.collect { it + ['Appended Number': batch.number] }",
    13: COUNTING,
    14: """batch.rows.collect { row ->
    double x = row.X * batch.value
    row + [X: x, Y: -x * batch.value]
}""",
    15: "batch.rows.collect { [iteration: i, value: i] }",
    16: "[[currentIteration: i]]",
}

# Same sample variance and bias-corrected skewness and excess kurtosis as the
# KNIME Statistics node on these finite inputs. Median is disabled in this case.
STATS = """
def stats(rows, name, group) {
    def cells = rows.collect { it[name] }
    def values = cells.findAll { it != null && Double.isFinite(it.doubleValue()) }
    int n = values.size()
    double sum = values.sum(), mean = sum / n
    def moment = { power -> values.sum { Math.pow(it.doubleValue() - mean, power) } }
    double variance = moment(2) / (n-1), sd = Math.sqrt(variance)
    def nan = [__float__: 'NaN']
    return [Column: name, Min: values.min(), Max: values.max(), Mean: mean,
      'Std. deviation': sd, Variance: variance,
      Skewness: n < 3 ? nan : n * moment(3) / ((n-1)*(n-2)*Math.pow(sd,3)),
      Kurtosis: n < 4 ? nan : n*(n+1)*moment(4)/((n-1)*(n-2)*(n-3)*Math.pow(sd,4))
        - 3d*(n-1)*(n-1)/((n-2)*(n-3)),
      'Overall sum': sum, 'No. missings': cells.count { it == null },
      'No. NaNs': cells.count { it != null && Double.isNaN(it.doubleValue()) },
      'No. +∞s': cells.count { it == Double.POSITIVE_INFINITY },
      'No. -∞s': cells.count { it == Double.NEGATIVE_INFINITY },
      Median: null, 'Row count': cells.size(), Class: group]
}
"""


def read_rows(name, numeric):
    with (INPUT / name).open(encoding="utf-8-sig", newline="") as stream:
        return [{key: float(value) if key in numeric else value
                 for key, value in row.items() if key != "row ID"}
                for row in csv.DictReader(stream)]


def operator(parent, kind, name, x, y):
    return ET.SubElement(parent, "operator", {"class": kind, "compatibility": "10.1.000",
                         "name": name, "activated": "true", "expanded": "true",
                         "x": str(x), "y": str(y)})


def param(op, name, value):
    ET.SubElement(op, "parameter", key=name, value=str(value))


def script(parent, name, x, y, code):
    op = operator(parent, "execute_script", name, x, y)
    param(op, "script", TABLE + code)
    param(op, "standard_imports", "false")


def connect(parent, source, output, target, port):
    attributes = {"from_port": output, "to_port": port}
    if source:
        attributes["from_op"] = source
    if target:
        attributes["to_op"] = target
    ET.SubElement(parent, "connect", attributes)


def build(n, path):
    root = ET.Element("process", version="10.1.000")
    process = ET.SubElement(operator(root, "process", "Process", 0, 0), "process")
    data = read_rows(f"{n:02}-input.csv", {"Number", "X", "Y"})
    prepare = "def rows = new JsonSlurper().parseText('''" + json.dumps(data) + "''')\n"
    prepare += "def batches = " + PREPARE[n] + "\n"
    prepare += "operator.process.macroHandler.addMacro('batches', batches.size().toString())\nreturn table(batches)"
    script(process, "Prepare", 45, 35, prepare)
    loop = operator(process, "loop_until" if n == 13 else "loop", "Repeat", 245, 35)
    for key, val in {"set_iteration_macro": "true", "macro_name": "i", "macro_start_value": 0}.items():
        param(loop, key, val)
    if n == 13:
        for key, val in {"condition_on_data": "true", "condition_on_performance": "false",
                         "condition_before": "false", "min_examples": 1, "max_examples": 1,
                         "min_attributes": 1, "max_attributes": 1, "max_iterations": 100}.items():
            param(loop, key, val)
    else:
        param(loop, "iterations", "%{batches}")
    inside = ET.SubElement(loop, "process")
    body = "int i = Integer.parseInt(operator.process.macroHandler.getMacro('i'))\n"
    body += "def batch = unpack(input[0])[" + ("0" if n == 13 else "i") + "]\n"
    if n == 11:
        body += STATS
    if n == 12:
        points = read_rows("12-points.csv", {"X", "Y", "Class"})
        body += "def points = new JsonSlurper().parseText('''" + json.dumps(points) + "''')\n"
    body += "def result = table(" + BODY[n] + ")\n"
    body += "return [result, table(i >= 4 ? [[stop: true]] : [])]" if n == 13 else "return result"
    script(inside, "Body", 180, 60, body)
    connect(inside, None, "input 1", "Body", "input 1")
    connect(inside, "Body", "output 1", None, "output 1")
    if n == 13:
        connect(inside, "Body", "output 2", None, "example set")
    collect = "def rows = input[0].getObjects().collectMany { unpack(it) }\n"
    if n == 15:
        collect += """def wide = rows.collectEntries { row ->
    [(row.iteration == 0 ? 'Counting Column' : 'Counting Column (Iter #' + row.iteration + ')'): row.value]
}
return table([wide])"""
    else:
        collect += "return table(rows)"
    script(process, "Collect", 445, 35, collect)
    connect(process, "Prepare", "output 1", "Repeat", "input 1")
    connect(process, "Repeat", "output 1", "Collect", "input 1")
    connect(process, "Collect", "output 1", None, "result 1")
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    out = parser.parse_args().output
    out.mkdir(parents=True, exist_ok=True)
    for case in PREPARE:
        build(case, out / f"{case:02}.rmp")
