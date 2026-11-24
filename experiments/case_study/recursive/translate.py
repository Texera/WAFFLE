"""Translate the two disconnected output branches of published workflow 07."""
import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "rapidminer"))
sys.path.insert(0, str(HERE.parents[1] / "loop_execution"))
from build import connect, operator, param, script
from experiment import graph
from prepare_knime import config, entry

BRANCHES = {"sum": (1, 7), "fib": (8, 3)}


def read_spec(original, seed_id, end_id):
    root = ET.parse(original).getroot()
    settings = {int(entry(node, "id").get("value")): original.parent / entry(node, "node_settings_file").get("value")
                for node in config(root, "nodes")}
    seed = config(ET.parse(settings[seed_id]).getroot(), "model")
    values = config(seed, "values")
    assert entry(values, "array-size").get("value") == "2"
    model = config(ET.parse(settings[end_id]).getroot(), "model")
    count = next(x.get("value") for x in model.iter() if x.get("key") == "CFG_MaxNrIterations")
    return [int(entry(values, str(i)).get("value")) for i in range(2)], int(count)


def waffle(kind, seed, limit):
    g = graph(Path("unused"), limit, "loop")
    source, start, body, end, sink = g["operators"]
    fields = [dict(attributeName=k, attributeType="integer") for k in ("x", "y")]
    source["operatorProperties"].update(columns=fields, code=f"""from pytexera import *
class Seed(UDFSourceOperator):
    def produce(self):
        yield dict(x={seed[0]}, y={seed[1]})
""")
    start["operatorProperties"] = dict(initialization="i = 0\na = int(D.iloc[0]['x'])\nb = int(D.iloc[0]['y'])", output="D")
    step = "a + 1, b + a + 1" if kind == "sum" else "b, a + b"
    body["operatorProperties"].update(outputColumns=fields, code=f"""from pytexera import *
class Advance(UDFOperatorV2):
    def process_state(self, state, port):
        return None

    def process_tuple(self, row, port):
        a, b = int(self.state['a']), int(self.state['b'])
        self.x, self.y = {step}
        yield dict(x=self.x, y=self.y)

    def produce_state_on_finish(self, port):
        return State(dict(self.state, next_a=self.x, next_b=self.y))
""")
    end["operatorProperties"] = dict(update="a = next_a\nb = next_b\ni += 1", condition=f"i < {limit}")
    sink["operatorProperties"].update(outputColumns=fields)
    return g


def n8n(kind, seed, limit):
    # Reuse the published comparison's feedback-edge topology.
    g = json.loads((HERE.parent / "n8n_results/13-n8n.json").read_text())
    g.update(id="recursive07" + kind, name="Recursive loop - " + kind)
    nodes = {n["name"]:n["parameters"] for n in g["nodes"]}
    nodes["Input"]["jsCode"] = f"return [{{x:{seed[0]}, y:{seed[1]}, collected:[], i:0}}];"
    step = "[x+1, y+x+1]" if kind == "sum" else "[y, x+y]"
    nodes["Body"]["jsCode"] = ("const {x,y,collected,i} = $input.first().json;\n"
                                f"const [a,b] = {step};\n"
                                "return [{x:a,y:b,i:i+1,collected:collected.concat({x:a,y:b})}];")
    nodes["Continue"]["conditions"]["number"][0]["value2"] = limit
    return g


def rapidminer(kind, seed, limit, destination):
    root = ET.Element("process", version="10.1.000")
    main = ET.SubElement(operator(root,"process","Process",0,0), "process")
    script(main,"Seed",45,35, f"""def h = operator.process.macroHandler
h.addMacro('currentX','{seed[0]}')
h.addMacro('currentY','{seed[1]}')
return table([[x:{seed[0]},y:{seed[1]}]])""")
    loop = operator(main, "loop", "Repeat", 245, 35)
    param(loop,"iterations",str(limit))
    param(loop,"enable_parallel_execution","false")
    inner = ET.SubElement(loop, "process")
    step = "[x+1,y+x+1]" if kind == "sum" else "[y,x+y]"
    script(inner,"Body",180,60, f"""def h = operator.process.macroHandler
int x = h.getMacro('currentX').toInteger()
int y = h.getMacro('currentY').toInteger()
def (a,b) = {step}
h.addMacro('currentX',a.toString())
h.addMacro('currentY',b.toString())
return table([[x:a,y:b]])""")
    connect(inner, None,"input 1","Body","input 1")
    connect(inner,"Body","output 1",None,"output 1")
    script(main,"Collect",445,35,"return table(input[0].getObjects().collectMany { unpack(it) })")
    connect(main,"Seed","output 1","Repeat","input 1")
    connect(main,"Repeat","output 1","Collect","input 1")
    connect(main,"Collect","output 1",None,"result 1")
    ET.indent(root,space="  ")
    ET.ElementTree(root).write(destination,encoding="utf-8",xml_declaration=True)


def prepare(original, out):
    out.mkdir(parents=True, exist_ok=False)
    runs = []
    for kind,(seed_id,end_id) in BRANCHES.items():
        seed,limit = read_spec(original,seed_id,end_id)
        for name,workflow in [("waffle",waffle(kind,seed,limit)),("n8n",n8n(kind,seed,limit))]:
            (out / f"{kind}-{name}.json").write_text(json.dumps(workflow,indent=2),encoding="utf8")
        rapidminer(kind,seed,limit,out / f"{kind}.rmp")
        runs.append(dict(case=kind,strategy="recursive",workflow=kind+"-waffle.json",fields=["x","y"],pair=0,warmup=False))
    (out/"manifest.json").write_text(json.dumps(dict(runs=runs),indent=2),encoding="utf8")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workflow",type=Path)
    parser.add_argument("out",type=Path)
    args=parser.parse_args()
    prepare(args.workflow,args.out)
