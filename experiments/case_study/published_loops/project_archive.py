"""Extract only the graph fields used by the two published-plan analyses."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

from analyze import ARCHIVE_SHA, digest


def project(plan):
    operators = []
    indexes = {}
    for original in plan["operators"]:
        key = original["operatorID"]
        if key in indexes:
            raise ValueError("Duplicate operator ID")
        index = indexes[key] = len(operators)
        omitted = any(prop.get("dummyProperty") == "Source XML" and
                      prop.get("dummyValue") == "Omitted for license reasons"
                      for prop in original["operatorProperties"].get("dummyPropertyList", []))
        flags = [{"dummyProperty": "Source XML", "dummyValue": "Omitted for license reasons"}] if omitted else []
        operators.append({"operatorID": index, "customDisplayName": original.get("customDisplayName", ""),
                          "operatorType": "Dummy" if original["operatorType"] == "Dummy" else "",
                          "operatorProperties": {"dummyPropertyList": flags}})
    links = [{side: {"operatorID": indexes[link[side]["operatorID"]], "portID": link[side]["portID"]}
              for side in ("source", "target")} for link in plan["links"]]
    return {"operators": operators, "links": links}


def export(source, destination):
    if hashlib.sha256(source.read_bytes()).hexdigest() != ARCHIVE_SHA:
        raise ValueError("Unexpected upstream archive")
    with tarfile.open(source) as src, destination.open("xb") as raw, gzip.GzipFile(
            fileobj=raw, filename="", mode="wb", mtime=0) as compressed, tarfile.open(
                mode="w|", fileobj=compressed) as dest:
        for member in src:
            if member.isfile() and member.name.endswith(".json"):
                graph = project(json.load(src.extractfile(member)))
                encoded = json.dumps(graph, separators=(",", ":")).encode()
                item = tarfile.TarInfo(digest(member.name) + ".json")
                item.size = len(encoded)
                dest.addfile(item, io.BytesIO(encoded))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    export(args.upstream, args.destination)
