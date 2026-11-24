"""Inspect vendor samples/tutorials and public .rmp files returned by GitHub code search."""

import argparse
import hashlib
import json
import math
import subprocess
import time
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests
from defusedxml import ElementTree as ET
from defusedxml.common import DefusedXmlException
from collect import get, load, save

# Native operators whose subprocess repeats over candidates, folds, or a collection.
EXPLICIT = {
    "x_validation",
    "cross_validation",
    "batch_x_validation",
    "sliding_window_validation",
    "bootstrapping_validation",
    "optimize_parameters_grid",
    "optimize_parameters_evolutionary",
}


def graph(root):
    """Keep operator classes, enabled state, port connections and subprocess nesting."""
    groups = []
    roles = set()

    def visit(process, path, active):
        ops = process.findall("operator")
        indices = {op.get("name"): i for i, op in enumerate(ops)}
        classes = []
        links = []
        for i, op in enumerate(ops):
            cls = op.get("class", "")
            live = op.get("activated", "true") != "false"
            classes.append([cls, live])
            subs = op.findall("process")
            name = cls.rsplit(":", 1)[-1]
            # Only active subprocess operators contribute evidence of a loop.
            if (
                active
                and live
                and subs
                and (name == "loop" or name.startswith("loop_") or name in EXPLICIT)
            ):
                roles.add(cls)
            for j, sub in enumerate(subs):
                visit(sub, [*path, i, j], active and live)
        for edge in process.findall("connect"):
            a, b = edge.get("from_op"), edge.get("to_op")
            if (a and a not in indices) or (b and b not in indices):
                raise ValueError("unresolved operator reference")
            links.append(
                [
                    indices[a] if a else -1,
                    edge.get("from_port", ""),
                    indices[b] if b else -1,
                    edge.get("to_port", ""),
                ]
            )
        groups.append([path, classes, sorted(links)])

    if root.tag != "process" or not root.findall("operator"):
        raise ValueError("no process root")
    visit(root, [], True)
    return {"groups": sorted(groups), "loop_classes": sorted(roles)}


def summarize(root):
    try:
        g = graph(root)
    except (ValueError, KeyError, TypeError):
        return {"status": "unrecognized-process"}
    raw = json.dumps(g, sort_keys=True, separators=(",", ":")).encode()
    return dict(
        status="read",
        match=bool(g["loop_classes"]),
        plan_sha256=hashlib.sha256(raw).hexdigest(),
        graph=g if g["loop_classes"] else None,
    )


def vendor(lib, dest):
    records = []
    files = {}
    for jar in sorted(lib.rglob("*.jar")):
        with zipfile.ZipFile(jar) as z:
            for name in sorted(z.namelist()):
                if not name.endswith((".xml", ".rmp")):
                    continue
                content = z.read(name)
                if not (name.endswith(".rmp") or b"tutorialProcess" in content):
                    continue
                doc = ET.fromstring(content)
                roots = (
                    [doc]
                    if name.endswith(".rmp")
                    else [
                        p
                        for t in doc.iter()
                        if t.tag.rsplit("}", 1)[-1] == "tutorialProcess"
                        for p in t
                        if p.tag == "process"
                    ]
                )
                for i, proc in enumerate(roots):
                    source = f"{jar.relative_to(lib).as_posix()}!{name}#{i + 1}"
                    records.append(dict(source=source, **summarize(proc)))
                    if jar.name not in files:
                        with jar.open("rb") as f:
                            files[jar.name] = hashlib.file_digest(
                                f, "sha256"
                            ).hexdigest()
    save(dest / "rapidminer-vendor.json.gz", dict(jar_sha256=files, records=records))
    print(
        "vendor",
        len(records),
        Counter(r["status"] for r in records),
        sum(r.get("match", False) for r in records),
        flush=True,
    )


def search_cache(root, low, high, page):
    path = root / f"{low}-{high}-{page}.json.gz"
    if not path.exists():
        query = f"operator extension:rmp size:{low}..{high}"
        cmd = [
            "gh",
            "api",
            "-X",
            "GET",
            "search/code",
            "-f",
            "q=" + query,
            "-f",
            "per_page=100",
            "-f",
            "page=" + str(page),
        ]
        for attempt in range(6):
            result = subprocess.run(
                cmd, capture_output=True, encoding="utf8", errors="replace"
            )
            if not result.returncode:
                obj = json.loads(result.stdout)
                if not obj["incomplete_results"]:
                    break
            elif (
                "rate limit" not in result.stderr.lower()
                and "502" not in result.stderr
                and "503" not in result.stderr
            ):
                raise RuntimeError(result.stderr[:140])
            time.sleep(max(8, 65 if result.returncode else 8))
        else:
            raise RuntimeError("GitHub search incomplete or rate limited " + query)
        items = [
            {
                "url": i["html_url"],
                "blob": i["sha"],
                "repo": i["repository"]["full_name"],
            }
            for i in obj["items"]
        ]
        save(path, {"total": obj["total_count"], "items": items})
        time.sleep(6.2)
    return load(path)


