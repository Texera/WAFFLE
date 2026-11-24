"""Verify the snapshot and emit source manifests plus portable structural plans."""

import argparse
import csv
import gzip
import hashlib
import io
import json
from collections import Counter, defaultdict, deque
from contextlib import contextmanager, ExitStack
from pathlib import Path

from collect import load
from rapidminer import EXPLICIT


def serial(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(obj):
    return hashlib.sha256(serial(obj).encode()).hexdigest()


@contextmanager
def output(path):
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz,
    ):
        with io.TextIOWrapper(gz, encoding="utf8", newline="\n") as stream:
            yield stream


def reverse_path(graph):
    parents = defaultdict(set)
    ids = set(graph["node_ids"])
    for a, _, b, _ in graph["edges"]:
        assert a in ids and b in ids
        parents[b].add(a)
    starts = {i for i, role in graph["roles"].items() if role == "LoopStart"}
    seen = {i for i, role in graph["roles"].items() if role == "LoopEnd"}
    pending = list(seen)
    while pending:
        previous = parents[pending.pop()] - seen
        if previous & starts:
            return True
        pending.extend(previous)
        seen.update(previous)
    return False


def verify_cycle(graph):
    active = {i for i, off in enumerate(graph["disabled"]) if not off}
    assert len(graph["disabled"]) == len(graph["types"])
    targets = defaultdict(list)
    degree = dict.fromkeys(active, 0)
    for a, _, b, _ in graph["edges"]:
        assert 0 <= a < len(graph["types"]) and 0 <= b < len(graph["types"])
        if a in active and b in active:
            targets[a].append(b)
            degree[b] += 1
    ready = deque(i for i, d in degree.items() if d == 0)
    count = 0
    while ready:
        count += 1
        for i in targets[ready.popleft()]:
            degree[i] -= 1
            if degree[i] == 0:
                ready.append(i)
    return count < len(active)


def verify_subprocess(graph):
    groups = {tuple(path): ops for path, ops, _ in graph["groups"]}
    found = set()
    for path in groups:
        live = True
        for depth in range(0, len(path), 2):
            cls, enabled = groups[path[:depth]][path[depth]]
            live = live and enabled
        if path and live:
            name = cls.split(":")[-1]
            if name == "loop" or name.startswith("loop_") or name in EXPLICIT:
                found.add(cls)
    assert sorted(found) == graph["loop_classes"]
    return bool(found)


class Collection:
    def __init__(self, name, stack, out, manifests):
        self.name = name
        self.counts = Counter()
        self.plans = stack.enter_context(output(out / (name + "-plans.jsonl.gz")))
        self.rows = csv.writer(
            stack.enter_context(output(manifests / (name + "-manifest.csv.gz"))),
            lineterminator="\n",
        )
        self.rows.writerow(
            ["source", "revision", "status", "loop_witness", "projection_sha256"]
        )
        self.matches = 0
        self.ids = set()
        self.fingerprints = set()

    def add(self, source, revision, status, graph=None, witness=None):
        assert source not in self.ids, source
        self.ids.add(source)
        self.counts[status] += 1
        checksum = ""
        if graph is not None:
            assert witness is True
            checksum = digest(graph)
            self.matches += 1
            self.fingerprints.add(checksum)
            self.plans.write(
                serial(
                    {
                        "source": source,
                        "revision": revision,
                        "graph": graph,
                        "projection_sha256": checksum,
                    }
                )
                + "\n"
            )
        self.rows.writerow(
            [
                source,
                revision,
                status,
                "" if witness is None else int(witness),
                checksum,
            ]
        )

    def summary(self):
        return {
            "records": len(self.ids),
            "verified_loop_records": self.matches,
            "distinct_loop_projections": len(self.fingerprints),
            "status": dict(sorted(self.counts.items())),
        }


def knime(root, col):
    raw_pages = sorted((root / "knime-pages").glob("*.json.gz"))
    cursor = None
    seen = set()
    duplicates = 0
    byte_discrepancies = 0
    missing_factory_maps = 0
    assert raw_pages
    for n, page in enumerate(raw_pages):
        assert page.name == f"{n:05}.json.gz"
        record = load(page)
        assert record["cursor"] == cursor
        cursor = record["following"]
        assert bool(cursor) == (n < len(raw_pages) - 1), (
            "Incomplete catalog cursor chain"
        )
        for row in record["rows"]:
            i = row["id"]
            if i in seen:
                duplicates += 1
                continue
            seen.add(i)
            src = "https://api.hub.knime.com/repository/" + i
            args = (src, row["version"])
            if not row["indexed"]:
                col.add(*args, "no-node-index")
                continue
            if {"LoopStart", "LoopEnd"} - {b[3] for b in row["boundaries"]}:
                col.add(*args, "no-native-boundary-pair", witness=False)
                continue
            item = load(root / "knime-graphs" / (i[1:] + ".json.gz"))
            assert item["id"] == i
            if item["status"] != "read":
                col.add(*args, item["status"])
                continue
            assert item.get("version", row["version"]) == row["version"]
            types = load(root / "knime-factory-maps" / (i[1:] + ".json.gz"))
            if "version" not in types:
                missing_factory_maps += 1
            else:
                assert types["version"] == row["version"]
                if types.get("size") and types["size"] != item["archive_bytes"]:
                    byte_discrepancies += 1
                    col.add(*args, "archive-size-mismatch")
                    continue
            groups = []
            for g in item["graphs"]:
                assert reverse_path(g) == g["connected"]
                if set(g["roles"].values()) >= {"LoopStart", "LoopEnd"}:
                    groups.append(
                        {
                            k: g[k]
                            for k in (
                                "container",
                                "node_ids",
                                "roles",
                                "edges",
                                "connected",
                            )
                        }
                    )
            match = any(g["connected"] for g in groups)
            assert match == item["connected"]
            graph = (
                {"operators": types.get("operators", {}), "boundary_scopes": groups}
                if match
                else None
            )
            missing_scopes = item.get("eligible_scopes", 0) > len(groups)
            status = "partial-scopes" if missing_scopes else "read"
            col.add(
                *args, status, graph, match if match or not missing_scopes else None
            )
    return {
        **col.summary(),
        "cursor_pages": len(raw_pages),
        "repeated_catalog_ids": duplicates,
        "map_fetch_failures": missing_factory_maps,
        "archive_size_mismatches": byte_discrepancies,
    }


