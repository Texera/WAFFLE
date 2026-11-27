"""Verify the Table 3 output examples against the recorded engine results."""

import csv
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CASES = HERE.parent
sys.path.insert(0, str(CASES))
from check import check_translations, compare, expected_rows


def main():
    reference = CASES / "results"
    check_translations(CASES)
    samples = [json.loads(line) for line in (reference / "native.jsonl").read_text().splitlines()]
    for number in (12, 16):
        run = json.loads((reference / f"{number}-knime-run.json").read_bytes())
        assert run["exit_code"] == 0 and run["exports_present"]
        sample, = [s for s in samples if s["case"] == str(number)]
        compare(expected_rows(reference, number), [json.loads(r["payload"]) for r in sample["rows"]])

    workflow = json.loads((HERE / "workflow.json").read_bytes())
    ops = workflow["operators"]
    assert [op["operatorType"] for op in ops] == ["PythonUDFSourceV2", "LoopStart", "LoopEnd"]
    assert [(e["source"]["operatorID"], e["target"]["operatorID"]) for e in workflow["links"]] == [
        (a["operatorID"], b["operatorID"]) for a, b in zip(ops, ops[1:])
    ]
    history = json.loads((HERE / "native.jsonl").read_bytes())["rows"]
    assert history == expected_rows(reference, 16) == [{"currentIteration": i} for i in range(5)]

    path = CASES.parent / "loop_policies/native_controls/observations.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        records = list(csv.DictReader(stream))
    targets = [r for r in records if r["rule"] == "target"]
    assert len(targets) == 16
    for fixture in ("immediate", "near", "far", "unreachable"):
        full, = [json.loads(r["output"]) for r in records
                 if (r["rule"], r["fixture"], r["engine"]) == ("sweep", fixture, "waffle")]
        stop = next((i for i, row in enumerate(full) if row["score"] >= -100), len(full) - 1)
        runs = [r for r in targets if r["fixture"] == fixture]
        assert {r["engine"] for r in runs} == {"waffle", "knime", "n8n", "rapidminer"}
        assert all(json.loads(r["output"]) == full[:stop + 1] for r in runs), fixture
    print("Verified examples 12 and 16, the boundary-only WAFFLE history, and all 16 target runs.")


if __name__ == "__main__":
    main()
