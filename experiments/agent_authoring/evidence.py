"""Package observed rows and re-score every published trial without either engine."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
from controls import controls
from graphs import preview
from protocol import HIDDEN, PUBLIC, SEEDS, TASKS, TRIES, oracle
from worked_example import condition_prompt

CONDITIONS = (
    "documentation",
    "worked_example",
    "wiring_only",
    "wiring_timing",
    "wiring_rules",
    "end_ports",
    "assignment_format",
    "row_numbering",
    "expression_strings",
    "feedback_filter",
)


def key_for(system, plan, data):
    digest = hashlib.sha256(json.dumps([plan, data]).encode()).hexdigest()[:16]
    return system + "-" + digest


def lines(path):
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf8").splitlines()
        if line.strip()
    ]


def write_lines(path, records):
    with path.open("w", encoding="utf8", newline="\n") as f:
        for r in records:
            f.write(json.dumps(r, separators=(",", ":"), ensure_ascii=False) + "\n")


def collect(root, out):
    out.mkdir(exist_ok=True, parents=True)
    sessions = []
    checks = {}
    engine_dirs = [
        root / name for name in ("native", "native-worked", "controls/engines")
    ]
    extensions = [
        root / name
        for name in ("native-feedback", "native-expressions", "native-numbering", "native-assignments", "native-ports", "native-rules", "native-timing", "native-wiring")
    ]
    # Retain the archived execution ID if an identical graph was run previously.
    paths = [p for folder in extensions for p in sorted(folder.rglob("native.jsonl"))]
    paths.extend(
        sorted(p for folder in engine_dirs for p in folder.rglob("native.jsonl"))
    )
    for path in paths:
        for row in lines(path):
            if row.get("strategy") != "authored":
                continue
            observed = [[r["x"], r["y"]] for r in row["rows"]]
            if row["case"] in checks and checks[row["case"]]["rows"] != observed:
                raise ValueError(f"Repeated executions disagree for {row['case']}")
            checks[row["case"]] = dict(
                case=row["case"],
                engine="WAFFLE",
                execution_id=row["execution_id"],
                rows=observed,
            )
    for folder in [*extensions, *engine_dirs]:
        for path in folder.glob("knime-*/result.json"):
            row = json.loads(path.read_text())
            if row["exit"] != 0:
                raise ValueError(
                    f"Engine infrastructure or graph failure, inspect {path}"
                )
            if row["case"] in checks and checks[row["case"]]["rows"] != row["rows"]:
                raise ValueError(f"Repeated executions disagree for {row['case']}")
            checks[row["case"]] = dict(
                case=row["case"],
                engine="KNIME 5.5.3",
                exit=row["exit"],
                rows=row["rows"],
            )
    for sub, condition in zip(
        ("trials", "worked", "wiring", "timing", "rules", "ports", "assignments", "numbering", "expressions", "feedback"),
        CONDITIONS,
        strict=True,
    ):
        for path in sorted((root / sub).glob("*.json")):
            row = json.loads(path.read_text(encoding="utf8"))
            sessions.append(dict(condition=condition, **row))
    write_lines(out / "sessions.jsonl", sessions)
    write_lines(out / "native.jsonl", sorted(checks.values(), key=lambda r: r["case"]))


def score(path):
    native = {r["case"]: r["rows"] for r in lines(path / "native.jsonl")}
    sessions = lines(path / "sessions.jsonl")
    observations = []
    used = set()
    seen = set()
    for session in sessions:
        c, s, t, seed = [session[k] for k in ("condition", "system", "task", "seed")]
        identity = c, s, t, seed
        assert identity not in seen
        seen.add(identity)
        text = condition_prompt(s, t, c)
        assert hashlib.sha256(text.encode()).hexdigest() == session["prompt_hash"]
        attempts = session["attempts"]
        assert 1 <= len(attempts) <= TRIES and not any(
            a["public_pass"] for a in attempts[:-1]
        )
        final = attempts[-1]
        passed = False
        if final["public_pass"]:
            assert preview(final["plan"], s, PUBLIC) == oracle(t, PUBLIC)
            checks = []
            for data in HIDDEN[t]:
                key = key_for(s, final["plan"], data)
                used.add(key)
                checks.append(native[key] == oracle(t, data))
            passed = all(checks)
        else:
            assert len(attempts) == TRIES
        observations.append(
            dict(
                condition=c,
                system=s,
                task=t,
                seed=seed,
                submissions=len(attempts),
                public_pass=final["public_pass"],
                first_success=passed and len(attempts) == 1,
                success=passed,
            )
        )
    for t in TASKS:
        for s, plan in controls(t).items():
            for data in HIDDEN[t]:
                key = key_for(s, plan, data)
                used.add(key)
                assert native[key] == oracle(t, data), (
                    t,
                    s,
                    data,
                    native[key],
                    oracle(t, data),
                )
    expected = {
        (c, s, t, seed)
        for c in CONDITIONS
        for s in ("knime", "waffle")
        for t in TASKS
        for seed in SEEDS
    }
    assert seen == expected
    assert used == set(native), (
        "missing or extra native records",
        used.symmetric_difference(native),
    )
    return observations


def totals(observations):
    groups = defaultdict(Counter)
    for row in observations:
        group = groups[row["condition"], row["system"]]
        group.update(
            sessions=1,
            first=row["first_success"],
            within_budget=row["success"],
            public=row["public_pass"],
            submissions=row["submissions"],
        )
    return groups


def submitted_nodes(response):
    """Read the submitted node array, including graphs that failed validation."""
    raw = response.strip()
    if raw.startswith("```") and raw.endswith("```"):
        raw = raw.partition("\n")[2][:-3].strip()
    try:
        nodes = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return nodes if isinstance(nodes, list) else []


def has_expression_strings(response):
    """Check the two output argument types and the continuation argument type."""
    nodes = submitted_nodes(response)
    emit = [n for n in nodes if isinstance(n, list) and n[:1] == ["emit"]]
    end = [n for n in nodes if isinstance(n, list) and n[:1] == ["end"]]
    if len(emit) != 1 or len(end) != 1 or len(emit[0]) != 4 or len(end[0]) != 4:
        return False
    return all(isinstance(value, str) for value in (*emit[0][2:], end[0][3]))


def has_direct_sink(response):
    """Check the sink edge independently of other graph validation errors."""
    nodes = submitted_nodes(response)
    sinks = [
        i
        for i, node in enumerate(nodes)
        if isinstance(node, list) and node[:1] == ["sink"]
    ]
    if len(sinks) != 1:
        return False
    i = sinks[0]
    if len(nodes[i]) != 2:
        return False
    source = nodes[i][1]
    return (
        type(source) is int
        and 0 <= source < i
        and isinstance(nodes[source], list)
        and nodes[source][:1] == ["end"]
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path)
    parser.add_argument(
        "--collect",
        type=Path,
        help="local root containing the prompt and native run directories and feasibility controls",
    )
    args = parser.parse_args()
    if args.collect:
        collect(args.collect, args.results)
    observations = score(args.results)
    if args.collect:
        with (args.results / "outcomes.csv").open(
            "w", encoding="utf8", newline=""
        ) as f:
            writer = csv.DictWriter(f, list(observations[0]))
            writer.writeheader()
            writer.writerows(observations)
    for group, count in totals(observations).items():
        print(*group, dict(count))
    sessions = lines(args.results / "sessions.jsonl")
    for condition in ("wiring_rules", "end_ports"):
        connections = [
            has_direct_sink(a["text"])
            for session in sessions
            if session["system"] == "knime" and session["condition"] == condition
            for a in session["attempts"]
        ]
        print(
            f"{condition} KNIME direct sink: {sum(connections)}/{len(connections)} submissions"
        )
    for condition in ("row_numbering", "expression_strings"):
        formats = [
            has_expression_strings(a["text"])
            for session in sessions
            if session["system"] == "waffle" and session["condition"] == condition
            for a in session["attempts"]
        ]
        print(f"{condition} WAFFLE expression strings: {sum(formats)}/{len(formats)} submissions")
