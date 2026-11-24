"""Fetch public KNIME workflow.knime plans via ZIP ranges; omit inputs and settings."""

import argparse
import io
import re
import threading
import time
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path, PurePosixPath
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException

import requests
from collect import KNIME, get, load, save

LOCAL = threading.local()


class RemoteZIP(io.RawIOBase):
    def __init__(self, url, size_hint=0):
        self.url = url
        self.position = 0
        self.blocks = []
        initial = "bytes=0-2097151" if 0 < size_hint <= 2097152 else "bytes=-262144"
        a, payload, self.length = self.fetch(initial)
        self.blocks.append((a, payload))

    def fetch(self, value):
        if not hasattr(LOCAL, "session"):
            LOCAL.session = requests.Session()
        response = LOCAL.session.get(
            self.url, headers={"Range": value}, timeout=(10, 40), stream=True
        )
        with response:
            if response.status_code != 206:
                raise ValueError("range-unavailable")
            match = re.fullmatch(
                r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", "")
            )
            if not match:
                raise ValueError("invalid-range")
            start, end, size = map(int, match.groups())
            data = response.content
            if len(data) != end - start + 1:
                raise ValueError("short-range")
            return start, data, size

    def seekable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        pos = (0, self.position, self.length)[whence] + offset
        if pos < 0:
            raise OSError("invalid seek")
        self.position = pos
        return pos

    def read(self, n=-1):
        pos = self.position
        n = max(0, min(n if n >= 0 else self.length - pos, self.length - pos))
        if n == 0:
            return b""
        for start, block in self.blocks:
            if start <= pos and pos + n <= start + len(block):
                self.position += n
                return block[pos - start : pos - start + n]
        if n > 32 * 1024 * 1024:
            raise ValueError("oversize-zip-member")
        end = min(self.length - 1, pos + max(n, 16384) - 1)
        start, block, _ = self.fetch(f"bytes={pos}-{end}")
        if start != pos:
            raise ValueError("unexpected-offset")
        self.blocks.append((start, block))
        self.position += n
        return block[:n]


def children(node, key):
    for child in node:
        if child.get("key") == key:
            return child
    return ()


def plan_graph(data):
    root = ET.fromstring(data)
    nodes = set()
    for node in children(root, "nodes"):
        props = {x.get("key"): x.get("value") for x in node}
        num = props["id"]
        if num in nodes:
            raise ValueError("duplicate-local-node")
        nodes.add(num)
    edges = []
    for link in children(root, "connections"):
        props = {x.get("key"): x.get("value") for x in link}
        a, b = props["sourceID"], props["destID"]
        if a in nodes and b in nodes:
            edges.append((a, props.get("sourcePort"), b, props.get("destPort")))
    return dict(nodes=nodes, edges=edges)


def reachable(graph, starts, ends):
    next_nodes = defaultdict(set)
    for a, _, b, _ in graph["edges"]:
        next_nodes[a].add(b)
    pending = list(starts)
    seen = set(starts)
    while pending:
        n = pending.pop()
        for child in next_nodes[n] - seen:
            if child in ends:
                return True
            seen.add(child)
            pending.append(child)
    return False


