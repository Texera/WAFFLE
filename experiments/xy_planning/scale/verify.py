"""Verify measured X/Y plans and prove optimality from a mandatory-edge path bound."""

import argparse
import csv
from collections import defaultdict
from graphlib import TopologicalSorter
import json
from pathlib import Path
from statistics import median
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "runner"))
from oracle import cost_of  # noqa: E402

LAYOUTS = [(4, 0), (5, 0), (4, 4), (4, 8)]


def rows(folder, name):
    with (folder / f"{name}.csv").open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def lower_bound(weights, edges):
    # Along one directed path each mandatory cut forces a different region.
    # Every region of the original graph costs one, including singleton regions.
    assert set(weights.values()) == {1.0}
    incoming = {node: [] for node in weights}
    for a, b, required in edges:
        incoming[b].append((a, int(required)))
    order = TopologicalSorter({b: [a for a, _ in pred] for b, pred in incoming.items()})
    depth = {}
    for b in order.static_order():
        depth[b] = max((depth[a] + w for a, w in incoming[b]), default=1)
    return max(depth.values())


FILTER_GAPS = [(4, f) for f in (1, 2, 3, 5, 6, 7)]


def verify(root, layouts=LAYOUTS):
    meta = json.loads((root / "metadata.json").read_text())
    assert (
        meta["forks"],
        meta["warmup_pairs"],
        meta["measured_pairs"],
        meta["pruning"],
    ) == (3, 3, 7, True)
    assert meta["revision"] == "ddc04792511838d06f982ced01641e7d06ce6524"
    observations = defaultdict(list)
    for fork in range(3):
        directory = root / f"fork-{fork}"
        op_rows, edge_rows, comp, times = [
            rows(directory, key)
            for key in ("operators", "edges", "compilation", "results")
        ]
        assert len(times) == len(layouts) * 2 * 7 and len(comp) == len(layouts)
        for groups, filters in layouts:
            name = f"groups-{groups}-filters-{filters}"
            ops = [r for r in op_rows if r["case"] == name]
            links = [r for r in edge_rows if r["case"] == name]
            weights = {r["operator"]: float(r["estimate"]) for r in ops}
            inside = {r["operator"] for r in ops if r["inside"] == "true"}
            size = 4 + 2 * groups * (4 + filters)
            assert len(ops) == len(weights) == size and len(inside) == size // 2
            assert sum("-exclude-" in node for node in weights) == 2 * groups * filters
            assert len(links) == 3 + 2 * groups * (5 + filters)
            [compiled] = [r for r in comp if r["case"] == name]
            assert (int(compiled["operators"]), int(compiled["links"])) == (
                size,
                len(links),
            )
            edges = [(r["from"], r["to"], r["required"] == "true") for r in links]
            mandatory = {i for i, e in enumerate(edges) if e[2]}
            boundary = {
                i for i, (a, b, _) in enumerate(edges) if (a in inside) != (b in inside)
            }
            compiler_cuts = {
                i for i, r in enumerate(links) if r["compiler_required"] == "true"
            }
            assert len(boundary) == 2 and len(compiler_cuts) == 4 * groups
            assert mandatory == compiler_cuts | boundary
            best = lower_bound(weights, edges)
            for method in ("X", "Y"):
                runs = [
                    r for r in times if (r["case"], r["strategy"]) == (name, method)
                ]
                assert sorted(int(r["repetition"]) for r in runs) == list(range(7))
                for r in runs:
                    rep = int(r["repetition"])
                    assert int(r["fork"]) == fork and r["order"] == (
                        "XY" if (fork + rep) % 2 == 0 else "YX"
                    )
                    cuts = {int(i) for i in r["cuts"].split(";") if i}
                    assert mandatory <= cuts
                    assert (
                        cost_of(weights, weights, edges, cuts)
                        == float(r["cost"])
                        == best
                        == int(r["regions"])
                    )
                    assert int(r["total_ns"]) == sum(
                        int(r[k])
                        for k in ("search_ns", "composition_ns", "decomposition_ns")
                    )
                    assert int(r["total_ns"]) > 0 and int(r["search_states"]) > 0
                observations[name, method].extend(runs)
    summary = []
    for groups, filters in layouts:
        name = f"groups-{groups}-filters-{filters}"
        size = 4 + 2 * groups * (4 + filters)
        entry = dict(
            case=name,
            inside=groups,
            outside=groups,
            filters_per_group=filters,
            operators=size,
            minimum_estimated_cost=float(observations[name, "X"][0]["cost"]),
        )
        for method in ("X", "Y"):
            sample = observations[name, method]
            states = {int(r["search_states"]) for r in sample}
            assert len(sample) == 21 and len(states) == 1
            ms = [int(r["total_ns"]) / 1e6 for r in sample]
            fork_medians = [median(ms[i * 7 : (i + 1) * 7]) for i in range(3)]
            entry[method] = dict(
                search_states=states.pop(),
                pooled_median_ms=median(ms),
                jvm_medians_ms=fork_medians,
                jvm_median_min_ms=min(fork_medians),
                jvm_median_max_ms=max(fork_medians),
            )
        summary.append(entry)
    return summary


