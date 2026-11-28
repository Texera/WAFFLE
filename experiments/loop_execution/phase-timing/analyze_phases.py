"""Verify native results and compute wall time in worker-start and storage calls."""

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from statistics import median
from zipfile import ZipFile


def intervals_union(spans):
    total = 0
    end = None
    for left, right in sorted(spans):
        assert left <= right
        if end is None or left >= end:
            total += right - left
        elif right > end:
            total += right - end
        end = right if end is None else max(right, end)
    return total


def read_capture(root):
    rows = [
        json.loads(line)
        for line in (root / "data/native.jsonl").read_text().splitlines()
    ]
    assert (root / "data/exit-code.txt").read_text().strip() == "0"
    assert [r["sample"] for r in rows] == list(range(12))
    verification = json.loads((root / "verification.json").read_text())
    assert (
        verification["coverage_probe_matches"] == 0
        and verification["compiled_classes_scanned"] > 0
    )
    schedule = json.loads((root / "data/manifest.json").read_text())["runs"]
    assert len(schedule) == 12
    events = {i: [] for i in range(12)}
    anchors = {i: {} for i in range(12)}
    for line in (root / "jvm.tsv").read_text().splitlines():
        idx, kind, worker, lo, hi = line.split("\t")
        i, lo, hi = int(idx), int(lo), int(hi)
        if kind in ("begin", "end"):
            assert kind not in anchors[i]
            anchors[i][kind] = lo
        else:
            assert kind in ("startup", "create", "jvm_flush") and hi > lo
            events[i].append((kind, worker, lo, hi))
    if (root / "python-events.zip").exists():
        with ZipFile(root / "python-events.zip") as archive:
            traces = [
                (name, archive.read(name).decode("utf8")) for name in archive.namelist()
            ]
    else:
        traces = [
            (file.name, file.read_text()) for file in sorted(root.glob("python-*.tsv"))
        ]
    for file, trace in traces:
        for line in trace.splitlines():
            kind, name, lo, hi = line.split("\t")
            lo, hi = int(lo), int(hi)
            assert kind in ("writer_setup", "py_flush") and hi > lo
            matches = [
                i for i, a in anchors.items() if a["begin"] <= lo <= hi <= a["end"]
            ]
            assert len(matches) == 1, (file, kind, matches)
            events[matches[0]].append((kind, name, lo, hi))
    metrics = []
    for row, plan in zip(rows, schedule):
        i = row["sample"]
        strategy = row["strategy"]
        for key in ["strategy", "warmup", "pair", "case"]:
            assert row[key] == plan[key]
        assert len(row["rows"]) == len(plan["expected"]) == 1
        expected = plan["expected"][0]
        actual = row["rows"][0]
        assert actual["K"] == expected["K"] == 2 and math.isclose(
            actual["score"], expected["score"], abs_tol=1e-9, rel_tol=1e-9
        )
        assert (
            abs(anchors[i]["end"] - anchors[i]["begin"] - row["execution_ns"])
            < 30_000_000
        )
        es = events[i]
        counts = Counter(k for k, *_ in es)
        for kind, name, left, right in es:
            assert anchors[i]["begin"] <= left <= right <= anchors[i]["end"]
        worker_count = {"copies": 3, "loop": 5}[strategy]
        assert counts["startup"] == worker_count
        assert len({name for k, name, _, _ in es if k == "startup"}) == worker_count
        assert (
            counts["writer_setup"] >= worker_count
            and counts["create"] >= worker_count
            and counts["py_flush"] >= worker_count
        ), counts
        assert all(str(row["execution_id"]) in name for _, name, _, _ in es)
        startups = [(a, b) for k, _, a, b in es if k == "startup"]
        storage = [(a, b) for k, _, a, b in es if k != "startup"]
        sns = intervals_union(startups)
        mns = intervals_union(storage)
        covered = intervals_union(startups + storage)
        assert covered <= row["execution_ns"] + 30_000_000
        metrics.append(
            dict(
                sample=i,
                pair=row["pair"],
                strategy=strategy,
                warmup=row["warmup"],
                wall_s=row["execution_ns"] / 1e9,
                startup_s=sns / 1e9,
                materialization_s=mns / 1e9,
                overlap_s=(sns + mns - covered) / 1e9,
                outside_s=(row["execution_ns"] - covered) / 1e9,
                workers=counts["startup"],
                creates=counts["create"],
                writer_setups=counts["writer_setup"],
                python_flushes=counts["py_flush"],
                jvm_flushes=counts["jvm_flush"],
            )
        )
    return metrics


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("capture", type=Path)
    a = ap.parse_args()
    data = read_capture(a.capture)
    with (a.capture / "phase-times.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows(data)
    measured = [r for r in data if not r["warmup"]]
    keys = ["wall_s", "startup_s", "materialization_s", "overlap_s", "outside_s"]
    report = {}
    for name in ["loop", "copies"]:
        group = [r for r in measured if r["strategy"] == name]
        assert len(group) == 5
        report[name] = {k: median(r[k] for r in group) for k in keys}
    report["median_paired_difference"] = {}
    for k in keys:
        diff = []
        for pair in range(5):
            group = {r["strategy"]: r[k] for r in measured if r["pair"] == pair}
            diff.append(group["loop"] - group["copies"])
        report["median_paired_difference"][k] = median(diff)
    (a.capture / "phase-summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
