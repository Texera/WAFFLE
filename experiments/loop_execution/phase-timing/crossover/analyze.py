"""Verify the timers and estimate their incremental cost in matched blocks."""

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


def python_lines(root):
    bundle = root / "residual-events.zip"
    if bundle.exists():
        with ZipFile(bundle) as z:
            for name in z.namelist():
                yield from z.read(name).decode().splitlines()
    else:
        for p in root.glob("residual-*.tsv"):
            yield from p.read_text().splitlines()


def write_csv(p, records):
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)


def measurements(root):
    rows = read_capture(root, expected_samples=36)
    original = Path(__file__).resolve().parents[1] / "capture"
    previous = json.loads((original / "verification.json").read_text())
    current = json.loads((root / "verification.json").read_text())
    for key in (
        "tree",
        "original_input_sha256",
        "compiled_classes_scanned",
        "class_sha256_aggregate",
        "java_flags",
        "coverage_probe_matches",
    ):
        assert current[key] == previous[key], key
    plan = json.loads((root / "data/manifest.json").read_text())["runs"]
    native = [
        json.loads(line)
        for line in (root / "data/native.jsonl").read_text().splitlines()
    ]
    ids = {f"Worker:WF{r['execution_id']}": r["sample"] for r in native}
    assert len(ids) == 36
    detail = defaultdict(Counter)
    for line in python_lines(root):
        kind, worker, *_ = line.split("\t")
        detail[ids[worker.split("-", 1)[0]]][kind] += 1
    for line in (root / "lifecycle.tsv").read_text().splitlines():
        sample, kind, *_ = line.split("\t")
        detail[int(sample)][kind] += 1
    by_cell = defaultdict(Counter)
    precedence = Counter()
    for row, run, planned in zip(rows, native, plan):
        i = row["sample"]
        assert row["pair"] == i // 4 - 1 and row["warmup"] == (i < 4)
        assert isinstance(run["trace"], bool) and run["trace"] == planned["trace"]
        assert bool(detail[i]) == run["trace"], (i, detail[i])
        if run["trace"]:
            assert all(
                detail[i][k] > 0
                for k in (
                    "port_read",
                    "tuple_batch",
                    "tuple_finish",
                    "r_plan",
                    "r_sink_read",
                )
            )
            assert detail[i]["loop_read"] == int(row["strategy"] == "loop")
            assert detail[i]["r_allocate"] == row["workers"] == detail[i]["r_retire"]
        row.update(
            trace=run["trace"], position=i % 4, extra_events=sum(detail[i].values())
        )
        if not row["warmup"]:
            cell = (row["strategy"], row["trace"])
            by_cell[cell][i % 4] += 1
            if i % 4:
                prev = rows[i - 1]
                precedence[((prev["strategy"], prev["trace"]), cell)] += 1
    assert len(by_cell) == 4 and all(
        c == Counter({0: 2, 1: 2, 2: 2, 3: 2}) for c in by_cell.values()
    )
    assert (
        len(precedence) == 12
        and set(precedence.values()) == {2}
        and all(a != b for a, b in precedence)
    )
    return rows


def analyze(root):
    rows = measurements(root)
    blocks = []
    for pair in range(8):
        cells = {(r["strategy"], r["trace"]): r for r in rows if r["pair"] == pair}
        assert len(cells) == 4
        block = {"block": pair}
        for metric in (
            "wall_s",
            "outside_s",
            "startup_s",
            "materialization_s",
            "overlap_s",
        ):
            for trace in (False, True):
                block[f"{metric}_gap_{'on' if trace else 'off'}"] = (
                    cells["loop", trace][metric] - cells["copies", trace][metric]
                )
            for strategy in ("loop", "copies"):
                block[f"{metric}_{strategy}_on_minus_off"] = (
                    cells[strategy, True][metric] - cells[strategy, False][metric]
                )
            change = block[f"{metric}_gap_on"] - block[f"{metric}_gap_off"]
            assert (
                abs(
                    change
                    - (
                        block[f"{metric}_loop_on_minus_off"]
                        - block[f"{metric}_copies_on_minus_off"]
                    )
                )
                < 1e-9
            )
            block[f"{metric}_change_in_gap"] = change
        blocks.append(block)
    write_csv(root / "per-workflow.csv", rows)
    write_csv(root / "per-block.csv", blocks)
    stats = {}
    for k in blocks[0]:
        if k == "block":
            continue
        values = [b[k] for b in blocks]
        stats[k] = dict(
            median=median(values),
            mean=mean(values),
            minimum=min(values),
            maximum=max(values),
            positive=sum(v > 0 for v in values),
        )
    (root / "summary.json").write_text(json.dumps(stats, indent=2) + "\n")
    for k in ("wall_s", "outside_s"):
        print(
            k,
            "median change in gap:",
            round(stats[f"{k}_change_in_gap"]["median"], 3),
            "s",
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("capture", type=Path)
    analyze(p.parse_args().capture)