def github(root, jobs):
    pages = root / "rapidminer-search"
    pages.mkdir(exist_ok=True)
    blobs = root / "rapidminer-blobs"
    blobs.mkdir(exist_ok=True)
    items = {}
    inventory = root / "rapidminer-search-items.json.gz"
    if inventory.exists():
        items.update((row["url"], row) for row in load(inventory))

    def walk(lo, hi, page_threshold):
        first = search_cache(pages, lo, hi, 1)
        count = first["total"]
        # Include observed locations even when the search index changes between requests.
        for obj in first["items"]:
            items[obj["url"]] = obj
        if count > page_threshold and lo < hi:
            cut = min(
                hi - 1,
                max(
                    lo,
                    8000
                    if hi == 1_000_000_000 and lo == 0
                    else lo + max(4000, lo * 2)
                    if hi == 1_000_000_000
                    else (hi + lo) // 2,
                ),
            )
            walk(lo, cut, page_threshold)
            walk(cut + 1, hi, page_threshold)
            return
        if count > 1000:
            raise ValueError("Cannot enumerate a saturated exact file size")
        seen = set()
        for i in range(1, math.ceil(count / 100) + 1):
            result = first if i == 1 else search_cache(pages, lo, hi, i)
            for obj in result["items"]:
                items[obj["url"]] = obj
                seen.add(obj["url"])
        print(
            "GitHub bytes",
            lo,
            hi,
            "reported",
            count,
            "retrieved",
            len(seen),
            flush=True,
        )

    for threshold in (950, 95):
        walk(0, 1_000_000_000, threshold)
    save(root / "rapidminer-search-items.json.gz", list(items.values()))
    by_blob = {}
    for obj in items.values():
        if obj["repo"].casefold() == "texera/waffle":
            continue
        by_blob.setdefault(obj["blob"], []).append(obj)

    def fetch(pair):
        blob, sources = pair
        path = blobs / (blob + ".json.gz")
        if path.exists() and load(path)["status"] == "read":
            return
        record = {"status": "unavailable"}
        for obj in sources:
            parts = obj["url"].split("/blob/", 1)
            if len(parts) != 2:
                continue
            ref, _, p = parts[1].partition("/")
            url = (
                "https://raw.githubusercontent.com/" + obj["repo"] + "/" + ref + "/" + p
            )
            try:
                resp = get(url)
                if not resp.ok:
                    continue
                data = resp.content
                if (
                    hashlib.sha1(
                        b"blob " + str(len(data)).encode() + b"\0" + data
                    ).hexdigest()
                    != blob
                ):
                    record = {"status": "hash-mismatch"}
                    continue
                record = summarize(ET.fromstring(data))
                break
            except requests.RequestException:
                continue
            except (ET.ParseError, ValueError, DefusedXmlException):
                record = {"status": "invalid-xml"}
                break
        if record["status"] in ("unavailable", "hash-mismatch"):
            # A file can move between discovery and retrieval. The blob identifier stays usable.
            result = subprocess.run(
                [
                    "gh",
                    "api",
                    "--header",
                    "Accept: application/vnd.github.raw+json",
                    "repos/" + sources[0]["repo"] + "/git/blobs/" + blob,
                ],
                capture_output=True,
            )
            data = result.stdout
            if (
                result.returncode == 0
                and hashlib.sha1(
                    b"blob " + str(len(data)).encode() + b"\0" + data
                ).hexdigest()
                == blob
            ):
                try:
                    record = summarize(ET.fromstring(data))
                except (ET.ParseError, ValueError, DefusedXmlException):
                    record = {"status": "invalid-xml"}
        save(path, record)

    with ThreadPoolExecutor(jobs) as pool:
        list(pool.map(fetch, by_blob.items()))
    print(
        "GitHub locations",
        len(items),
        "external distinct blobs",
        len(by_blob),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--studio-lib", type=Path)
    p.add_argument("--github", action="store_true")
    p.add_argument("--jobs", type=int, default=8)
    args = p.parse_args()
    if args.studio_lib:
        vendor(args.studio_lib, args.root)
    if args.github:
        github(args.root, args.jobs)
