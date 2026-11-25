"""Count distinct-branch reconvergence in Chowder's published logical operator graphs."""
import argparse
from collections import Counter
from graphlib import CycleError, TopologicalSorter
import hashlib
import json
from pathlib import Path
import tarfile

ARCHIVE_SHA = "d8fd2f7cc1b95647326eed1bfdb4493c49b58f896bd43f997928ad476e6f402a"
SOURCE = ("https://raw.githubusercontent.com/Texera/Chowder/"
          "e054e86a6a239b15783b8884e675a5f43a36f38d/experiments/workflows/6k_set/plans_json.tar.gz")


def count_reconvergence(plan):
    operators = [node["operatorID"] for node in plan["operators"]]
    if len(operators) != len(set(operators)):
        raise ValueError("duplicate operator identifier")
    predecessors = {node: set() for node in operators}
    for link in plan["links"]:
        source = link["source"]["operatorID"]
        target = link["target"]["operatorID"]
        if source not in predecessors or target not in predecessors:
            raise ValueError("edge with an unknown endpoint")
        predecessors[target].add(source)
    order = tuple(TopologicalSorter(predecessors).static_order())

    # A merge receives the same source assignment on distinct parent edges
    # exactly when two parents have at least one common ancestor (possibly a parent).
    ancestors = {}
    reconvergent_merges = 0
    for index, node in enumerate(order):
        reached = 0
        overlap = False
        for parent in predecessors[node]:
            overlap |= bool(reached & ancestors[parent])
            reached |= ancestors[parent]
        reconvergent_merges += overlap
        ancestors[node] = reached | (1 << index)

    # Independent cross-check: propagate 0/1/2-or-more paths from each source.
    # In a DAG every possible split is reachable from some source.
    repeated = False
    for source in (n for n in order if not predecessors[n]):
        paths = {}
        for node in order:
            paths[node] = min(2, int(node == source) + sum(paths[p] for p in predecessors[node]))
            if paths[node] == 2:
                repeated = True
                break
        if repeated:
            break
    if repeated != bool(reconvergent_merges):
        raise AssertionError("ancestor and path-count checks disagree")
    return len(operators), reconvergent_merges


def summarize(archive):
    # The bundled projection contains the same endpoints and preserves isolated vertices.
    if hashlib.sha256(archive.read_bytes()).hexdigest() not in (ARCHIVE_SHA, "6450d44dd226f2e98734b276efd90f48c44ff29d293b72483816204ce42d09a5"):
        raise ValueError("unexpected archive; obtain the pinned source")
    groups = {label: Counter(workflows=0, with_reconvergence=0)
              for label in ("0-10", "11-20", "21-50", "51+")}
    observed = Counter(json_files=0, cyclic=0, invalid=0, reconvergent_merges=0)
    with tarfile.open(archive) as source:
        for member in source:
            if not member.isfile() or not member.name.endswith(".json"):
                continue
            observed["json_files"] += 1
            plan = json.load(source.extractfile(member))
            try:
                size, merges = count_reconvergence(plan)
            except CycleError:
                observed["cyclic"] += 1
                continue
            except ValueError:
                observed["invalid"] += 1
                continue
            group = groups["0-10" if size <= 10 else "11-20" if size <= 20
                           else "21-50" if size <= 50 else "51+"]
            group["workflows"] += 1
            group["with_reconvergence"] += bool(merges)
            observed["reconvergent_merges"] += merges
    return {"archive": SOURCE, "sha256": ARCHIVE_SHA, "counts": observed, "by_size": groups}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize(args.archive), indent=2))
