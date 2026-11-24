"""Scan public KNIME and n8n catalog records. Keep plan structure only; never run workflows."""

import argparse
import csv
import gzip
import hashlib
import json
import math
import re
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from defusedxml import ElementTree as ET

import requests

KNIME = "https://api.hub.knime.com"
N8N = "https://api.n8n.io"
SITEMAP = "https://n8n.io/sitemap-workflows.xml"
LOCAL = threading.local()


def get(url, params=None):
    if not hasattr(LOCAL, "session"):
        LOCAL.session = requests.Session()
    for attempt in range(4):
        try:
            response = LOCAL.session.get(url, params=params, timeout=(12, 75))
            if response.status_code not in (429, 500, 502, 503, 504):
                return response
            time.sleep(max(float(response.headers.get("Retry-After", 0)), 2**attempt))
        except (requests.ConnectionError, requests.Timeout):
            if attempt == 3:
                raise
            time.sleep(2**attempt)
    return response


def save(path, data):
    text = json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(gzip.compress(text.encode(), mtime=0))
    tmp.replace(path)


def load(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def n8n_graph(workflow):
    # Ignore credentials, node parameters, pinned example rows, annotations and titles.
    nodes = workflow["nodes"]
    names = Counter(n.get("name") for n in nodes)
    index = {
        n["name"]: i
        for i, n in enumerate(nodes)
        if n.get("name") and names[n["name"]] == 1
    }
    unresolved = 0
    types = [n["type"] for n in nodes]
    disabled = [bool(n.get("disabled")) for n in nodes]
    edges = []
    for name, ports in workflow["connections"].items():
        if ports == []:
            continue
        if not isinstance(ports, dict):
            raise ValueError("unknown connection shape")
        for output, branches in ports.items():
            if output != "main":
                continue
            for port, destinations in enumerate(branches):
                for dest in destinations or []:
                    if dest.get("type") == "main":
                        if name not in index or dest.get("node") not in index:
                            unresolved += 1
                            continue
                        edges.append(
                            (
                                index[name],
                                port,
                                index[dest["node"]],
                                dest.get("index", -1),
                            )
                        )
    graph = dict(types=types, disabled=disabled, edges=sorted(edges))
    if unresolved:
        graph["unresolved_edges"] = unresolved
    return graph


def has_cycle(graph):
    pred = {i: [] for i, off in enumerate(graph["disabled"]) if not off}
    for a, _, b, _ in graph["edges"]:
        if a in pred and b in pred:
            pred[b].append(a)
    try:
        tuple(TopologicalSorter(pred).static_order())
    except CycleError:
        return True
    return False


def n8n(root, jobs):
    sitemap = root / "n8n-ids.json.gz"
    if not sitemap.exists():
        response = get(SITEMAP)
        response.raise_for_status()
        ids = set()
        for loc in ET.fromstring(response.content).findall(".//{*}loc"):
            match = re.fullmatch(
                r"https://n8n\.io/workflows/(\d+)-[^/]+/?", loc.text or ""
            )
            if match:
                ids.add(int(match[1]))
        if not ids:
            raise ValueError("Empty template sitemap")
        save(sitemap, sorted(ids))
    listed = root / "n8n-directory.json.gz"
    if not listed.exists():

        def search(page):
            response = get(
                N8N + "/templates/search",
                {"rows": 250, "page": page, "sort": "createdAt:asc"},
            )
            response.raise_for_status()
            data = response.json()
            return data["totalWorkflows"], {
                int(w["id"]): bool(w.get("price") or w.get("purchaseUrl"))
                for w in data["workflows"]
            }

        total, entries = search(1)
        with ThreadPoolExecutor(min(jobs, 4)) as pool:
            for _, items in pool.map(search, range(2, math.ceil(total / 250) + 1)):
                entries.update(items)
        save(listed, {"reported_total": total, "entries": entries})
    directory = load(listed)
    flags = {int(k): v for k, v in directory["entries"].items()}
    ids = sorted(set(load(sitemap)) | set(flags))
    plans = root / "n8n-graphs"
    plans.mkdir(exist_ok=True)

    def fetch(i):
        path = plans / f"{i}.json.gz"
        if flags.get(i):
            record = dict(id=i, status="paid")
            save(path, record)
            return record
        if path.exists():
            record = load(path)
            if record["status"] in ("graph", "partial-graph", "paid"):
                return record
        try:
            response = get(f"{N8N}/templates/workflows/{i}")
            if not response.ok:
                result = dict(status=f"http-{response.status_code}")
            else:
                entry = response.json()["workflow"]
                if int(entry["id"]) != i:
                    raise ValueError("template ID mismatch")
                if entry.get("price") or entry.get("purchaseUrl"):
                    result = dict(status="paid")
                elif not isinstance(entry.get("workflow"), dict) or not isinstance(
                    entry["workflow"].get("nodes"), list
                ):
                    result = dict(status="no-public-graph")
                else:
                    graph = n8n_graph(entry["workflow"])
                    if not graph["types"]:
                        result = dict(status="empty-graph")
                    else:
                        result = dict(
                            status="partial-graph"
                            if graph.get("unresolved_edges")
                            else "graph",
                            cycle=has_cycle(graph),
                            graph=graph,
                        )
        except (
            AttributeError,
            ValueError,
            KeyError,
            TypeError,
            requests.RequestException,
        ) as err:
            result = dict(status="unreadable-" + type(err).__name__)
        result["id"] = i
        save(path, result)
        return result

    with (
        (root / "n8n.csv").open("w", newline="", encoding="utf8") as stream,
        ThreadPoolExecutor(jobs) as pool,
    ):
        writer = csv.writer(stream)
        writer.writerow(
            [
                "template_id",
                "status",
                "main_edge_cycle",
                "nodes",
                "main_edges",
                "plan_sha256",
            ]
        )
        for n, row in enumerate(pool.map(fetch, ids), 1):
            graph = row.get("graph")
            digest = (
                hashlib.sha256(
                    json.dumps(graph, sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest()
                if graph
                else ""
            )
            writer.writerow(
                [
                    row["id"],
                    row["status"],
                    int(row["cycle"]) if graph else "",
                    len(graph["types"]) if graph else "",
                    len(graph["edges"]) if graph else "",
                    digest,
                ]
            )
            if n % 1000 == 0:
                print("n8n", n, "/", len(ids), flush=True)


def knime(root):
    nodefile = root / "knime-factories.json.gz"
    if not nodefile.exists():
        reply = get(KNIME + "/nodes", {"details": "minimum"})
        reply.raise_for_status()
        save(
            nodefile,
            [
                {k: n.get(k) for k in ("factoryName", "factoryId", "nodeType", "title")}
                for n in reply.json()
            ],
        )
    types = {
        n[k]: n["nodeType"]
        for n in load(nodefile)
        for k in ("factoryId", "factoryName")
        if n[k] and n["nodeType"] in ("LoopStart", "LoopEnd")
    }
    pages = root / "knime-pages"
    pages.mkdir(exist_ok=True)
    cursor = None
    seen_cursors = set()
    seen = set()
    page = 0
    with (root / "knime.csv").open("w", newline="", encoding="utf8") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["workflow_id", "version_id", "status", "start_nodes", "end_nodes"]
        )
        while True:
            path = pages / f"{page:05}.json.gz"
            if path.exists():
                record = load(path)
                if record["cursor"] != cursor:
                    raise ValueError("Inconsistent cached page chain")
            else:
                params = {
                    "details": "aggregated",
                    "limit": 350,
                    "version": "current-state",
                }
                if cursor:
                    params["startingAfter"] = cursor
                response = get(KNIME + "/list/workflows", params)
                response.raise_for_status()
                data = response.json()
                rows = []
                for item in data["items"]:
                    details = item.get("details") or {}
                    nodes = details.get("aggregatedNodes")
                    boundaries = []
                    if nodes is not None:
                        boundaries = [
                            [
                                n["factoryName"],
                                n.get("level"),
                                n["count"],
                                types[n["factoryName"]],
                            ]
                            for n in nodes
                            if n["factoryName"] in types
                        ]
                    rows.append(
                        dict(
                            id=item["id"],
                            version=item.get("itemVersionId", ""),
                            indexed=nodes is not None,
                            boundaries=boundaries,
                        )
                    )
                record = dict(
                    cursor=cursor, following=data.get("nextStartingAfter"), rows=rows
                )
                save(path, record)
            for row in record["rows"]:
                if row["id"] in seen:
                    continue
                seen.add(row["id"])
                count = Counter()
                for _, _, n, role in row["boundaries"]:
                    count[role] += n
                writer.writerow(
                    [
                        row["id"],
                        row["version"],
                        "indexed" if row["indexed"] else "no-node-index",
                        count["LoopStart"],
                        count["LoopEnd"],
                    ]
                )
            page += 1
            if page % 10 == 0:
                print("KNIME", page, "pages,", len(seen), "IDs", flush=True)
            nxt = record["following"]
            if not nxt:
                break
            if nxt in seen_cursors:
                raise ValueError("Repeated cursor")
            seen_cursors.add(nxt)
            cursor = nxt
    print("KNIME complete", len(seen), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("system", choices=("knime", "n8n"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    if args.system == "knime":
        knime(args.root)
    else:
        n8n(args.root, args.jobs)
