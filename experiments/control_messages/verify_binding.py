"""Check every first-tuple binding and every Filter output row."""
import argparse
import json
from pathlib import Path

from prepare_binding import REPEATS, ROWS, WORKERS, WIDE_WORKERS

RESULTS = Path(__file__).with_name("binding_results")


def check(path, widths=WORKERS):
    records = [json.loads(line) for line in (path / "native.jsonl").read_text().splitlines()]
    expected_runs = {(workers, repeat) for workers in widths for repeat in range(REPEATS)}
    seen = set()
    summary = {workers: {"observations": 0, "matched": 0} for workers in widths}
    expected_rows = [[k, x] for k in (2, 3) for x in range(k, ROWS)]
    for record in records:
        workers, repeat = record["workers"], record["repeat"]
        run = (workers, repeat)
        if run not in expected_runs or run in seen:
            raise ValueError(f"Unexpected or duplicate run {run}")
        seen.add(run)
        if record["input_rows"] != ROWS or record["rows"] != expected_rows:
            raise ValueError(f"Wrong Filter output for {run}")
        observations = record["first_tuples"]
        keys = [(item["received_K"], item["worker"]) for item in observations]
        expected_keys = {(k, worker) for k in (2, 3) for worker in range(workers)}
        if set(keys) != expected_keys or len(keys) != len(expected_keys):
            raise ValueError(f"Missing or duplicate worker observation for {run}: {keys}")
        for item in observations:
            if item["workers"] != workers or not 0 <= item["first_x"] < ROWS:
                raise ValueError(f"Invalid worker metadata for {run}: {item}")
            summary[workers]["observations"] += 1
            summary[workers]["matched"] += item["bound_K"] == item["received_K"]
        if any(item["bound_K"] != item["received_K"] for item in observations):
            raise ValueError(f"Property bound to the wrong K in {run}")
    if seen != expected_runs:
        raise ValueError(f"Missing runs: {expected_runs - seen}")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="?", type=Path, default=RESULTS)
    parser.add_argument("--wide", action="store_true", help="Expect all 16- and 32-worker runs")
    args = parser.parse_args()
    for workers, counts in check(args.results, WIDE_WORKERS if args.wide else WORKERS).items():
        print(f"{workers} workers: {counts['matched']}/{counts['observations']} first tuples use the expected K")
