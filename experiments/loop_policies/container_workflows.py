"""Execute the same K-means bodies under native n8n and RapidMiner loop control."""

from concurrent.futures import ThreadPoolExecutor
import argparse
from functools import partial
import json
import subprocess
import sys
from xml.etree import ElementTree as ET
from prepare import ROOT, ART, points, specs, save, model

sys.path.insert(0, str(ART / "experiments/case_study"))
from n8n_cases import IMAGE as N8N

sys.path.insert(0, str(ART / "experiments/case_study/rapidminer"))
import build as rm

JS_SCORE = """
const s=$input.first().json, points=s.points, k=s.K;
const centers=points.slice(0,k).map(p=>[...p]);
const dist=(a,b)=>(a[0]-b[0])**2+(a[1]-b[1])**2;
for(let t=0;t<50;t++) {
  const sums=centers.map(()=>[0,0,0]);
  for(const p of points) {
    let best=0;
    for(let i=1;i<k;i++) if(dist(p,centers[i])<dist(p,centers[best])) best=i;
    sums[best][0]+=p[0]; sums[best][1]+=p[1]; sums[best][2]++;
  }
  let movement=0;
  for(let i=0;i<k;i++) if(sums[i][2]) for(let j=0;j<2;j++) {
    const v=sums[i][j]/sums[i][2];
    movement=Math.max(movement,Math.abs(v-centers[i][j])); centers[i][j]=v;
  }
  if(movement<1e-10) break;
}
const score=-points.reduce((sum,p)=>sum+Math.min(...centers.map(c=>dist(p,c))),0);
return [{json:{...s,score,rows:[...s.rows,{K:k,score}]}}];
"""


def js_controller(rule):
    step = "score < -250 ? 2*K : K+1" if rule == "adaptive" else "K+1"
    test = {
        "sweep": "next<=4",
        "target": "next<=4 && score < -100",
        "adaptive": "next<=4 && score < -100",
        "history": "next<=4 && (K===2 || score-s.previous>=150)",
    }[rule]
    return (
        "const s=$input.first().json, {K,score}=s;\nconst next="
        + step
        + ";\n"
        + "return [{json:{...s,K:next,"
        + ("previous:score," if rule == "history" else "")
        + "again:"
        + test
        + "}}];"
    )


def n8n(spec, folder):
    nodes = []
    edges = {}

    def node(name, kind, ver, params, x, y):
        nodes.append(
            dict(
                id=name,
                name=name,
                type="n8n-nodes-base." + kind,
                typeVersion=ver,
                parameters=params,
                position=[x, y],
            )
        )

    def connect(src, *dest):
        edges[src] = {"main": [[dict(node=d, type="main", index=0)] for d in dest]}

    rule = spec["task"]
    node("Start", "manualTrigger", 1, {}, 0, 0)
    node(
        "Init",
        "code",
        2,
        dict(
            jsCode="return [{json:{K:2,rows:[],points:"
            + json.dumps(points(spec["fixture"]))
            + "}}];"
        ),
        150,
        0,
    )
    node("Body", "code", 2, dict(jsCode=JS_SCORE), 300, 0)
    node("Update", "code", 2, dict(jsCode=js_controller(rule)), 470, 0)
    node(
        "Continue",
        "if",
        1,
        {
            "conditions": {
                "boolean": [
                    {
                        "value1": "={{ $json.again }}",
                        "operation": "equal",
                        "value2": True,
                    }
                ]
            }
        },
        640,
        0,
    )
    node(
        "Result",
        "code",
        2,
        dict(jsCode="return $input.first().json.rows.map(r=>({json:r}));"),
        820,
        0,
    )
    connect("Start", "Init")
    connect("Init", "Body")
    connect("Body", "Update")
    connect("Update", "Continue")
    connect("Continue", "Body", "Result")
    path = folder / "workflow.json"
    save(
        path,
        dict(
            id="adaptiveProbe",
            name=spec["id"],
            active=False,
            nodes=nodes,
            connections=edges,
            settings={"executionOrder": "v1"},
        ),
    )
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "-e",
        "N8N_DIAGNOSTICS_ENABLED=false",
        "-v",
        str(path) + ":/case.json:ro",
        "--entrypoint",
        "sh",
        N8N,
        "-ec",
        "n8n import:workflow --input=/case.json >&2; exec n8n execute --id adaptiveProbe --rawOutput",
    ]
    result = subprocess.run(
        cmd, timeout=150, capture_output=True, encoding="utf-8", errors="replace"
    )
    (folder / "engine.log").write_text(
        result.stderr + "\n" + result.stdout, encoding="utf-8"
    )
    result.check_returncode()
    record, _ = json.JSONDecoder().raw_decode(
        result.stdout[result.stdout.index("{\n") :]
    )
    assert record["status"] == "success"
    trace = record["data"]["resultData"]["runData"]
    visits = [
        {k: r["data"]["main"][0][0]["json"][k] for k in ("K", "score")}
        for r in trace["Body"]
    ]
    rows = [r["json"] for r in trace["Result"][0]["data"]["main"][0]]
    assert model.compare(spec["expected"], visits), visits
    return rows, len(visits)