def n8n(root, col):
    listing = load(root / "n8n-directory.json.gz")
    sitemap = set(load(root / "n8n-ids.json.gz"))
    union = sitemap | set(map(int, listing["entries"]))
    for i in sorted(union):
        rec = load(root / "n8n-graphs" / f"{i}.json.gz")
        assert rec["id"] == i
        src = f"https://api.n8n.io/templates/workflows/{i}"
        if "graph" in rec:
            graph = rec["graph"]
            match = verify_cycle(graph)
            assert match == rec["cycle"]
            col.add(
                src,
                "",
                rec["status"],
                graph if match else None,
                match if match or rec["status"] == "graph" else None,
            )
        else:
            col.add(src, "", rec["status"])
    return {
        **col.summary(),
        "sitemap_ids": len(sitemap),
        "distinct_search_ids": len(listing["entries"]),
        "search_api_reported_total": listing["reported_total"],
    }


def n8n_archive(root, col, filename, official):
    data = load(root / filename)
    for r in data["records"]:
        match = r.get("match")
        if r.get("graph"):
            assert verify_cycle(r["graph"]) == match
        witness = match if match or r["status"] == "graph" else None
        col.add(r["source"], r["blob"], r["status"], r.get("graph"), witness)
    return {
        **col.summary(),
        "repository_revision": data["revision"],
        "loop_projections_also_in_directory": len(
            col.fingerprints & official.fingerprints
        ),
    }


def rapidminer(root, vendor, community, sources_file):
    data = load(root / "rapidminer-vendor.json.gz")

    def add(collection, src, rev, r):
        match = r.get("match")
        graph = r.get("graph")
        if graph:
            assert verify_subprocess(graph) and r["plan_sha256"] == digest(graph)
        collection.add(src, rev, r["status"], graph, match)

    for row in sorted(data["records"], key=lambda r: r["source"]):
        jar = row["source"].split("!")[0].split("/")[-1]
        add(vendor, row["source"], data["jar_sha256"][jar], row)
    items = load(root / "rapidminer-search-items.json.gz")
    by_blob = defaultdict(set)
    locations = set()
    excluded = 0
    for obj in items:
        if obj["repo"].casefold() == "texera/waffle":
            excluded += 1
            continue
        locations.add(obj["url"])
        by_blob[obj["blob"]].add(obj["url"])
    with output(sources_file) as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["git_blob_sha1", "published_source"])
        for blob, urls in sorted(by_blob.items()):
            rec = load(root / "rapidminer-blobs" / (blob + ".json.gz"))
            for url in sorted(urls):
                writer.writerow([blob, url])
            add(community, min(urls), blob, rec)
    return vendor.summary(), {
        **community.summary(),
        "indexed_locations": len(items),
        "external_locations": len(locations),
        "loop_projections_also_in_vendor": len(
            community.fingerprints & vendor.fingerprints
        ),
        "own_artifact_locations_excluded": excluded,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("cache", type=Path)
    p.add_argument(
        "plans", type=Path, help="Output directory for local plan projections"
    )
    p.add_argument(
        "manifests", type=Path, help="Output directory for shareable source inventories"
    )
    args = p.parse_args()
    args.plans.mkdir(parents=True, exist_ok=True)
    args.manifests.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:

        def make(name):
            return Collection(name, stack, args.plans, args.manifests)

        official = make("n8n")
        stats = {
            "knime": knime(args.cache, make("knime")),
            "n8n": n8n(args.cache, official),
        }
        for key in ("n8n-community", "n8n-community-latest"):
            stats[key] = n8n_archive(args.cache, make(key), key + ".json.gz", official)
        stats["rapidminer_vendor"], stats["rapidminer_github"] = rapidminer(
            args.cache,
            make("rapidminer-vendor"),
            make("rapidminer-github"),
            args.manifests / "rapidminer-locations.csv.gz",
        )
    (args.manifests / "coverage.json").write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf8"
    )
    print(json.dumps(stats, indent=2), flush=True)


if __name__ == "__main__":
    main()
