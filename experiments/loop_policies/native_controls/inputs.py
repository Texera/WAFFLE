"""Replay measured score inputs while exercising the four systems' loop controls."""

from pathlib import Path
import csv
import json
import os
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from prepare import (  # noqa: E402
    ART as ART,
    CONDITION,
    INIT,
    POLICIES,
    SCALES,
    UPDATE,
    VISITS,
    model,
    save,
    waffle,
)

RUN = Path(
    os.environ.get("WAFFLE_NATIVE_CONTROLS_RUN", "native-controls-run")
).resolve()


def curve(fixture):
    with (RUN / "data" / fixture / "scores.csv").open(newline="") as f:
        return {int(r["K"]): float(r["score"]) for r in csv.DictReader(f)}


def cases():
    return json.loads((RUN / "manifest.json").read_text(encoding="utf-8"))["runs"]


def prepare():
    RUN.mkdir(parents=True, exist_ok=False)
    (RUN / "facilitator").mkdir()
    with (HERE.parent / "results/observations.csv").open(newline="") as f:
        sweeps = {
            r["fixture"]: json.loads(r["output"])
            for r in csv.DictReader(f)
            if r["rule"] == "sweep" and r["engine"] == "waffle"
        }
    runs = []
    for index, fixture in enumerate(SCALES):
        data = RUN / "data" / fixture
        data.mkdir(parents=True)
        source = data / "scores.csv"
        scores = sweeps[fixture]
        reference = model.scores(
            HERE.parent / "results/inputs" / fixture / "points.csv"
        )
        if not model.compare(reference, scores):
            raise ValueError("Input scores disagree with NumPy")
        with source.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["K", "score"])
            w.writeheader()
            w.writerows(scores)
        for rule in POLICIES:
            label = f"{rule}-{fixture}"
            folder = RUN / "waffle" / label
            folder.mkdir(parents=True)
            graph = waffle.graph(data, folder, "sweep", -100, short=True)
            reader, start, _, end, _ = graph["operators"]
            reader["customDisplayName"] = "Read scores"
            reader["operatorProperties"]["fileName"] = source.as_posix()
            start["operatorProperties"] = dict(
                initialization=INIT[rule],
                output="score = float(D.loc[D['K'] == K, 'score'].iloc[0])\nD[D['K'] == K]",
            )
            end["operatorProperties"] = dict(
                update=UPDATE[rule], condition=CONDITION[rule]
            )
            graph["operators"] = [reader, start, end]
            graph["links"] = graph["links"][:2]
            graph["links"][1]["target"]["operatorID"] = end["operatorID"]
            graph["operatorPositions"] = {
                n["operatorID"]: graph["operatorPositions"][n["operatorID"]]
                for n in graph["operators"]
            }
            path = folder / "workflow.json"
            save(path, graph)
            runs.append(
                dict(
                    id=label,
                    tool="waffle",
                    task=rule,
                    fixture=fixture,
                    workflow=path.relative_to(RUN).as_posix(),
                    expected=[scores[k - 2] for k in VISITS[rule][index]],
                )
            )
    save(RUN / "manifest.json", dict(runs=runs))


if __name__ == "__main__":
    prepare()
