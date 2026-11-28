"""Reconstruct the same LoopStart interval in both benchmark captures."""

import argparse
import csv
import json
from pathlib import Path
from statistics import median

from analyze import traces
from analyze_phases import intervals_union, read_capture


def windows(root, campaign):
    rows = read_capture(root)
    native = [
        json.loads(line)
        for line in (root / "data/native.jsonl").read_text().splitlines()
    ]
    python = [line.split("\t") for lines in traces(root, "python") for line in lines]
    jvm = [line.split("\t") for line in (root / "jvm.tsv").read_text().splitlines()]
    for row in rows:
        if row["strategy"] != "loop" or row["warmup"]:
            continue
        i = row["sample"]
        eid = str(native[i]["execution_id"])
        phases = [
            (kind, name, int(lo), int(hi))
            for kind, name, lo, hi in python
            if eid in name
        ]
        phases.extend(
            (kind, name, int(lo), int(hi))
            for idx, kind, name, lo, hi in jvm
            if int(idx) == i and kind not in ("begin", "end")
        )
        marks = [
            (kind, hi) for kind, name, _, hi in phases if "LoopStart-operator-" in name
        ]
        start = max(hi for kind, hi in marks if kind == "writer_setup")
        end = max(hi for kind, hi in marks if kind == "py_flush")
        assert start < end
        covered = intervals_union(
            [
                (max(start, lo), min(end, hi))
                for _, _, lo, hi in phases
                if lo < end and hi > start
            ]
        )
        yield dict(
            campaign=campaign,
            pair=row["pair"],
            elapsed_s=(end - start) / 1e9,
            covered_s=covered / 1e9,
            outside_s=(end - start - covered) / 1e9,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("traced", type=Path)
    args = parser.parse_args()
    results = [*windows(args.original, "original"), *windows(args.traced, "traced")]
    with (args.traced / "loopstart-window.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    for name in ("original", "traced"):
        group = [r["outside_s"] for r in results if r["campaign"] == name]
        print(
            name,
            "LoopStart window outside startup and writes:",
            round(median(group), 3),
            "s",
        )
