"""Construct three executable hierarchy workflows from the original input rows."""

import argparse
import csv
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "loop_execution"))
sys.path.insert(0, str(HERE.parent / "rapidminer"))
from experiment import graph
from build import connect, operator, param, script


def waffle(edges):
    workflow = graph(Path("unused"), 100, "loop")
    source, start, body, end, sink = workflow["operators"]
    columns = [
        {"attributeName": name, "attributeType": "string"}
        for name in ("parent", "child")
    ]
    payload = [{"attributeName": "payload", "attributeType": "string"}]
    source["operatorProperties"].update(
        columns=columns,
        code=f"""from pytexera import *
class Edges(UDFSourceOperator):
    def produce(self):
        for parent, child in {edges!r}:
            yield dict(parent=parent, child=child)
""",
    )
    start["operatorProperties"] = dict(
        initialization="level = 1\nrelation = D.drop_duplicates().to_json(orient='values')\nfrontier = D.loc[~D.parent.isin(D.child)].drop_duplicates().to_json(orient='values')",
        output="__import__('pandas').DataFrame(__import__('json').loads(frontier), columns=['parent','child'])",
    )
    body["operatorProperties"].update(
        outputColumns=payload,
        code="""from pytexera import *
import json
class Expand(UDFOperatorV2):
    def open(self):
        self.incoming = []
        self.trace = None

    def process_state(self, state, port):
        return None

    def process_tuple(self, row, port):
        self.incoming.append((row['parent'], row['child']))
        yield None

    def advance(self):
        if self.trace is None:
            current = list(dict.fromkeys(self.incoming))
            relation = json.loads(self.state['relation'])
            expanded = [(root, child) for root, tip in current for parent, child in relation if tip == parent]
            tips = {tip for _, tip in current}
            remaining = [edge for edge in relation if edge[0] not in tips]
            self.trace = dict(level=int(self.state['level']), incoming=self.incoming, relation=relation,
                              expanded=expanded, following=expanded + remaining, emitted=current)
        return self.trace

    def produce_state_on_finish(self, port):
        step = self.advance()
        return State(dict(self.state, next_frontier=json.dumps(step['expanded']), next_relation=json.dumps(step['following'])))

    def on_finish(self, port):
        yield dict(payload=json.dumps(self.advance()))
""",
    )
    end["operatorProperties"] = dict(
        update="frontier = next_frontier\nrelation = next_relation\nlevel += 1",
        condition="bool(__import__('json').loads(frontier)) and level <= 100",
    )
    sink["operatorProperties"].update(
        outputColumns=payload,
        code="""from pytexera import *
import json
import pandas as pd
class Collect(UDFTableOperator):
    def process_table(self, table, port):
        steps = [json.loads(value) for value in table['payload']]
        rows = [(p,c,s['level']) for s in steps for p,c in s['emitted']]
        rows.sort(key=lambda row: (row[0], row[2], row[1]))
        records = [{'row': row} for row in rows] + [{'trace': s} for s in steps]
        yield pd.DataFrame([{'payload':json.dumps(rec)} for rec in records])
""",
    )
    return workflow


def n8n(edges):
    workflow = json.loads((HERE.parent / "n8n_results/13-n8n.json").read_bytes())
    workflow.update(id="recursiveHierarchy", name="Parent-child hierarchy")
    props = {node["name"]: node["parameters"] for node in workflow["nodes"]}
    props["Input"]["jsCode"] = (
        "const edges = "
        + json.dumps(edges)
        + """;
const relation = Array.from(new Map(edges.map(e=>[JSON.stringify(e),e])).values());
const children = new Set(relation.map(e=>e[1]));
return [{frontier:relation.filter(e=>!children.has(e[0])),relation,level:1,history:[]}];"""
    )
    props["Body"][
        "jsCode"
    ] = """const {frontier,relation,level,history} = $input.first().json;
const emitted = Array.from(new Map(frontier.map(e=>[JSON.stringify(e),e])).values());
const expanded = emitted.flatMap(([root,tip])=>relation.filter(e=>e[0]===tip).map(e=>[root,e[1]]));
const tips = new Set(emitted.map(e=>e[1]));
const following = expanded.concat(relation.filter(e=>!tips.has(e[0])));
const trace = {level,incoming:frontier,relation,expanded,following,emitted};
return [{frontier:expanded,relation:following,level:level+1,history:history.concat(trace),again:Number(expanded.length>0 && level<100)}];"""
    cond = props["Continue"]["conditions"]["number"][0]
    cond.update(value1="={{ $json.again }}", operation="equal", value2=1)
    props["Result"]["jsCode"] = """const {history} = $input.first().json;
const rows = history.flatMap(s=>s.emitted.map(([p,c])=>[p,c,s.level]));
rows.sort((a,b)=>a[0].localeCompare(b[0]) || a[2]-b[2] || a[1].localeCompare(b[1]));
return rows.map(row=>({row})).concat(history.map(trace=>({trace})));"""
    return workflow