def fetch(row, folder, labels):
    path = folder / (row["id"][1:] + ".json.gz")
    if path.exists() and load(path)["status"] == "read":
        return
    try:
        item_url = f"{KNIME}/repository/{row['id']}"
        meta = get(item_url, {"details": "full"})
        if not meta.ok:
            raise ValueError("metadata-http-" + str(meta.status_code))
        metadata = meta.json()
        if metadata.get("itemVersionId") != row["version"]:
            raise ValueError("version-changed")
        roles_by_id = {
            str(n["nodeInstanceId"]): labels[n["factoryName"]]
            for n in metadata["details"]["nodes"]
            if n.get("factoryName") in labels
        }
        response = get(item_url + "/artifact", {"version": "current-state"})
        if not response.ok:
            raise ValueError("http-" + str(response.status_code))
        scopes = defaultdict(set)
        for address, role in roles_by_id.items():
            scopes[tuple(address.split(":")[:-1])].add(role)
        eligible_scopes = {
            s for s, roles in scopes.items() if roles == {"LoopStart", "LoopEnd"}
        }
        stream = RemoteZIP(response.json()["downloadUrl"], metadata.get("size") or 0)
        graphs = []
        hit = False
        with zipfile.ZipFile(stream) as archive:
            members = [
                i
                for i in archive.infolist()
                if PurePosixPath(i.filename).name == "workflow.knime"
            ]
            if not members:
                raise ValueError("no-workflow-xml")
            root_depth = min(len(PurePosixPath(m.filename).parts) for m in members)
            root_members = [
                m for m in members if len(PurePosixPath(m.filename).parts) == root_depth
            ]
            if len(root_members) != 1:
                raise ValueError("ambiguous-workflow-root")
            prefix = PurePosixPath(root_members[0].filename).parent
            members.sort(key=lambda m: len(PurePosixPath(m.filename).parts))
            for member in members:
                member_path = PurePosixPath(member.filename)
                if not member_path.is_relative_to(prefix):
                    continue
                segments = member_path.relative_to(prefix).parts[:-1]
                parents = [re.search(r"\(#(\d+)\)$", s) for s in segments]
                if any(v is None for v in parents):
                    continue
                parent_ids = [v[1] for v in parents]
                if tuple(parent_ids) not in eligible_scopes:
                    continue
                if member.file_size > 32 * 1024 * 1024:
                    raise ValueError("oversize-workflow-xml")
                if stream.length > 2097152:
                    stream.seek(member.header_offset)
                    stream.read(
                        min(
                            stream.length - member.header_offset,
                            member.compress_size + 1024,
                        )
                    )
                graph = plan_graph(archive.read(member))
                roles = {
                    i: roles_by_id.get(":".join([*parent_ids, i]))
                    for i in graph["nodes"]
                }
                start = {i for i, r in roles.items() if r == "LoopStart"}
                end = {i for i, r in roles.items() if r == "LoopEnd"}
                connected = reachable(graph, start, end)
                hit |= connected
                # Store only generic graph structure and boundary roles, no display text or settings.
                graphs.append(
                    dict(
                        container=parent_ids,
                        roles={i: r for i, r in roles.items() if r},
                        node_ids=sorted(roles),
                        edges=graph["edges"],
                        connected=connected,
                    )
                )
        result = dict(
            status="read",
            connected=hit,
            graphs=graphs,
            archive_bytes=stream.length,
            eligible_scopes=len(eligible_scopes),
            version=row["version"],
        )
    except (
        AttributeError,
        TypeError,
        IndexError,
        ValueError,
        KeyError,
        zipfile.BadZipFile,
        OSError,
        ET.ParseError,
        DefusedXmlException,
        RuntimeError,
        requests.RequestException,
    ) as e:
        msg = str(e)
        result = dict(
            status=msg if re.fullmatch(r"[a-z-]+(?:\d+)?", msg) else type(e).__name__
        )
    result["id"] = row["id"]
    save(path, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()
    catalog = load(args.root / "knime-factories.json.gz")
    labels = {
        n[k]: n["nodeType"]
        for n in catalog
        for k in ("factoryName", "factoryId")
        if n.get(k) and n.get("nodeType") in ("LoopStart", "LoopEnd")
    }
    folder = args.root / "knime-graphs"
    folder.mkdir(exist_ok=True)
    page = 0
    seen = set()
    with ThreadPoolExecutor(args.jobs) as pool:
        pending = set()
        while True:
            p = args.root / "knime-pages" / f"{page:05}.json.gz"
            if not p.exists():
                time.sleep(3)
                continue
            record = load(p)
            candidates = [
                r
                for r in record["rows"]
                if {"LoopStart", "LoopEnd"} <= {b[3] for b in r["boundaries"]}
                and r["id"] not in seen
            ]
            for row in candidates:
                pending.add(pool.submit(fetch, row, folder, labels))
                if len(pending) >= 3 * args.jobs:
                    done, pending = wait(pending, return_when=FIRST_COMPLETED)
                    for future in done:
                        future.result()
            seen.update(r["id"] for r in candidates)
            if page % 5 == 0:
                print("archive checks", len(seen), "through page", page, flush=True)
            if not record["following"]:
                break
            page += 1
        for future in pending:
            future.result()


if __name__ == "__main__":
    main()
