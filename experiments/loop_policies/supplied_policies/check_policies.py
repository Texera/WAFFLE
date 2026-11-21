"""Check both kinds of evidence: result sequences and calls into the supplied file."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from prepare_cases import HERE, VISITS, model

sys.path.insert(0, str(HERE.parent / "native_controls"))
from verify import ALLOWED, actual, node_types

ENGINES = ("waffle", "knime", "n8n", "rapidminer")


def checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(root):
    records = []
    primitives = {}
    for case in VISITS:
        rule, version, fixture = case
        name = "-".join(case)
        folder = root / name
        library = folder / "policy.py"
        if checksum(library) != checksum(HERE / f"policy_{version}.py"):
            raise ValueError(f"{name}: supplied library changed")
        g = json.loads((folder / "workflow.json").read_text())
        signature = [
            (op["operatorType"], op["operatorProperties"]) for op in g["operators"][1:]
        ]
        if primitives.setdefault(rule, signature) != signature:
            raise ValueError(f"{name}: loop fields changed with the input or policy")
        for engine in ENGINES:
            run = (
                folder if engine == "waffle" else root / "translations" / engine / name
            )
            output = actual(engine, run)
            calls = (
                [
                    json.loads(line)
                    for line in library.with_suffix(".calls").read_text().splitlines()
                ]
                if engine == "waffle"
                else []
            )
            records.append(
                dict(
                    system=engine,
                    workflow=rule,
                    policy=version,
                    input=fixture,
                    mode="supplied Python"
                    if engine == "waffle"
                    else "native translation",
                    node_types=json.dumps(node_types(engine, run)),
                    rows=json.dumps(output),
                    calls=json.dumps(calls),
                )
            )
    return records


def verify(records):
    pending = {(engine, *case) for engine in ENGINES for case in VISITS}
    for rec in records:
        engine = rec["system"]
        case = tuple(rec[k] for k in ("workflow", "policy", "input"))
        rule, version, fixture = case
        pending.remove((engine, *case))
        scores = model.scores(
            HERE.parent / "results" / "inputs" / fixture / "points.csv"
        )
        rows = [scores[k - 2] for k in VISITS[case]]
        assert model.compare(rows, json.loads(rec["rows"])), rec
        nodes = json.loads(rec["node_types"])
        assert nodes and set(nodes) <= ALLOWED[engine]
        calls = json.loads(rec["calls"])
        if engine == "waffle":
            assert (
                nodes == ["CSVFileScan", "LoopStart", "LoopEnd"]
                and rec["mode"] == "supplied Python"
            )
            assert len(calls) == len(rows)
            for idx, (call, row) in enumerate(zip(calls, rows)):
                func, k, score, state = call
                assert func == (
                    "next_candidate" if rule == "choose" else "keep_searching"
                )
                assert model.compare([row], [dict(K=k, score=score)])
                expected_state = (
                    idx + 1
                    if rule == "choose"
                    else (rows[idx - 1]["score"] if idx else 0)
                )
                assert model.compare([{"state": expected_state}], [{"state": state}])
        else:
            assert not calls and rec["mode"] == "native translation"
    assert not pending, pending


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--extract", type=Path, metavar="RUN")
    src = args.parse_args().extract
    csv_path = HERE / "observations.csv"
    if src:
        rows = extract(src.resolve())
        verify(rows)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    with csv_path.open(newline="", encoding="utf-8") as f:
        verify(list(csv.DictReader(f)))
    print(
        "Verified 8 executions of supplied policies in WAFFLE and 24 translations across KNIME, n8n and RapidMiner."
    )
