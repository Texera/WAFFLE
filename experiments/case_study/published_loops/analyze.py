"""Census of named loop boundaries and a reproducible sample of distinct published plans."""
import argparse
import csv
import hashlib
import json
import re
import tarfile
from collections import Counter, defaultdict
from graphlib import TopologicalSorter
from pathlib import Path

ARCHIVE_SHA = "d8fd2f7cc1b95647326eed1bfdb4493c49b58f896bd43f997928ad476e6f402a"
HERE = Path(__file__).resolve().parent


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def label(value):
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold())).replace("tablerow ", "table row ")


def analyze(plan):
    names = {op["operatorID"]: label(op.get("customDisplayName", "")) for op in plan["operators"]}
    if len(names) != len(plan["operators"]):
        raise ValueError("Duplicate operator identifier")
    starts = {n for n, name in names.items() if re.search(r"\bloop start\b", name)}
    ends = {n for n, name in names.items() if re.search(r"\bloop end\b", name)}
    if not starts or not ends:
        return "no connected pair", None
    inputs = {n: [] for n in names}
    outputs = {n: [] for n in names}
    for link in plan["links"]:
        a, b = link["source"], link["target"]
        u, v = a["operatorID"], b["operatorID"]
        ports = (a["portID"], b["portID"])
        inputs[v].append((u, ports))
        outputs[u].append((v, ports))
    order = list(TopologicalSorter({n: [u for u, _ in parents] for n, parents in inputs.items()}).static_order())
    reached = set(starts)
    for n in order:
        if n in reached:
            reached.update(v for v, _ in outputs[n])
    if not reached & ends:
        return "no connected pair", None
    if len(starts) != 1 or len(ends) != 1:
        return "multiple named boundaries", None
    # A label-preserving graph isomorphism must preserve each vertex's ancestor
    # and descendant signatures. Distinct fingerprints certify distinct labeled
    # structures; no claim about equivalence is needed for matching digests.
    def signatures(nodes, links):
        result = {}
        for n in nodes:
            neighbors = sorted((result[u], ports) for u, ports in links[n])
            result[n] = digest([names[n], neighbors])
        return result
    upstream = signatures(order, inputs)
    downstream = signatures(reversed(order), outputs)
    fingerprint = digest(sorted((upstream[n], downstream[n]) for n in names))
    start, = starts
    end, = ends
    # Intersect forward and backward reachability to isolate vertices on
    # a start-to-end path. A branch ending in a separate sink lies outside it.
    to_end = {end}
    for n in reversed(order):
        if n in to_end:
            to_end.update(u for u, _ in inputs[n])
    paths = reached & to_end
    side_in = sum(u not in paths for v in paths - {start} for u, _ in inputs[v])
    side_out = sum(v not in paths for u in paths - {end} for v, _ in outputs[u])
    hidden = all(op["operatorType"] == "Dummy" and any(
        prop.get("dummyProperty") == "Source XML" and prop.get("dummyValue") == "Omitted for license reasons"
        for prop in op["operatorProperties"].get("dummyPropertyList", []))
        for op in plan["operators"] if op["operatorID"] in (start, end))
    return "one connected pair", (fingerprint, names[start], names[end], side_in, side_out, hidden)


def sample(archive):
    if hashlib.file_digest(archive, "sha256").hexdigest() != ARCHIVE_SHA:
        raise ValueError("Unexpected 6K-Set archive")
    archive.seek(0)
    groups = defaultdict(list)
    census = Counter()
    with tarfile.open(fileobj=archive) as tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith(".json"):
                continue
            plan = json.load(tar.extractfile(member))
            status, record = analyze(plan)
            census[status] += 1
            if record:
                fingerprint, *details = record
                groups[fingerprint].append((digest(member.name), *details))
    originals = json.loads((HERE / "reference_pairs.json").read_text())
    pairs = {(label(x["start"]), label(x["end"])) for x in originals}
    rows = []
    for fingerprint in sorted(groups)[:500]:
        archive_path_hash, start, end, side_in, side_out, hidden = min(groups[fingerprint])
        rows.append((fingerprint, archive_path_hash, start, end, int((start, end) in pairs), side_in, side_out, int(hidden)))
    if len(rows) != 500:
        raise ValueError("Fewer than 500 distinct eligible structures")
    pair_counts = Counter((r[2], r[3]) for r in rows)
    return rows, dict(archive_members=sum(census.values()), classifications=dict(census),
                      eligible_signatures=len(groups), sample=len(rows), sampled_pairs=len(pair_counts),
                      matching_reference_pair=sum(r[4] for r in rows),
                      path_regions_without_side_links=sum(r[5] == 0 and r[6] == 0 for r in rows),
                      missing_boundary_source=sum(r[7] for r in rows),
                      pairs=[dict(start=s, end=e, plans=n) for (s, e), n in sorted(pair_counts.items())])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("archive", type=Path)
    p.add_argument("output", type=Path)
    args = p.parse_args()
    with args.archive.open("rb") as stream:
        rows, summary = sample(stream)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "sample.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(("fingerprint", "archive_member_hash", "start", "end", "reference_pair",
                         "incoming_side_links", "outgoing_side_links", "boundary_source_omitted"))
        writer.writerows(rows)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
