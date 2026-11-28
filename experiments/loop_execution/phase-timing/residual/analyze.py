"""Partition time outside the original startup and output-write timers."""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze_phases import read_capture


def traces(root, prefix):
    bundle = root / (prefix + "-events.zip")
    if bundle.exists():
        with ZipFile(bundle) as z:
            for name in sorted(z.namelist()):
                yield z.read(name).decode().splitlines()
    else:
        for p in sorted(root.glob(prefix + "-*.tsv")):
            yield p.read_text().splitlines()


def work(root):
    base = read_capture(root)
    native = [
        json.loads(line)
        for line in (root / "data/native.jsonl").read_text().splitlines()
    ]
    bounds = defaultdict(dict)
    events = defaultdict(list)
    active_read = Counter()
    read_rows = Counter()
    boundary_tuples = defaultdict(list)
    for line in (root / "jvm.tsv").read_text().splitlines():
        idx, kind, _, lo, hi = line.split("\t")
        i, lo, hi = int(idx), int(lo), int(hi)
        if kind in ("begin", "end"):
            bounds[i][kind] = lo
        else:
            events[i].append(("prior", kind, lo, hi))

    def sample(lo, hi):
        (i,) = [i for i, b in bounds.items() if b["begin"] <= lo <= hi <= b["end"]]
        return i

    for lines in traces(root, "python"):
        for line in lines:
            kind, _, lo, hi = line.split("\t")
            lo, hi = int(lo), int(hi)
            events[sample(lo, hi)].append(("prior", kind, lo, hi))
    for lines in traces(root, "residual"):
        for line in lines:
            kind, worker, lo, hi, active, rows = line.split("\t")
            lo, hi, active, rows = map(int, (lo, hi, active, rows))
            i = sample(lo, hi)
            assert worker.startswith(f"Worker:WF{native[i]['execution_id']}-")
            assert active >= 0 and rows >= 0
            if kind in ("port_read", "loop_read"):
                category = "read"
                active_read[i] += active
                read_rows[i] += rows
            else:
                assert kind in ("tuple_batch", "tuple_finish")
                category = "tuple"
                for boundary in ("LoopStart", "LoopEnd"):
                    if f"-{boundary}-operator-" in worker:
                        boundary_tuples[i].append((boundary, kind, lo, hi))
            events[i].append((category, kind, lo, hi))
    launch = {
        "r_plan",
        "r_allocate",
        "r_mount",
        "r_init",
        "r_assign",
        "r_connect",
        "r_open",
        "r_start",
    }
    for line in (root / "lifecycle.tsv").read_text().splitlines():
        idx, kind, _, lo, hi = line.split("\t")
        i, lo, hi = int(idx), int(lo), int(hi)
        assert sample(lo, hi) == i
        if kind in launch:
            category = "schedule"
        else:
            category = {"r_sink_read": "read", "r_retire": "retire"}[kind]
        events[i].append((category, kind, lo, hi))

    results = []
    masks = []
    for row in base:
        i = row["sample"]
        start, end = bounds[i]["begin"], bounds[i]["end"]
        delta = defaultdict(Counter)
        delta[start]
        delta[end]
        counts = Counter()
        for boundary, kind, lo, hi in boundary_tuples[i]:
            for key in (boundary, boundary + "_" + kind):
                delta[lo]["kind_" + key] += 1
                delta[hi]["kind_" + key] -= 1
        for cat, kind, lo, hi in events[i]:
            assert start <= lo <= hi <= end
            counts[kind] += 1
            for key in (cat, "kind_" + kind):
                delta[lo][key] += 1
                delta[hi][key] -= 1
        assert counts["r_plan"] and counts["r_sink_read"] == 1
        assert all(
            counts[k] == row["workers"] for k in (launch - {"r_plan"}) | {"r_retire"}
        ), counts
        assert counts["port_read"] and counts["tuple_batch"] and counts["tuple_finish"]
        assert counts["loop_read"] == (1 if row["strategy"] == "loop" else 0)
        assert bool(boundary_tuples[i]) == (row["strategy"] == "loop")
        state = Counter()
        split = Counter()
        individual = Counter()
        prev = start
        for instant, changes in sorted(delta.items()):
            length = instant - prev
            if length and not state["prior"]:
                mask = tuple(
                    sorted(
                        k for k, n in state.items() if n and not k.startswith("kind_")
                    )
                )
                split[mask] += length
                for k, n in state.items():
                    if n and k.startswith("kind_"):
                        individual[k[5:]] += length
            state.update(changes)
            assert all(v >= 0 for v in state.values())
            prev = instant
        assert not any(state.values())
        clock_delta = row["wall_s"] - (end - start) / 1e9
        assert abs(sum(split.values()) / 1e9 + clock_delta - row["outside_s"]) < 1e-7
        result = {
            **row,
            "reader_active_s": active_read[i] / 1e9,
            "reader_rows": read_rows[i],
            "read_calls": counts["port_read"] + counts["loop_read"],
            "region_count": counts["r_allocate"],
            "harness_delta_s": clock_delta,
        }
        for cat in ("read", "tuple", "schedule", "retire"):
            result[cat + "_only_s"] = split[(cat,)] / 1e9
            result[cat + "_inclusive_s"] = (
                sum(v for m, v in split.items() if cat in m) / 1e9
            )
        result["overlapping_s"] = sum(v for m, v in split.items() if len(m) > 1) / 1e9
        result["untraced_s"] = split[()] / 1e9
        for kind in sorted(
            launch
            | {
                "r_retire",
                "r_sink_read",
                "port_read",
                "loop_read",
                "tuple_batch",
                "tuple_finish",
                "LoopStart",
                "LoopStart_tuple_batch",
                "LoopStart_tuple_finish",
                "LoopEnd",
            }
        ):
            result[kind + "_s"] = individual[kind] / 1e9
        masks.extend(
            dict(sample=i, mask="+".join(mask) or "untraced", seconds=ns / 1e9)
            for mask, ns in sorted(split.items())
        )
        results.append(result)
    return results, masks


def summarize(rows, keys):
    groups = {
        s: sorted(
            [r for r in rows if not r["warmup"] and r["strategy"] == s],
            key=lambda r: r["pair"],
        )
        for s in ("loop", "copies")
    }
    assert all(
        [r["pair"] for r in group] == list(range(5)) for group in groups.values()
    )
    out = {
        s: {k: median(r[k] for r in group) for k in keys} for s, group in groups.items()
    }
    differences = {
        k: [
            loop[k] - copies[k]
            for loop, copies in zip(groups["loop"], groups["copies"])
        ]
        for k in keys
    }
    out.update(
        {
            name: {k: stat(v) for k, v in differences.items()}
            for name, stat in [("paired_median", median), ("paired_mean", mean)]
        }
    )
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    root = parser.parse_args().capture
    rows, masks = work(root)
    for name, data in [("residual-times", rows), ("residual-overlap", masks)]:
        with (root / (name + ".csv")).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)
    keys = [
        k
        for k in rows[0]
        if k.endswith("_s") or k in ("reader_rows", "region_count", "read_calls")
    ]
    stats = summarize(rows, keys)
    (root / "residual-summary.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(
        f"Verified {len(rows)} executions. Median paired residual: {stats['paired_median']['outside_s']:.3f} s"
    )


if __name__ == "__main__":
    main()
