"""Prepare two fixed graphs with different data and interchangeable policy modules."""

import argparse
import csv
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from prepare import model, save, waffle  # noqa: E402

# Specified before execution, in order. Fixtures use the original study points.
VISITS = {
    ("choose", "v1", "far"): [2, 4, 3],
    ("choose", "v2", "far"): [2, 3, 4],
    ("choose", "v1", "near"): [2, 3],
    ("choose", "v2", "near"): [2, 3],
    ("stop", "v1", "far"): [2, 3],
    ("stop", "v2", "far"): [2, 3, 4],
    ("stop", "v1", "near"): [2, 3],
    ("stop", "v2", "near"): [2, 3, 4],
}


def prepare(root):
    root.mkdir(parents=True, exist_ok=False)
    (root / "facilitator").mkdir()
    runs = []
    for (rule, version, fixture), visits in VISITS.items():
        label = "-".join((rule, version, fixture))
        folder = root / label
        folder.mkdir()
        policy = folder / "policy.py"
        shutil.copyfile(HERE / f"policy_{version}.py", policy)
        scores = model.scores(
            HERE.parent / "results" / "inputs" / fixture / "points.csv"
        )
        source = folder / "scores.csv"
        with source.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["K", "score", "policy_path"])
            w.writeheader()
            w.writerows([{**row, "policy_path": policy.as_posix()} for row in scores])
        g = waffle.graph(folder, folder, "sweep", -100, short=True)
        reader, start, _, end, _ = g["operators"]
        reader["operatorProperties"]["fileName"] = source.as_posix()
        start["operatorProperties"] = dict(
            initialization="K = 2\n"
            + ("trials = 0" if rule == "choose" else "previous = 0.0"),
            output="policy_path = str(D['policy_path'].iloc[0])\nscore = float(D.loc[D['K'] == K,'score'].iloc[0])\nD[D['K'] == K]",
        )
        if rule == "choose":
            end["operatorProperties"] = dict(
                update="from runpy import run_path\ntrials += 1\nK = run_path(policy_path)['next_candidate'](K, score, trials)\ndel run_path",
                condition="K != 0",
            )
        else:
            end["operatorProperties"] = dict(
                update="tested = K\nprior = previous\nprevious = score\nK += 1",
                condition="__import__('runpy').run_path(policy_path)['keep_searching'](tested, score, prior)",
            )
        g["operators"] = [reader, start, end]
        g["links"] = g["links"][:2]
        g["links"][1]["target"]["operatorID"] = end["operatorID"]
        g["operatorPositions"] = {
            op["operatorID"]: g["operatorPositions"][op["operatorID"]]
            for op in g["operators"]
        }
        path = folder / "workflow.json"
        save(path, g)
        runs.append(
            dict(
                id=label,
                tool="waffle",
                task=rule,
                fixture=fixture,
                version=version,
                workflow=f"{label}/workflow.json",
                expected=[scores[k - 2] for k in visits],
            )
        )
    save(root / "manifest.json", dict(runs=runs))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    prepare(parser.parse_args().run.resolve())
