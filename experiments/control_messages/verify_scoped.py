"""Verify the saved full-workflow outcomes and the corresponding controlled deliveries."""
import argparse
import json
from pathlib import Path
from scoped_orders import CASES, verify

RESULTS = Path(__file__).with_name("scoped_results")


def check_native(records, loop_id):
    expected = {(case, layout) for case in CASES for layout in ("LR", "RL")}
    expected.add(("new-iteration", "LR"))
    executions = set()
    for record in records:
        case, layout = record["case"], record["layout"]
        expected.remove((case, layout))
        execution = record["execution_id"]
        assert execution not in executions
        executions.add(execution)
        if case == "conflict":
            assert record["outcome"] == "conflict" and "merge" in record["worker"]
            assert record["error"] in {
                f"Binding conflict for K in {loop_id}: 2 versus 3",
                f"Binding conflict for K in {loop_id}: 3 versus 2",
            }, record
            continue
        assert record["outcome"] == "completed"
        rows = record["rows"]
        assert sorted(row["K"] for row in rows) == ([2, 3] if case == "new-iteration" else [2])
        for row in rows:
            assert row["rows_seen"] == 2 and row["first"] in (0, 1)
            assert row["ratio"] == (0.8 if case == "independent" else 0)
            assert row["calls"] == (2 if case == "independent" else 1)
    assert not expected, expected


def check_original(records):
    pairs = [record for record in records if record["case"] in CASES]
    assert len(pairs) == 6
    for case, pair in CASES.items():
        actual = [rec["events"] for rec in pairs if rec["case"] == case]
        assert [[(e["id"], e["incoming"]) for e in ev] for ev in actual] == [pair, list(reversed(pair))]
        for events in actual:
            final = events[-1]
            assert final["callbacks"] == final["forwarded"] == [e["incoming"] for e in events]
            assert not final["error"] and final["visible"] == final["incoming"]


def check(results):
    verify(json.loads((results / "receiver.json").read_text()))
    check_original(json.loads((results / "receiver-original.json").read_text()))
    workflow = json.loads((results / "equal-LR.json").read_text())
    loop_id = next(op["operatorID"] for op in workflow["operators"] if op["operatorType"] == "LoopStart")
    check_native([json.loads(line) for line in (results / "native.jsonl").read_text().splitlines()], loop_id)
    print("Verified 7 full workflows, 12 scoped receiver traces and 6 original receiver comparisons.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, nargs="?", default=RESULTS)
    check(parser.parse_args().results)
