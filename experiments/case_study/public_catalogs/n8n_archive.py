"""Screen the workflow JSON directory at a fixed public community revision."""

import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
from urllib.parse import quote
import zipfile

from collect import get, has_cycle, n8n_graph, save

REPO = "Zie619/n8n-workflows"
PUBLISHED = "54688735f7043504a561565f2c2df3e8a9e835cc"
LATEST = "94007c1445d9258a7da116646b79473e7c7c3282"


def scan(dest, revision, filename):
    response = get(f"https://codeload.github.com/{REPO}/zip/{revision}")
    response.raise_for_status()
    records = []
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        for item in sorted(archive.infolist(), key=lambda i: i.filename):
            parts = PurePosixPath(item.filename).parts[1:]
            if not parts or parts[0] != "workflows" or not parts[-1].endswith(".json"):
                continue
            data = archive.read(item)
            sha = hashlib.sha1(
                b"blob " + str(len(data)).encode() + b"\0" + data
            ).hexdigest()
            obj = {
                "source": f"https://github.com/{REPO}/blob/{revision}/"
                + quote("/".join(parts)),
                "blob": sha,
            }
            try:
                workflow = json.loads(data.decode("utf-8-sig"))
                graph = n8n_graph(workflow)
                match = has_cycle(graph)
                obj.update(
                    status="partial-graph"
                    if graph.get("unresolved_edges")
                    else "graph",
                    match=match,
                    graph=graph if match else None,
                )
            except (ValueError, KeyError, AttributeError, TypeError) as exc:
                obj["status"] = "unreadable-" + type(exc).__name__
            records.append(obj)
    save(dest / filename, {"revision": revision, "records": records})
    print(
        "Community files",
        len(records),
        "with cycles",
        sum(bool(r.get("match")) for r in records),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    root = parser.parse_args().root
    scan(root, PUBLISHED, "n8n-community.json.gz")
    scan(root, LATEST, "n8n-community-latest.json.gz")
