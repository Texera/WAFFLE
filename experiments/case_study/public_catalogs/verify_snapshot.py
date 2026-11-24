"""Check a downloaded snapshot using only its source manifests and plan projections."""

import argparse
import csv
import gzip
import json
from collections import Counter
from pathlib import Path

from package_plans import digest, reverse_path, verify_cycle, verify_subprocess


def verify(data, manifests):
    info = json.loads((manifests / "coverage.json").read_text(encoding="utf8"))
    for name, counts in sorted(info.items()):
        prefix = name.replace("_", "-")
        with gzip.open(
            manifests / (prefix + "-manifest.csv.gz"), "rt", encoding="utf8", newline=""
        ) as f:
            rows = list(csv.DictReader(f))
        assert counts["records"] == len(rows)
        assert len({r["source"] for r in rows}) == len(rows)
        assert Counter(r["status"] for r in rows) == counts["status"]
        positives = {
            (r["source"], r["revision"]): r["projection_sha256"]
            for r in rows
            if r["loop_witness"] == "1"
        }
        assert len(positives) == counts["verified_loop_records"]
        assert len(set(positives.values())) == counts["distinct_loop_projections"]
        with gzip.open(data / (prefix + "-plans.jsonl.gz"), "rt", encoding="utf8") as f:
            for line in f:
                row = json.loads(line)
                graph = row["graph"]
                assert (
                    positives.pop((row["source"], row["revision"]))
                    == row["projection_sha256"]
                    == digest(graph)
                )
                if prefix == "knime":
                    assert any(reverse_path(s) for s in graph["boundary_scopes"])
                elif prefix.startswith("n8n"):
                    assert verify_cycle(graph)
                else:
                    assert verify_subprocess(graph)
        assert not positives
        print(
            prefix, counts["verified_loop_records"], "verified projections", flush=True
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plans", type=Path)
    p.add_argument("manifests", type=Path)
    a = p.parse_args()
    verify(a.plans, a.manifests)
