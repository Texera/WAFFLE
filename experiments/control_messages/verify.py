"""Verify both experiments and return the counts plotted in the paper."""
import argparse
import csv
import json
from pathlib import Path

WIDTHS = (1, 2, 4, 8)
RESULTS = Path(__file__).with_name("results")


def check(results):
    native = [json.loads(line) for line in (results / "native.jsonl").read_text().splitlines()]
    cases = {row["case"]: row for row in native}
    expected_cases = {f"width-{w}-{mode}" for w in WIDTHS for mode in ("copies", "update")}
    if len(native) != len(expected_cases) or set(cases) != expected_cases:
        raise ValueError("Missing or duplicate native workflow run")
    for width in WIDTHS:
        for mode, value, callbacks in (("copies", 2, 1), ("update", 3, 2)):
            record = cases[f"width-{width}-{mode}"]
            expected = [{"K": value, "callbacks": callbacks, "rows_seen": width}]
            if record["strategy"] != mode or record["rows"] != expected:
                raise ValueError(f"Unexpected native result: {record}")

    with (results / "arrival_orders.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    modes = ("publication", "per_copy")
    expected_orders = {(w, pos, mode) for w in WIDTHS for pos in range(1, w + 1) for mode in modes}
    observed = set()
    successes = {mode: {w: 0 for w in WIDTHS} for mode in modes}
    for row in rows:
        width, before = int(row["branches"]), int(row["copies_before_update"])
        mode = row["identity"]
        order = (width, before, mode)
        if order not in expected_orders or order in observed:
            raise ValueError(f"Unexpected or repeated order: {order}")
        observed.add(order)
        delivered = [2] * before + [3] + [2] * (width - before)
        received = [2, 3] if mode == "publication" else delivered
        if ([int(x) for x in row["delivered_K"].split()] != delivered
                or [int(x) for x in row["callback_K"].split()] != received
                or int(row["callbacks"]) != len(received)
                or int(row["final_K"]) != received[-1]):
            raise ValueError(f"Unexpected callback trace or value: {row}")
        successes[mode][width] += int(row["final_K"]) == 3
    if observed != expected_orders:
        raise ValueError(f"Missing orders: {expected_orders - observed}")
    return successes


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", nargs="?", default=RESULTS, type=Path)
    counts = check(parser.parse_args().results)
    print("8 workflow outputs verified. Orders retaining K=3 out of 15:")
    for mode, widths in counts.items():
        print(f"{mode}: {sum(widths.values())} ({widths})")