def rapidminer(edges, path):
    root = ET.Element("process", version="10.1.000")
    main = ET.SubElement(operator(root, "process", "Process", 0, 0), "process")
    seed_code = """def relation = new JsonSlurper().parseText('''EDGES''').unique(false)
def children = relation.collect { it[1] }.toSet()
def frontier = relation.findAll { !children.contains(it[0]) }
def h = operator.process.macroHandler
h.addMacro('frontier',JsonOutput.toJson(frontier))
h.addMacro('relation',JsonOutput.toJson(relation))
return table([[ready:true]])"""
    script(main, "Seed", 45, 35, seed_code.replace("EDGES", json.dumps(edges)))
    loop = operator(main, "loop_until", "Repeat", 245, 35)
    for key, val in dict(
        set_iteration_macro="true",
        macro_name="level",
        macro_start_value=1,
        condition_on_data="true",
        condition_on_performance="false",
        condition_before="false",
        min_examples=1,
        max_examples=1,
        min_attributes=1,
        max_attributes=1,
        max_iterations=100,
    ).items():
        param(loop, key, val)
    inner = ET.SubElement(loop, "process")
    script(
        inner,
        "Body",
        180,
        60,
        """def h = operator.process.macroHandler
int level = h.getMacro('level').toInteger()
def frontier = new JsonSlurper().parseText(h.getMacro('frontier'))
def relation = new JsonSlurper().parseText(h.getMacro('relation'))
def emitted = frontier.unique(false)
def expanded = emitted.collectMany { row -> relation.findAll { it[0]==row[1] }.collect { [row[0],it[1]] } }
def tips = emitted.collect { it[1] }.toSet()
def following = expanded + relation.findAll { !tips.contains(it[0]) }
h.addMacro('frontier',JsonOutput.toJson(expanded))
h.addMacro('relation',JsonOutput.toJson(following))
def trace = [level:level,incoming:frontier,relation:relation,expanded:expanded,following:following,emitted:emitted]
return [table([trace]),table(expanded.isEmpty() ? [[done:true]] : [])]""",
    )
    connect(inner, None, "input 1", "Body", "input 1")
    connect(inner, "Body", "output 1", None, "output 1")
    connect(inner, "Body", "output 2", None, "example set")
    script(
        main,
        "Collect",
        445,
        35,
        """def history = input[0].getObjects().collectMany { unpack(it) }
def rows = history.collectMany { s -> s.emitted.collect { [it[0],it[1],s.level] } }
rows.sort { a,b -> (a[0]<=>b[0]) ?: (a[2]<=>b[2]) ?: (a[1]<=>b[1]) }
return table(rows.collect { [row:it] } + history.collect { [trace:it] })""",
    )
    connect(main, "Seed", "output 1", "Repeat", "input 1")
    connect(main, "Repeat", "output 1", "Collect", "input 1")
    connect(main, "Collect", "output 1", None, "result 1")
    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf8", xml_declaration=True)


def prepare(source, out):
    with source.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == ["row ID", "parent", "child"]
        edges = [[r["parent"], r["child"]] for r in reader]
    out.mkdir(parents=True, exist_ok=False)
    for system, workflow in [("waffle", waffle(edges)), ("n8n", n8n(edges))]:
        (out / f"hierarchy-{system}.json").write_text(
            json.dumps(workflow, indent=2), encoding="utf8"
        )
    rapidminer(edges, out / "hierarchy.rmp")
    run = dict(
        case="hierarchy",
        strategy="recursive",
        workflow="hierarchy-waffle.json",
        fields=["payload"],
        pair=0,
        warmup=False,
    )
    (out / "manifest.json").write_text(
        json.dumps(dict(runs=[run]), indent=2), encoding="utf8"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("out", type=Path)
    a = p.parse_args()
    prepare(a.input, a.out)
