"""Vary the stop fraction on matched graphs using the public WAFFLE operator driver."""
import argparse
import csv
from pathlib import Path
import sys


def measure(artifact, runtime, output):
    sys.path.insert(0, str(artifact / "experiments" / "generated_loops"))
    from corpus import FIXTURES, cases, graph
    from evaluate import checked
    from provenance import pinned_runtime

    pinned_runtime(runtime)
    sys.path.insert(0, str(runtime / "amber" / "src" / "main" / "python"))
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(("graph", "input", "fraction", "visits", "rows_meeting", "rows_total", "threshold_met"))
        for index, (family, _, arms) in enumerate(cases()):
            if family != "stopping":
                continue
            for fixture, values in FIXTURES.items():
                for policy, fraction in enumerate(("1/3", "1/2", "2/3")):
                    workflow = graph(family, policy, arms, values)
                    rows, _, last = checked(workflow, family, policy, arms, values)
                    score, count = int(last["score"]), int(last["count"])
                    met = 6 * score >= (2 + policy) * count
                    writer.writerow((index, fixture, fraction, len(rows), score, count, int(met)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="WAFFLE artifact checkout at 348589e or a compatible revision")
    parser.add_argument("runtime", type=Path, help="runtime prepared from implementation.lock.json")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    measure(args.artifact.resolve(), args.runtime.resolve(), args.output)
