"""Recheck the compact operator and coordinator evidence using only stdlib."""
import argparse
import csv
from collections import Counter
from functools import cache
import json
from pathlib import Path

from corpus import cases, digest, FIXTURES, graph
from oracle import expected, topology

HERE = Path(__file__).resolve().parent
SENTINELS = (0, 1, 2, 59, 399, 4680, 4681, 4682)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unfolded_tree(g):
    """An isomorphism invariant for a rooted DAG. Ignore every vertex label."""
    children = {op["operatorID"]: [] for op in g["operators"]}
    targets = set()
    for e in g["links"]:
        u, v = (e[t]["operatorID"] for t in ("source", "target"))
        children[u].append(v)
        targets.add(v)

    @cache
    def signature(u):
        return tuple(sorted(signature(v) for v in children[u]))

    root, = children.keys() - targets
    return signature(root)


def verify_operators(record):
    hashes, traces, shapes, trees = [], [], set(), set()
    node_sizes, edge_sizes = [], []
    profiles, iterations, policies, outcome = {}, {}, {}, Counter()
    routes = {}
    for i, (family, policy, arms) in enumerate(cases()):
        g = graph(family, policy, arms, FIXTURES["mixed"])
        require(topology(g) == arms and arms not in shapes, f"topology {i}")
        shapes.add(arms)
        trees.add(unfolded_tree(g))
        node_sizes.append(len(g["operators"]))
        edge_sizes.append(len(g["links"]))
        hashes.append(digest(g))
        profile = []
        for fixture, xs in FIXTURES.items():
            rows = expected(family, policy, arms, xs)
            profile.append(rows)
            traces.append([i, fixture, rows])
            iterations.setdefault(family, Counter())[len(rows)] += 1
            op = routes.setdefault(family, Counter())
            for k, score in rows:
                n = len(xs) if family != "aggregation" else len(xs[k::3])
                for a, b in arms:
                    op["feature_row_calls"] += n * (a + b)
                    op["union_invocations"] += 1
                    n *= 2
                op["reducer_input_rows"] += n
            if family == "stopping":
                passed = rows[-1][1] * 6 >= (policy + 2) * n
                outcome["quorum" if passed else "cap_without_quorum"] += 1
        profiles.setdefault(family, set()).add(digest(profile))
        policies.setdefault(family, Counter())[policy] += 1

    require(len(trees) == len(shapes), "unfolded trees did not distinguish every graph")
    families = {}
    for family, hist in iterations.items():
        families[family] = dict(graphs=sum(policies[family].values()), runs=sum(hist.values()),
                                visits=sum(k*v for k, v in hist.items()), policy_graphs=policies[family],
                                operations=routes[family], iterations_per_run=hist,
                                outcomes=outcome if family == "stopping" else {},
                                distinct_three_fixture_output_profiles=len(profiles[family]))
    expected_record = dict(graphs=len(shapes), nodes_range=[min(node_sizes), max(node_sizes)],
                           edges_range=[min(edge_sizes), max(edge_sizes)],
                           depth_histogram=Counter(map(len, shapes)), families=families,
                           graph_hash_list_sha256=digest(hashes), ordered_trace_sha256=digest(traces))
    require(json.loads(json.dumps(expected_record)) == record, "operator evidence differs from oracle")
    return hashes


def verify_sensitivity():
    stopping = {i: arms for i, (family, _, arms) in enumerate(cases()) if family == "stopping"}
    fractions = ("1/3", "1/2", "2/3")
    seen = set()
    with (HERE / "stopping_sensitivity.csv").open(newline="") as stream:
        for record in csv.DictReader(stream):
            i, fixture, fraction = int(record["graph"]), record["input"], record["fraction"]
            key = (i, fixture, fraction)
            require(i in stopping and fixture in FIXTURES and fraction in fractions and key not in seen,
                    f"unexpected or repeated threshold observation {key}")
            seen.add(key)
            policy = fractions.index(fraction)
            arms, values = stopping[i], FIXTURES[fixture]
            visits = expected("stopping", policy, arms, values)
            score = visits[-1][1]
            count = len(values) * 2 ** len(arms)
            observed = tuple(int(record[k]) for k in ("visits", "rows_meeting", "rows_total", "threshold_met"))
            require(observed == (len(visits), score, count, int(6 * score >= (policy + 2) * count)),
                    f"threshold result {key}")
    require(len(seen) == len(stopping) * len(FIXTURES) * len(fractions), "missing threshold observations")


def check_native(record, hashes):
    require(record["strict_compilations"] == len(hashes) and
            record["compiled_graph_hash_list_sha256"] == digest(hashes), "compiled graph coverage")
    require([r["index"] for r in record["coordinator"]] == list(SENTINELS), "coordinator coverage")
    specs = list(cases())
    for r in record["coordinator"]:
        i = r["index"]
        family, policy, arms = specs[i]
        rows = expected(family, policy, arms, FIXTURES["mixed"])
        require(r["graph_sha256"] == hashes[i] and r["rows"] == list(map(list, rows)), f"native rows {i}")


def collect(roots, hashes):
    compiled, executed = [], []
    for root in roots:
        require((root / "exit-code.txt").read_text().strip() == "0", f"engine exit in {root}")
        for name, dest in [("compiled", compiled), ("executed", executed)]:
            path = root / (name + ".jsonl")
            if path.exists():
                dest.extend(json.loads(line) for line in path.read_text().splitlines())
    compiled.sort(key=lambda r: r["index"])
    executed.sort(key=lambda r: r["index"])
    require([r["index"] for r in compiled] == list(range(len(hashes))), "missing/duplicate compilations")
    record = dict(strict_compilations=len(compiled),
                  compiled_graph_hash_list_sha256=digest([r["graph_sha256"] for r in compiled]),
                  coordinator=executed)
    check_native(record, hashes)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", nargs="+", type=Path, help="fresh native package(s) to check")
    parser.add_argument("--write", type=Path, help="new compact native result file")
    args = parser.parse_args()
    hashes = verify_operators(json.loads((HERE / "operators.json").read_text()))
    verify_sensitivity()
    if args.capture:
        record = collect(args.capture, hashes)
        if args.write:
            with args.write.open("x", encoding="utf-8") as f:
                json.dump(record, f, indent=2)
                f.write("\n")
        else:
            require(record == json.loads((HERE / "native.json").read_text()), "fresh native run differs")
    else:
        if args.write:
            parser.error("--write requires --capture")
        record = json.loads((HERE / "native.json").read_text())
        check_native(record, hashes)
    print(f"Verified {len(hashes)} compiled graphs, 3 operator fixtures each, "
          f"{len(record['coordinator'])} coordinator outputs.")


if __name__ == "__main__":
    main()
