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


def verify(root):
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
        assert len(times) == len(LAYOUTS) * 2 * 7 and len(comp) == len(LAYOUTS)
        for groups, filters in LAYOUTS:
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
    for groups, filters in LAYOUTS:
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


def verify_dense(root):
    metadata = json.loads((root / "metadata.json").read_text())
    assert metadata["revision"] == "ddc04792511838d06f982ced01641e7d06ce6524"
    assert metadata["limit_s"] == 120 and metadata["warmup_per_method"] == 3
    assert metadata["fresh_jvms_per_method"] == metadata["trials_per_method"] == 1
    manifest = None
    for method in ("X", "Y"):
        folder = root / method
        weights = {
            r["operator"]: float(r["estimate"]) for r in rows(folder, "operators")
        }
        edges = [
            (r["from"], r["to"], r["required"] == "true") for r in rows(folder, "edges")
        ]
        assert len(weights) == 100 and len(edges) == 123
        required = {i for i, e in enumerate(edges) if e[2]}
        assert len(required) == 50
        graph = (weights, set(edges))
        if manifest is not None:
            assert manifest == graph
        manifest = graph
        minimum = lower_bound(weights, edges)
        assert minimum == 51
        [r] = rows(folder, "outcome")
        assert r["method"] == method and int(r["limit_s"]) == 120
        if r["status"] == "completed":
            cuts = {int(i) for i in r["cuts"].split(";") if i}
            assert required <= cuts
            assert float(r["cost"]) == cost_of(weights, weights, edges, cuts) == minimum
            assert 0 < int(r["total_ns"]) <= int(r["wall_ns"])
            assert int(r["states"]) > 0
        else:
            assert r["status"] == "timeout" and int(r["wall_ns"]) >= 120_000_000_000
            assert all(r[k] == "" for k in ("total_ns", "states", "cost", "cuts"))
        print(
            "Separate 100-operator branching trial:",
            method,
            r["status"],
            r["total_ns"],
            r["states"],
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", nargs="?", type=Path, default=HERE / "raw")
    parser.add_argument("--write", type=Path)
    parser.add_argument("--dense", type=Path, default=HERE / "dense")
    args = parser.parse_args()
    data = verify(args.raw)
    if args.write:
        args.write.write_text(
            json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
    else:
        assert json.loads((HERE / "summary.json").read_text()) == data
        verify_dense(args.dense)
    for row in data:
        print(
            row["case"],
            row["operators"],
            row["minimum_estimated_cost"],
            row["X"],
            row["Y"],
        )
