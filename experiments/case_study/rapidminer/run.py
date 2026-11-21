"""Build and run all eight RapidMiner processes, retaining every case's outcome."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from build import build, HERE, INPUT
sys.path.insert(0, str(HERE.parent))
from check import compare, expected_rows

IMAGE = "waffle-rapidminer:10.1.0"
COUNTS = {9: 4, 10: 5, 11: 13, 12: 5, 13: 5, 14: 5, 15: 5, 16: 5}


def run_case(n, directory):
    process = directory / f"{n:02}.rmp"
    build(n, process)
    result = {"case": n, "process_sha256": hashlib.sha256(process.read_bytes()).hexdigest()}
    with tempfile.TemporaryDirectory() as out:
        command = ["docker", "run", "--rm", "--network", "none",
                   "-v", f"{process}:/input.rmp:ro", "-v", f"{out}:/out",
                   IMAGE, "/input.rmp", "/out/run.json"]
        run = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace")
        if run.returncode:
            (directory / f"{n:02}-error.log").write_text(run.stderr, encoding="utf-8")
            return dict(result, status="execution error", reason=f"See {n:02}-error.log")
        recorded = json.loads((Path(out) / "run.json").read_text(encoding="utf-8"))
    (directory / f"{n:02}-run.json").write_text(json.dumps(recorded, indent=2), encoding="utf-8")
    result.update(version=recorded["version"], iterations=recorded["iterations"], rows=len(recorded["rows"]))
    original = json.loads((INPUT / f"{n:02}-knime-run.json").read_text(encoding="utf-8"))
    if original["exit_code"] != 0 or not original["exports_present"]:
        return dict(result, status="unverified", reason="KNIME reference run did not complete")
    if result["iterations"] != COUNTS[n]:
        return dict(result, status="mismatch", reason=f"KNIME ran {COUNTS[n]} iterations")
    try:
        compare(expected_rows(INPUT, n), recorded["rows"])
    except AssertionError as error:
        return dict(result, status="mismatch", reason=str(error))
    return dict(result, status="match")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="A new directory for processes and results")
    directory = parser.parse_args().output.resolve()
    subprocess.run(["docker", "build", "-t", IMAGE, str(HERE)], check=True)
    directory.mkdir(parents=True, exist_ok=False)
    outcomes = []
    for n in COUNTS:
        outcome = run_case(n, directory)
        outcomes.append(outcome)
        print(outcome, flush=True)
    (directory / "comparison.json").write_text(json.dumps(outcomes, indent=2), encoding="utf-8")
    sys.exit(int(any(r["status"] != "match" for r in outcomes)))
