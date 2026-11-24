"""Execute translated branches against the two local comparison-system images."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

N8N = "n8nio/n8n@sha256:fabce3e9678a07d2dde83bd8f5124017f3ec457d0a3fc6b63bb4cec465d63861"
RAPIDMINER = "waffle-rapidminer:10.1.0"


def run(directory, system, kinds=("sum", "fib")):
    for kind in kinds:
        out = directory / (kind + "-" + system + "-run.json")
        if out.exists():
            raise FileExistsError(out)
        if system == "n8n":
            path = directory / (kind + "-n8n.json")
            graph = json.loads(path.read_bytes())
            cmd = ["docker","run","--rm","--network","none","-e","N8N_DIAGNOSTICS_ENABLED=false",
                   "-v",f"{path}:/case.json:ro","--entrypoint","sh",N8N,"-ec",
                   'n8n import:workflow --input=/case.json >&2; exec n8n execute --id "$1" --rawOutput',
                   "sh",graph["id"]]
        else:
            path = directory / (kind + ".rmp")
            cmd = ["docker","run","--rm","--network","none","-v",f"{path}:/input.rmp:ro",
                   "-v",f"{directory}:/out",RAPIDMINER,"/input.rmp","/out/"+out.name]
        proc = subprocess.run(cmd,capture_output=True,encoding="utf8",errors="replace")
        (directory / f"{kind}-{system}.log").write_text(proc.stderr+"\n"+proc.stdout,encoding="utf8")
        proc.check_returncode()
        if system=="n8n":
            doc,_=json.JSONDecoder().raw_decode(proc.stdout[proc.stdout.index("{\n"):])
            data=doc["data"]["resultData"]
            assert doc["finished"] and doc["status"]=="success" and data["lastNodeExecuted"]=="Result" and "error" not in data
            trace=data["runData"]
            rows=[it["json"] for it in trace["Result"][0]["data"]["main"][0]]
            record=dict(image=N8N, iterations=len(trace["Body"]),rows=rows)
        else:
            record=json.loads(out.read_bytes())
        record["workflow_sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
        out.write_text(json.dumps(record,indent=2)+"\n",encoding="utf8")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("system",choices=["n8n","rapidminer"])
    p.add_argument("directory",type=Path)
    a=p.parse_args()
    run(a.directory.resolve(),a.system)
