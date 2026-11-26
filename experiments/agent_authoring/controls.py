"""Investigator-written positive controls, kept outside all authoring prompts."""

import argparse
from pathlib import Path
from graphs import preview
from protocol import TASKS, HIDDEN, PUBLIC, oracle, dump
from native import prepare


def controls(task):
    # Body expressions emit the observed pair. Feedback updates run after emission.
    step = [["i", "i+1"]]
    emit = ["x", "y"]
    test = "i < n"
    if task == "advance":
        step += [["x", "x+2"]]
    elif task == "running_sum":
        emit = ["x+1", "y+x+1"]
        step += [["x", "x+1"], ["y", "y+x"]]
    elif task == "crossing":
        test = "i < n and u < goal"
        step += [["u", "x"], ["x", "x+y"]]
    elif task == "recurrence":
        step += [["u", "x"], ["x", "y"], ["y", "u+y"]]
    elif task == "zigzag":
        step += [["x", "x+y if flag == 0 else x-y"], ["y", "y+1"], ["flag", "1-flag"]]
    elif task == "cooldown":
        emit = ["x", "y+x"]
        step += [["y", "y+x"], ["x", "x+2 if y < 0 else x+1"]]
        test = "i < n and y < goal"
    w = [
        ["input"],
        ["start", 0, []],
        ["emit", 1, *emit],
        ["end", 2, step, test],
        ["sink", 3],
    ]
    k = [["input"], ["start", 0]]
    collect = 1
    if task == "running_sum":
        k.extend([["set", 1, "x", "x+1"], ["set", 2, "y", "y+x"]])
        collect = 3
    elif task == "cooldown":
        k.append(["set", 1, "y", "y+x"])
        collect = 2
    feed = 1
    for col, expr in step:
        k.append(["set", feed, col, expr])
        feed = len(k) - 1
    # Make a new predicate only after updating the state for the next iteration.
    k.extend(
        [
            ["set", feed, "flag", "1 if (" + test + ") else 0"],
            ["keep", feed + 1, "flag"],
        ]
    )
    if task == "zigzag":
        # Preserve the parity scratch column on the back edge.
        k[-2][2] = "v"
        k[-1][2] = "v"
    k += [["end", collect, len(k) - 1], ["sink", len(k)]]
    return {"waffle": w, "knime": k}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    reviews = args.out / "reference"
    reviews.mkdir(parents=True, exist_ok=False)
    for task in TASKS:
        for system, plan in controls(task).items():
            for data in [PUBLIC, *HIDDEN[task]]:
                assert preview(plan, system, data) == oracle(task, data), (
                    task,
                    system,
                    data,
                )
            dump(
                reviews / (task + "-" + system + ".json"),
                dict(
                    task=task,
                    system=system,
                    seed=0,
                    attempts=[dict(public_pass=True, plan=plan)],
                ),
            )
    prepare(reviews, args.out / "engines", control=True)
