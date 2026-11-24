"""Attach version-matched operator types to the public KNIME plan projections."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time
import requests
from collect import KNIME, get, load, save


def fetch(row, folder):
    path = folder / (row["id"][1:] + ".json.gz")
    if path.exists() and load(path).get("version") == row["version"]:
        return
    try:
        response = get(f"{KNIME}/repository/{row['id']}", {"details": "full"})
        response.raise_for_status()
        meta = response.json()
        if meta["itemVersionId"] != row["version"]:
            raise ValueError("version-changed")
        operators = {
            str(n["nodeInstanceId"]): n.get("factoryName") or n["type"]
            for n in meta["details"]["nodes"]
        }
        data = dict(
            version=meta["itemVersionId"], operators=operators, size=meta.get("size")
        )
    except (ValueError, KeyError, requests.RequestException) as err:
        data = dict(error=type(err).__name__)
    save(path, data)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("--jobs", type=int, default=8)
    args = p.parse_args()
    dest = args.root / "knime-factory-maps"
    dest.mkdir(exist_ok=True)
    seen = set()
    page = 0
    with ThreadPoolExecutor(args.jobs) as pool:
        while True:
            path = args.root / "knime-pages" / f"{page:05}.json.gz"
            if not path.exists():
                time.sleep(3)
                continue
            record = load(path)
            batch = []
            for row in record["rows"]:
                if row["id"] not in seen and {"LoopStart", "LoopEnd"} <= {
                    n[3] for n in row["boundaries"]
                }:
                    batch.append(row)
                    seen.add(row["id"])
            list(pool.map(lambda r: fetch(r, dest), batch))
            if page % 10 == 0:
                print("Typed candidates", len(seen), "through page", page, flush=True)
            if not record["following"]:
                break
            page += 1


if __name__ == "__main__":
    main()
