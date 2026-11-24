"""Check port contents by iteration and the full sorted hierarchy result."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path


def check(ok, message):
    if not ok:
        raise ValueError(message)


def pairs(rows):
    return Counter(tuple(row) for row in rows)


def read_table(path, columns):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        check(
            reader.fieldnames == ["row ID", *columns],
            f"Unexpected schema in {path.name}",
        )
        return [
            [int(r[c]) if c in ("level", "Iteration") else r[c] for c in columns]
            for r in reader
        ]


def graph_paths(edges):
    # Independent oracle: enumerate rooted paths using a static adjacency list.
    adj = defaultdict(set)
    children = set()
    for parent, child in edges:
        adj[parent].add(child)
        children.add(child)
    found = set()
    for root in set(adj) - children:
        todo = [(root, (root,))]
        while todo:
            parent, path = todo.pop()
            for child in adj.get(parent, ()):
                check(child not in path, "Cycle in example input")
                found.add((root, child, len(path)))
                todo.append((child, (*path, child)))
    return [list(row) for row in sorted(found, key=lambda r: (r[0], r[2], r[1]))]


def load_reference(folder):
    for i in range(1, 4):
        status = json.loads((folder / f"{i:02}-knime-run.json").read_bytes())
        check(
            status["exit_code"] == 0 and status["exports_present"],
            f"KNIME run {i} failed",
        )
    columns = ["parent", "child"]
    edges = read_table(folder / "input.csv", columns)
    result = read_table(folder / "final.csv", [*columns, "level"])
    check(
        graph_paths(edges) == result,
        "KNIME result differs from rooted paths in published input",
    )
    grouped = {}
    for name in ("collected", "feedback-frontier", "feedback-relation"):
        groups = defaultdict(list)
        for parent, child, iteration in read_table(
            folder / (name + ".csv"), [*columns, "Iteration"]
        ):
            groups[iteration + 1].append([parent, child])
        grouped[name] = groups
    levels = sorted(grouped["collected"])
    check(levels == list(range(1, len(levels) + 1)), "Missing iteration from original")
    for groups in grouped.values():
        check(set(groups) <= set(levels), "Unexpected diagnostic iteration")
    frontier = read_table(folder / "initial-frontier.csv", columns)
    relation = read_table(folder / "initial-relation.csv", columns)
    expected = []
    for level in levels:
        expanded = grouped["feedback-frontier"][level]
        following = grouped["feedback-relation"][level]
        expected.append(
            dict(
                level=level,
                incoming=frontier,
                relation=relation,
                expanded=expanded,
                following=following,
                emitted=grouped["collected"][level],
            )
        )
        frontier, relation = expanded, following
    check(
        bool(expected) and not frontier, "Termination did not produce an empty frontier"
    )
    return result, expected


def compare(system, records, expected_rows, expected_trace):
    traces = {}
    rows = []
    for record in records:
        if set(record) == {"trace"}:
            trace = record["trace"]
            level = trace["level"]
            check(
                type(level) is int and level not in traces,
                f"{system}: duplicate or invalid iteration",
            )
            traces[level] = trace
        else:
            check(set(record) == {"row"}, f"{system}: extra fields")
            row = record["row"]
            check(len(row) == 3 and type(row[2]) is int, f"{system}: level type")
            rows.append(row)
    check(
        rows == expected_rows, f"{system}: sorted rows, levels or multiplicities differ"
    )
    check(
        sorted(traces) == [step["level"] for step in expected_trace],
        f"{system}: iterations differ",
    )
    for step in expected_trace:
        actual = traces[step["level"]]
        check(set(step) == set(actual), f"{system}: trace schema")
        for key in ("incoming", "relation", "expanded", "following", "emitted"):
            check(
                pairs(actual[key]) == pairs(step[key]),
                f"{system}: iteration {step['level']} field {key}",
            )


def verify(reference, translated):
    rows, trace = load_reference(reference)
    check(
        (translated / "exit-code.txt").read_text().strip() == "0",
        "WAFFLE native execution failed",
    )
    provenance = translated / "waffle-provenance.json"
    if provenance.exists():
        graph = translated / "hierarchy-waffle.json"
        stored = json.loads(provenance.read_bytes())
        check(
            stored["workflow_sha256"][graph.name]
            == hashlib.sha256(graph.read_bytes()).hexdigest(),
            "WAFFLE workflow hash differs from the recorded run",
        )
    runs = [
        json.loads(line)
        for line in (translated / "native.jsonl").read_bytes().splitlines()
    ]
    check(
        len(runs) == 1 and runs[0]["case"] == "hierarchy",
        "WAFFLE case missing or repeated",
    )
    compare("WAFFLE", [json.loads(r["payload"]) for r in runs[0]["rows"]], rows, trace)
    for system, graph in [
        ("n8n", "hierarchy-n8n.json"),
        ("rapidminer", "hierarchy.rmp"),
    ]:
        record = json.loads((translated / f"hierarchy-{system}-run.json").read_bytes())
        check(record["iterations"] == len(trace), f"{system}: body execution count")
        check(
            hashlib.sha256((translated / graph).read_bytes()).hexdigest()
            == record["workflow_sha256"],
            f"{system}: workflow hash",
        )
        compare(system, record["rows"], rows, trace)
    return dict(
        rows=len(rows),
        rounds=len(trace),
        frontier=[len(trace[0]["incoming"]), *(len(s["expanded"]) for s in trace)],
        relation=[len(trace[0]["relation"]), *(len(s["following"]) for s in trace)],
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ("reference", "translated"):
        p.add_argument(
            arg, nargs="?", type=Path, default=Path(__file__).with_name("results")
        )
    a = p.parse_args()
    print(json.dumps(verify(a.reference, a.translated)))
