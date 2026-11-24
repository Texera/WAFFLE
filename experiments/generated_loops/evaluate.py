"""Evaluate generated JSON using the pinned Python loop operators in one process."""
import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import json
from pathlib import Path
import sys

from corpus import cases, digest, FIXTURES, graph
from oracle import expected, topology
from provenance import pinned_runtime


@lru_cache(None)
def operator_type(code):
    # Only called for code constructed by corpus.py.
    namespace = {}
    exec(code, namespace)
    return next(namespace[name] for name in ("Fixture", "Feature", "Body") if name in namespace)


def execute(g):
    from pytexera import LoopStartOperator, LoopEndOperator, State, Table

    nodes = g["operators"]
    incoming = defaultdict(list)
    for e in g["links"]:
        incoming[e["target"]["operatorID"]].append(e["source"]["operatorID"])
    props = [node["operatorProperties"] for node in nodes]
    ids = [node["operatorID"] for node in nodes]
    src = operator_type(props[0]["code"])()
    src.open()
    source = list(src.produce())
    original = Table(source)
    visits, emitted, multiplicities = [], [], []
    counts = Counter()
    checkpoint = None

    class Start(LoopStartOperator):
        def process_table(self, table, port):
            yield self.eval_output(table)

    class End(LoopEndOperator):
        def condition(self):
            return self.eval_condition(props[-2]["condition"])

    for iteration in range(16):  # Fail closed on nontermination.
        start = Start()
        start.run_initialization(props[1]["initialization"])
        start.run_output(props[1]["output"])
        if checkpoint is not None:
            start.process_state(checkpoint, 0)
        for row in source:
            list(start.process_tuple(row, 0))
        state = start.produce_state_on_finish(0)
        data = {ids[1]: next(start.on_finish(0)).to_dict("records")}
        body_state = None
        for i in range(2, len(nodes) - 2):
            rows = [row for parent in incoming[ids[i]] for row in data[parent]]
            if nodes[i]["operatorType"] == "Union":
                counts["union_invocations"] += 1
                data[ids[i]] = rows
                continue
            op = operator_type(props[i]["code"])()
            op.open()
            op.state = State(state)
            op.process_state(op.state, 0)
            emitted_rows = [out for row in rows for out in op.process_tuple(row, 0) if out is not None]
            forwarded = op.produce_state_on_finish(0)
            if forwarded is not None:
                body_state = forwarded
                counts["reducer_input_rows"] += len(rows)
            else:
                counts["feature_row_calls"] += len(rows)
            emitted_rows.extend(out for out in op.on_finish(0) if out is not None)
            data[ids[i]] = emitted_rows
        end = End()
        end.attach_loop_table(original)
        end.run_update(props[-2]["update"], State.from_tuple(body_state.to_tuple()))
        for row in data[incoming[ids[-2]][0]]:
            list(end.process_tuple(row, 0))
        batch = next(end.on_finish(0)).to_dict("records")
        emitted.extend(batch)
        visits.append((state["k"], body_state["score"]))
        multiplicities.append(body_state["count"])
        if not end.condition():
            order, = props[-1]["attributes"]
            rows = sorted(emitted, key=lambda r: r[order["attribute"]],
                          reverse=order["sortPreference"] == "DESC")
            return visits, [(r["step"], r["score"]) for r in rows], multiplicities, counts, body_state
        checkpoint = State.from_tuple(end.variables.to_tuple())
    raise RuntimeError("iteration limit exceeded")


def checked(g, family, policy, arms, values):
    if topology(g) != arms:
        raise ValueError("graph differs from the requested topology")
    reference = expected(family, policy, arms, values)
    visits, rows, multiplicities, counts, last = execute(g)
    expected_sizes = [2**len(arms) * (len(values[k::3]) if family == "aggregation" else len(values))
                      for k, _ in reference]
    if multiplicities != expected_sizes:
        raise ValueError(f"{family} {arms}: body input counts {multiplicities} != {expected_sizes}")
    if visits != reference or rows != reference:
        raise ValueError(f"{family} {policy} {arms}: expected {reference}, visits {visits}, rows {rows}")
    return rows, counts, last


def measure():
    shapes, hashes, traces, by_family = set(), [], [], {}
    sizes, edges = [], []
    for i, (family, policy, arms) in enumerate(cases()):
        group = by_family.setdefault(family, dict(graphs=0, runs=0, visits=0, policy_graphs=Counter(),
                                                  iterations_per_run=Counter(), operations=Counter(),
                                                  outcomes=Counter(), signatures=set()))
        reference_graph = graph(family, policy, arms, FIXTURES["mixed"])
        shape = topology(reference_graph)
        if shape in shapes:
            raise ValueError("unlabeled graph repeated")
        shapes.add(shape)
        hashes.append(digest(reference_graph))
        sizes.append(len(reference_graph["operators"]))
        edges.append(len(reference_graph["links"]))
        group["graphs"] += 1
        group["policy_graphs"][policy] += 1
        profile = []
        for fixture, values in FIXTURES.items():
            g = graph(family, policy, arms, values)
            rows, ops, last = checked(g, family, policy, arms, values)
            group["operations"].update(ops)
            group["iterations_per_run"][len(rows)] += 1
            group["visits"] += len(rows)
            group["runs"] += 1
            if family == "stopping":
                met = 6 * last["score"] >= (2 + policy) * last["count"]
                group["outcomes"]["quorum" if met else "cap_without_quorum"] += 1
            traces.append([i, fixture, rows])
            profile.append(rows)
        group["signatures"].add(digest(profile))
    for group in by_family.values():
        group["distinct_three_fixture_output_profiles"] = len(group.pop("signatures"))
    return dict(graphs=len(shapes), nodes_range=[min(sizes), max(sizes)], edges_range=[min(edges), max(edges)],
                depth_histogram=dict(Counter(map(len, shapes))), families=by_family,
                graph_hash_list_sha256=digest(hashes), ordered_trace_sha256=digest(traces))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--write", type=Path, help="write new result file (default: check recorded result)")
    args = parser.parse_args()
    repo = args.repo.resolve()
    pinned_runtime(repo)
    sys.path.insert(0, str(repo / "amber/src/main/python"))
    result = measure()
    if args.write:
        with args.write.open("x", encoding="utf-8") as f:
            json.dump(result, f, indent=2, sort_keys=True)
            f.write("\n")
    elif json.loads(json.dumps(result)) != json.loads(Path(__file__).with_name("operators.json").read_text()):
        raise SystemExit("operator result differs from recorded evidence")
    print(result["graphs"], "graphs,", sum(v["runs"] for v in result["families"].values()),
          "graph-input runs verified;", result["ordered_trace_sha256"])


if __name__ == "__main__":
    main()