def verify_dense(root, groups=12, metadata_dir=None):
    metadata = json.loads(((metadata_dir or root) / "metadata.json").read_text())
    assert metadata["revision"] == "ddc04792511838d06f982ced01641e7d06ce6524"
    assert metadata["limit_s"] == 120 and metadata["warmup_per_method"] == 3
    assert metadata["fresh_jvms_per_method"] == metadata["trials_per_method"] == 1
    size = 4 + 8 * groups
    entry = dict(operators=size, inside=groups, outside=groups)
    manifest = None
    for method in ("X", "Y"):
        folder = root / method
        operators = rows(folder, "operators")
        weights = {r["operator"]: float(r["estimate"]) for r in operators}
        inside = {r["operator"] for r in operators if r["inside"] == "true"}
        assert len(operators) == len(weights) == size and len(inside) == size // 2
        edges = [
            (r["from"], r["to"], r["required"] == "true") for r in rows(folder, "edges")
        ]
        assert len(edges) == 3 + 10 * groups and len(set(edges)) == len(edges)
        required = {i for i, e in enumerate(edges) if e[2]}
        boundary = {
            i for i, (a, b, _) in enumerate(edges) if (a in inside) != (b in inside)
        }
        assert (
            len(boundary) == 2
            and boundary <= required
            and len(required) == 4 * groups + 2
        )
        graph = (weights, inside, set(edges))
        if manifest is not None:
            assert manifest == graph
        manifest = graph
        minimum = lower_bound(weights, edges)
        assert minimum == 4 * groups + 3
        [r] = rows(folder, "outcome")
        assert r["method"] == method and int(r["limit_s"]) == 120
        observation = dict(status=r["status"], limit_s=int(r["limit_s"]))
        if r["status"] == "completed":
            cuts = {int(i) for i in r["cuts"].split(";") if i}
            assert required <= cuts
            assert float(r["cost"]) == cost_of(weights, weights, edges, cuts) == minimum
            assert 0 < int(r["total_ns"]) <= int(r["wall_ns"])
            assert int(r["states"]) > 0
            observation.update(
                search_states=int(r["states"]),
                total_ms=int(r["total_ns"]) / 1e6,
                cost=minimum,
            )
        else:
            assert r["status"] == "timeout" and int(r["wall_ns"]) >= 120_000_000_000
            assert all(r[k] == "" for k in ("total_ns", "states", "cost", "cuts"))
        entry[method] = observation
    return entry


def verify_intermediate(branches, filters, endpoint):
    return {
        "branch": [
            verify_dense(branches / f"groups-{g}", g, branches) for g in range(6, 12)
        ]
        + [verify_dense(endpoint)],
        "filter": verify(filters, FILTER_GAPS),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", nargs="?", type=Path, default=HERE / "raw")
    parser.add_argument("--write", type=Path)
    parser.add_argument("--dense", type=Path, default=HERE / "dense")
    parser.add_argument(
        "--branches", type=Path, default=HERE / "intermediate" / "branch"
    )
    parser.add_argument(
        "--filters", type=Path, default=HERE / "intermediate" / "filter"
    )
    parser.add_argument("--write-intermediate", type=Path)
    args = parser.parse_args()
    data = verify(args.raw)
    if args.write:
        args.write.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    else:
        assert json.loads((HERE / "summary.json").read_text()) == data
        intermediate = verify_intermediate(args.branches, args.filters, args.dense)
        if args.write_intermediate:
            args.write_intermediate.write_text(
                json.dumps(intermediate, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        else:
            assert json.loads((HERE / "intermediate.json").read_text()) == intermediate
        print(
            "Verified 252 repeated filter plans and the capped branch outcomes at all seven sizes."
        )
    for row in data:
        print(
            row["case"],
            row["operators"],
            row["minimum_estimated_cost"],
            row["X"],
            row["Y"],
        )
