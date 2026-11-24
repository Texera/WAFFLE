"""Check whether recorded loops have multiple operator paths between their boundaries."""
import argparse
import gzip
import hashlib
import json
from collections import Counter
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLANS = HERE.parents[1] / "case_study/public_catalogs/plans/knime-plans.jsonl.gz"


def reachable(start, edges):
    reached = {start}
    todo = [start]
    while todo:
        nxt = edges[todo.pop()] - reached
        todo.extend(nxt)
        reached.update(nxt)
    return reached


def classify(scope):
    starts = [n for n, role in scope["roles"].items() if role == "LoopStart"]
    ends = [n for n, role in scope["roles"].items() if role == "LoopEnd"]
    if len(starts) != 1 or len(ends) != 1:
        return "multiple-boundaries"
    start, end = starts[0], ends[0]
    parents = {n: set() for n in scope["node_ids"]}
    children = {n: set() for n in parents}
    for src, _, dst, _ in scope["edges"]:
        parents[dst].add(src)
        children[src].add(dst)
    region = reachable(start, children) & reachable(end, parents)
    if not region:
        return "disconnected"
    assert start in region and end in region and scope["connected"]
    try:
        order = tuple(TopologicalSorter({n: parents[n] & region for n in region}).static_order())
    except CycleError:
        return "cyclic-body"
    paths = {}
    for n in order:
        paths[n] = min(2, int(n == start) + sum(paths[p] for p in parents[n] & region))
    # Every edge inside the region lies on a start-to-end path. Two different
    # successors there give two paths, even if they rejoin before the loop end.
    has_split = any(len(children[n] & region) > 1 for n in region)
    assert (paths[end] == 2) == has_split
    return "several-paths" if has_split else "one-path"


def summarize(path):
    records = Counter()
    scopes = Counter()
    fingerprints = {}
    seen = set()
    with gzip.open(path, "rt", encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            assert row["source"] not in seen
            seen.add(row["source"])
            labels = [classify(scope) for scope in row["graph"]["boundary_scopes"]]
            scopes.update(labels)
            result = ("several-paths" if "several-paths" in labels else
                      "one-path" if "one-path" in labels else "no-eligible-scope")
            records[result] += 1
            old = fingerprints.setdefault(row["projection_sha256"], result)
            assert old == result
    return {"input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "workflow_items": dict(records), "scope_counts": dict(scopes),
            "distinct_projections": dict(Counter(fingerprints.values()))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plans", nargs="?", type=Path, default=PLANS)
    parser.add_argument("--check", action="store_true", help="Compare against the saved summary")
    args = parser.parse_args()
    result = summarize(args.plans)
    if args.check:
        assert result == json.loads((HERE/"loop_paths.json").read_text(encoding="utf8"))
    print(json.dumps(result, indent=2, sort_keys=True))
