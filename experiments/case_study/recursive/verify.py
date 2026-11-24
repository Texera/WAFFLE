"""Compare all native result rows to the reset original and independent sequence formulas."""
import argparse
import csv
from collections import Counter
import hashlib
import json
from pathlib import Path


def fib_pair(n):
    # Fast doubling is independent of the translated two-value shift recurrence.
    if not n:
        return 0, 1
    a,b=fib_pair(n//2)
    c,d=a*(2*b-a),a*a+b*b
    return (d,c+d) if n%2 else (c,d)


def table(path,columns):
    with path.open(encoding="utf-8-sig",newline="") as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=["row ID",*columns]:
            raise ValueError(f"Unexpected original schema in {path.name}")
        return [(int(row[columns[0]]),int(row[columns[1]])) for row in reader]


def check(reference,translations):
    run=json.loads((reference/"07-knime-run.json").read_bytes())
    assert run["exit_code"]==0 and run["exports_present"]
    assert (translations/"exit-code.txt").read_text().strip()=="0"
    native=[json.loads(line) for line in (translations/"native.jsonl").read_bytes().splitlines()]
    assert len(native)==2 and {r["case"] for r in native}=={"sum","fib"}
    report={}
    for kind,cols,seed,count in [("sum",["n","sum(1n)"],(0,0),10),("fib",["F(n-1)","F(n)"],(0,1),30)]:
        assert table(reference/(kind+"-input.csv"),cols)==[seed]
        rows=table(reference/(kind+"-output.csv"),cols)
        oracle=[(i,i*(i+1)//2) if kind=="sum" else fib_pair(i) for i in range(1,count+1)]
        assert rows==oracle,(kind,"original")
        provenance=translations/"waffle-provenance.json"
        if provenance.exists():
            graph=translations/(kind+"-waffle.json")
            assert json.loads(provenance.read_bytes())["workflow_sha256"][graph.name]==hashlib.sha256(graph.read_bytes()).hexdigest()
        outputs={"waffle":next(r["rows"] for r in native if r["case"]==kind)}
        for system,filename in [("n8n",kind+"-n8n.json"),("rapidminer",kind+".rmp")]:
            record=json.loads((translations/f"{kind}-{system}-run.json").read_bytes())
            assert record["iterations"]==count
            assert record["workflow_sha256"]==hashlib.sha256((translations/filename).read_bytes()).hexdigest()
            outputs[system]=record["rows"]
        for system,actual in outputs.items():
            assert all(set(row)=={"x","y"} and all(type(v) is int for v in row.values()) for row in actual)
            assert Counter((r["x"],r["y"]) for r in actual)==Counter(rows),(kind,system)
        report[kind]=dict(rows=len(rows),seed=seed,final=rows[-1],matched=["KNIME","WAFFLE","n8n","RapidMiner"])
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("reference",type=Path,nargs="?",default=Path(__file__).with_name("results"))
    p.add_argument("translations",type=Path,nargs="?",default=Path(__file__).with_name("results"))
    a=p.parse_args()
    print(json.dumps(check(a.reference,a.translations),indent=2))
