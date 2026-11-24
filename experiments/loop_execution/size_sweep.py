"""Verify graph size and wiring at dense small lengths and larger powers of two through 131,072."""
import argparse
import csv
from pathlib import Path
from experiment import graph


def sweep():
    for count in (*range(1, 1025), *(2**p for p in range(11, 18))):
        for method in ("loop", "copies"):
            workflow = graph(Path("points.csv"), count, method)
            names = [op["operatorID"] for op in workflow["operators"]]
            edges = {(e["source"]["operatorID"],e["target"]["operatorID"]) for e in workflow["links"]}
            if method == "loop":
                assert len(names) == 5
                expected = set(zip(names, names[1:]))
            else:
                assert len(names) == count + 2
                expected = {(names[0],op) for op in names[1:-1]} | {(op,names[-1]) for op in names[1:-1]}
            assert len(set(names)) == len(names) and edges == expected and len(workflow["links"]) == len(edges)
            yield (count, method, len(names), len(edges))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    with args.output.open("x",encoding="utf8",newline="") as stream:
        writer=csv.writer(stream,lineterminator="\n")
        writer.writerow(("candidates","workflow","operators","links"))
        writer.writerows(sweep())
