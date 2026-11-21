"""Make four loop policies on four scaled versions of the same 16 K-means points."""

import csv
import json
import os
from pathlib import Path
import sys

ROOT = Path(os.environ.get("WAFFLE_POLICY_RUN", "policy-run")).resolve()
ART = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ART / "experiments/user_study"))
import model
import waffle

SCALES = {"immediate": 0.1, "near": 0.7, "far": 1, "unreachable": 10}
POLICIES = ["sweep", "target", "adaptive", "history"]
# Fixed before launching the four engines; each entry is the list of actual K visits.
VISITS = {
    "sweep": [[2, 3, 4], [2, 3, 4], [2, 3, 4], [2, 3, 4]],
    "target": [[2], [2, 3], [2, 3, 4], [2, 3, 4]],
    "adaptive": [[2], [2, 3], [2, 4], [2, 4]],
    "history": [[2, 3], [2, 3], [2, 3, 4], [2, 3, 4]],
}
INIT = {p: "K = 2" for p in POLICIES}
INIT["history"] += "\nprevious = 0.0"
UPDATE = {p: "K += 1" for p in POLICIES}
UPDATE["adaptive"] = "K = 2 * K if score < -250 else K + 1"
UPDATE["history"] = (
    "again = K == 2 or score - previous >= 150\nprevious = score\nK += 1"
)
CONDITION = {
    "sweep": "K <= 4",
    "target": "K <= 4 and score < -100",
    "adaptive": "K <= 4 and score < -100",
    "history": "K <= 4 and again",
}


def save(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def points(fixture):
    with (ROOT / "data" / fixture / "points.csv").open() as f:
        return [[float(row["x"]), float(row["y"])] for row in csv.DictReader(f)]


def specs():
    return json.loads((ROOT / "manifest.json").read_text())["runs"]


def prepare():
    # Source points are identical to the study's Workflow A before scaling.
    centers = [(0, 0), (8, 8), (0, 8), (8, 0)]
    runs = []
    ROOT.mkdir(parents=True, exist_ok=False)
    (ROOT / "facilitator").mkdir()
    for index, (fixture, scale) in enumerate(SCALES.items()):
        data = ROOT / "data" / fixture
        data.mkdir(parents=True)
        with (data / "points.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["x", "y"])
            for dx, dy in [(0, 0), (0.4, -0.2), (-0.3, 0.5), (0.2, 0.3)]:
                w.writerows([((x + dx) * scale, (y + dy) * scale) for x, y in centers])
        reference = {r["K"]: r for r in model.scores(data / "points.csv")}
        for rule in POLICIES:
            label = rule + "-" + fixture
            folder = ROOT / "waffle" / label
            folder.mkdir(parents=True)
            g = waffle.graph(data, folder, "sweep", -100, short=True)
            for op in g["operators"]:
                if op["operatorType"] == "LoopStart":
                    op["operatorProperties"]["initialization"] = INIT[rule]
                if op["operatorType"] == "LoopEnd":
                    op["operatorProperties"].update(
                        update=UPDATE[rule], condition=CONDITION[rule]
                    )
            path = folder / "workflow.json"
            save(path, g)
            runs.append(
                dict(
                    id=label,
                    tool="waffle",
                    task=rule,
                    fixture=fixture,
                    workflow=path.relative_to(ROOT).as_posix(),
                    expected=[reference[k] for k in VISITS[rule][index]],
                )
            )
    save(ROOT / "manifest.json", dict(runs=runs))


if __name__ == "__main__":
    prepare()
