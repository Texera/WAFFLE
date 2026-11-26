"""Prepare controlled BFS sessions, serialize accepted graphs, and score native outputs."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path

import task
from native import knime, run_knime, waffle
from protocol import SEEDS, dump
from trials import run_session


def freeze(folder, clarified=False, state_and_branch=False):
    folder.mkdir(parents=True, exist_ok=False)
    for system, control in task.controls().items():
        (folder / f"{system}-prompt.txt").write_text(
            task.prompt(system, clarified, state_and_branch), encoding="utf8"
        )
        for root in task.VERTICES:
            assert task.public_preview(
                control, system, task.fixture(root)
            ) == task.expected(root)
    dump(folder / "fixtures.json", task.metadata())
    dump(folder / "controls.json", task.controls())


def sessions(folder, endpoint, model, key):
    dest = folder / "sessions"
    dest.mkdir(exist_ok=True)
    token = key.read_text().strip() if key else os.environ["INFERENCE_TOKEN"]

    def run(spec):
        system, seed = spec
        instructions = (folder / f"{system}-prompt.txt").read_text(encoding="utf8")
        run_session(
            (system, task.TASK, seed),
            dest,
            endpoint,
            model,
            token,
            instructions,
            task.fixture(task.PUBLIC_ROOT),
            task.expected(task.PUBLIC_ROOT),
            task.public_preview,
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(
            pool.map(run, [(sy, seed) for seed in SEEDS for sy in ("waffle", "knime")])
        )


def prepare(folder, stage):
    dest = (folder / stage).resolve()
    dest.mkdir(exist_ok=False)
    plans = []
    if stage == "controls":
        plans = [(system, "control", plan) for system, plan in task.controls().items()]
    else:
        files = sorted((folder / "sessions").glob("*.json"))
        assert len(files) == 4
        for f in files:
            rec = json.loads(f.read_text())
            item = rec["attempts"][-1]
            if item["public_pass"]:
                plans.append((rec["system"], rec["seed"], item["plan"]))
    mapping = []
    manifest = []
    prepared = set()
    for system, seed, plan in plans:
        assert task.public_preview(
            plan, system, task.fixture(task.PUBLIC_ROOT)
        ) == task.expected(task.PUBLIC_ROOT)
        for root in (task.PUBLIC_ROOT, *task.HELD_OUT):
            key = (
                system
                + "-"
                + hashlib.sha256(json.dumps([plan, root]).encode()).hexdigest()[:16]
            )
            mapping.append(dict(case=key, system=system, seed=seed, root=root))
            if key in prepared:
                continue
            prepared.add(key)
            if system == "waffle":
                dump(
                    dest / (key + ".json"),
                    waffle(plan, task.fixture(root), task.render, "long"),
                )
                manifest.append(
                    dict(
                        case=key,
                        strategy="karate",
                        pair=0,
                        warmup=False,
                        workflow=key + ".json",
                        fields=["x", "y"],
                    )
                )
            else:
                knime(plan, task.fixture(root), dest / key, task.render)
    dump(dest / "manifest.json", dict(runs=manifest))
    dump(dest / "mapping.json", mapping)
    print(
        stage,
        len(manifest),
        "WAFFLE graphs,",
        len(prepared) - len(manifest),
        "KNIME graphs",
    )


def score(folder, stage):
    dest = folder / stage
    mapping = json.loads((dest / "mapping.json").read_text())
    native = dest / "native.jsonl"
    waffle_rows = {}
    if native.exists():
        for line in native.read_text().splitlines():
            r = json.loads(line)
            assert r["case"] not in waffle_rows
            waffle_rows[r["case"]] = [[v["x"], v["y"]] for v in r["rows"]]
    result = []
    for m in mapping:
        key = m["case"]
        if m["system"] == "waffle":
            actual = waffle_rows[key]
        else:
            record = json.loads((dest / key / "result.json").read_text())
            if record["exit"] != 0:
                raise ValueError(f"{key}: native execution exit {record['exit']}")
            actual = record["rows"]
        expected = task.expected(m["root"])
        result.append(dict(**m, rows=actual, match=actual == expected))
    if stage == "controls":
        assert len(result) == 6 and all(r["match"] for r in result), result
    dump(folder / (stage + "-outputs.json"), result)
    print(
        stage,
        len(result),
        "native outputs;",
        sum(r["match"] for r in result),
        "exact matches",
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "command", choices=("freeze", "sessions", "prepare", "knime", "score")
    )
    p.add_argument("folder", type=Path)
    p.add_argument("--stage", choices=("controls", "agent"), default="agent")
    p.add_argument("--key-file", type=Path)
    p.add_argument("--endpoint")
    p.add_argument("--model", default="flash-next")
    p.add_argument(
        "--state-and-branch",
        action="store_true",
        help="include the format reminder and explain output, stored state and input wiring",
    )
    p.add_argument(
        "--clarified",
        action="store_true",
        help="add the shared format reminder when freezing prompts",
    )
    p.add_argument("--runtime", type=Path)
    a = p.parse_args()
    if a.command == "freeze":
        freeze(a.folder, a.clarified, a.state_and_branch)
    elif a.command == "sessions":
        sessions(a.folder, a.endpoint, a.model, a.key_file)
    elif a.command == "prepare":
        prepare(a.folder, a.stage)
    elif a.command == "knime":
        run_knime(a.folder / a.stage, a.runtime)
    else:
        score(a.folder, a.stage)