def rapidminer(spec, folder):
    rule = spec["task"]
    doc = ET.Element("process", version="10.1.000")
    p = ET.SubElement(rm.operator(doc, "process", "Process", 0, 0), "process")
    rm.script(
        p,
        "Init",
        45,
        35,
        "operator.process.macroHandler.addMacro('k','2')\nreturn table("
        + json.dumps(points(spec["fixture"]))
        + ")",
    )
    loop = rm.operator(p, "loop_until", "Repeat", 245, 35)
    for k, v in dict(
        condition_on_data="true",
        condition_on_performance="false",
        condition_before="false",
        min_examples=1,
        max_examples=1,
        min_attributes=1,
        max_attributes=1,
        max_iterations=8,
    ).items():
        rm.param(loop, k, v)
    inside = ET.SubElement(loop, "process")
    java = (ART / "experiments/user_study/KMeansBody.java.txt").read_text()
    body = java[java.index("double[][] centers") : java.index("out_k=k")].replace(
        "centers[c]=points[c].clone()",
        "{centers[c][0]=points[c][0];centers[c][1]=points[c][1];}",
    )
    rm.script(
        inside,
        "Body",
        30,
        35,
        "int k=Integer.parseInt(operator.process.macroHandler.getMacro('k'))\ndouble[][] points=unpack(input[0]) as double[][]\n"
        + body
        + "\nreturn table([[K:k,score:value]])",
    )
    code = "def m=operator.process.macroHandler, r=unpack(input[0])[0]\nint k=r.K; double score=r.score\n"
    code += (
        "int next="
        + ("score < -250 ? 2*k : k+1" if rule == "adaptive" else "k+1")
        + "\n"
    )
    test = {
        "sweep": "next<=4",
        "target": "next<=4 && score < -100",
        "adaptive": "next<=4 && score < -100",
        "history": "next<=4 && (k==2 || score-Double.parseDouble(m.getMacro('prev'))>=150)",
    }[rule]
    code += "boolean again=" + test + "\n"
    if rule == "history":
        code += "m.addMacro('prev',Double.toString(score))\n"
    code += "m.addMacro('k',Integer.toString(next))\nreturn [input[0],table(again ? [] : [[stop:true]])]"
    rm.script(inside, "Update", 225, 35, code)
    rm.connect(inside, None, "input 1", "Body", "input 1")
    rm.connect(inside, "Body", "output 1", "Update", "input 1")
    rm.connect(inside, "Update", "output 1", None, "output 1")
    rm.connect(inside, "Update", "output 2", None, "example set")
    rm.script(
        p,
        "Collect",
        445,
        35,
        "return table(input[0].getObjects().collectMany { unpack(it) })",
    )
    rm.connect(p, "Init", "output 1", "Repeat", "input 1")
    rm.connect(p, "Repeat", "output 1", "Collect", "input 1")
    rm.connect(p, "Collect", "output 1", None, "result 1")
    path = folder / "workflow.rmp"
    ET.indent(doc)
    ET.ElementTree(doc).write(path, encoding="utf-8", xml_declaration=True)
    out = folder / "out"
    out.mkdir(exist_ok=True)
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "-v",
        str(path) + ":/case.rmp:ro",
        "-v",
        str(out) + ":/out",
        "waffle-rapidminer:10.1.0",
        "/case.rmp",
        "/out/run.json",
    ]
    with (folder / "engine.log").open("w", encoding="utf-8") as log:
        subprocess.run(cmd, timeout=120, check=True, stdout=log, stderr=log)
    record = json.loads((out / "run.json").read_text())
    return record["rows"], record["iterations"]


def run(spec, name):
    folder = ROOT / name / spec["id"]
    folder.mkdir(parents=True, exist_ok=False)
    rows, count = ({"n8n": n8n, "rapidminer": rapidminer}[name])(spec, folder)
    assert model.compare(spec["expected"], rows) and count == len(rows), (
        spec["expected"],
        rows,
        count,
    )
    save(folder / "observed.json", dict(rows=rows, iterations=count))
    print(name, spec["id"], [r["K"] for r in rows], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("engine", choices=["n8n", "rapidminer"])
    parser.add_argument("--case", help="Run one rule/fixture ID from the manifest")
    args = parser.parse_args()
    selected = [s for s in specs() if args.case is None or s["id"] == args.case]
    if not selected:
        parser.error("No matching case")
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(partial(run, name=args.engine), selected))
