"""Verify the archived write-once binding sweep against the original protocol."""
import csv
import hashlib
import json
from pathlib import Path

from prepare_binding import REPEATS, ROWS, WIDE_WORKERS, WORKERS
from verify_binding import check


def verify():
    experiment = Path(__file__).resolve().parent
    results = experiment / "binding_scoped_results"
    lock = json.loads((experiment.parents[1] / "implementation.lock.json").read_text())
    provenance = json.loads((results / "provenance.json").read_text())
    if (provenance["scoped_tree"] != lock["runtime-scoped"]["tree"]
            or provenance["jvm_source_tree"] != lock["runtime"]["tree"]
            or provenance["scoped_patch_sha256"] != lock["runtime-scoped"]["patch_sha256"]):
        raise ValueError("Recorded runtimes do not match implementation.lock.json")
    for name, expected in provenance["file_sha256"].items():
        if hashlib.sha256((results / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Archive digest mismatch for {name}")

    summary = []
    for name, baseline, widths in [("standard", "binding_results", WORKERS),
                                    ("wide", "binding_wide_results", WIDE_WORKERS)]:
        batch = results / name
        for filename in ("workflow.json", "manifest.json"):
            if json.loads((batch / filename).read_text()) != json.loads((experiment / baseline / filename).read_text()):
                raise ValueError(f"Changed binding protocol in {name}/{filename}")
        for width, counts in check(batch, widths).items():
            expected_rows = sum(ROWS - k for k in (2, 3)) * REPEATS
            summary.append(dict(filter_workers=width, workflow_runs=REPEATS,
                                expected_first_tuples=2 * REPEATS * width,
                                observed_first_tuples=counts["observations"],
                                matching_first_bindings=counts["matched"],
                                checked_output_rows=expected_rows))
    with (results / "summary.csv").open(newline="") as stream:
        recorded = [{key: int(value) for key, value in row.items()} for row in csv.DictReader(stream)]
    if recorded != summary:
        raise ValueError("Width summary disagrees with native records")
    print(f"Write-once runtime: {sum(s['matching_first_bindings'] for s in summary)} "
          f"first-tuple bindings and {sum(s['checked_output_rows'] for s in summary)} output rows verified.")


if __name__ == "__main__":
    verify()
