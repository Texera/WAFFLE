"""Extract native observations, check each result, and enumerate the restricted controls."""

import argparse
import csv
from itertools import product
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from prepare import POLICIES, ROOT, SCALES, VISITS, model

ENGINES = ("waffle", "knime", "n8n", "rapidminer")
HERE = Path(__file__).resolve().parent


def csv_rows(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return [{"K": int(k), "score": float(score)} for k, score in csv.reader(stream)]


def observe(engine, folder):
    if engine in ("waffle", "knime"):
        if engine == "waffle" and (folder / "exit-code.txt").read_text().strip() != "0":
            raise ValueError(f"Unsuccessful WAFFLE execution in {folder}")
        if engine == "knime" and not (folder / "observed.json").is_file():
            raise ValueError(f"Missing successful KNIME verification in {folder}")
        visits = csv_rows(folder / "visits.csv")
        return csv_rows(folder / "results.csv"), visits, len(visits)
    if engine == "rapidminer":
        native = json.loads((folder / "out/run.json").read_text())
        if native["version"] != "10.1.000":
            raise ValueError("Unexpected RapidMiner version")
        # Its launcher exports the Body operator's getApplyCount() directly.
        return native["rows"], None, native["iterations"]
    # Recover the raw execution JSON following n8n's CLI startup messages.
    raw = (folder / "engine.log").read_text(encoding="utf-8")
    native, _ = json.JSONDecoder().raw_decode(raw[raw.index("{\n") :])
    if native["status"] != "success":
        raise ValueError(f"Unsuccessful n8n execution in {folder}")
    trace = native["data"]["resultData"]["runData"]
    visits = [
        {k: r["data"]["main"][0][0]["json"][k] for k in ("K", "score")}
        for r in trace["Body"]
    ]
    rows = [r["json"] for r in trace["Result"][0]["data"]["main"][0]]
    return rows, visits, len(visits)


def extract(run, destination):
    destination.mkdir(parents=True, exist_ok=False)
    for name in SCALES:
        inputs = destination / "inputs" / name
        inputs.mkdir(parents=True)
        shutil.copyfile(run / "data" / name / "points.csv", inputs / "points.csv")
    with (destination / "observations.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["engine", "rule", "fixture", "body_calls", "visits", "output"],
        )
        writer.writeheader()
        for engine, policy, fixture in product(ENGINES, POLICIES, SCALES):
            rows, visits, count = observe(engine, run / engine / f"{policy}-{fixture}")
            writer.writerow(
                dict(
                    engine=engine,
                    rule=policy,
                    fixture=fixture,
                    body_calls=count,
                    visits=json.dumps(visits) if visits is not None else "",
                    output=json.dumps(rows),
                )
            )


def reachable(curves, thresholds):
    # A stride >=3 can only visit K=2 within [2,4]. Any upper bound in the
    # domain has the same behavior as one of 2,3,4. One setting serves all inputs.
    traces = set()
    for cap, stride, threshold in product((2, 3, 4), (1, 2, 3), thresholds):
        signature = []
        for curve in curves.values():
            visits = []
            for k in range(2, cap + 1, stride):
                visits.append(k)
                if curve[k] >= threshold:
                    break
            signature.append(tuple(visits))
        traces.add(tuple(signature))
    return traces


def verify(path):
    curves = {
        name: {
            r["K"]: r["score"]
            for r in model.scores(path / "inputs" / name / "points.csv")
        }
        for name in SCALES
    }
    tested = set()
    with (path / "observations.csv").open(newline="", encoding="utf-8") as stream:
        for observation in csv.DictReader(stream):
            engine, rule, fixture = (
                observation[k] for k in ("engine", "rule", "fixture")
            )
            cells = VISITS[rule][list(SCALES).index(fixture)]
            want = [dict(K=k, score=curves[fixture][k]) for k in cells]
            key = engine, rule, fixture
            if key in tested or int(observation["body_calls"]) != len(want):
                raise ValueError(f"Duplicate case or wrong iteration count: {key}")
            if not model.compare(want, json.loads(observation["output"])):
                raise ValueError(f"Unexpected result rows: {key}")
            if engine != "rapidminer" and not model.compare(
                want, json.loads(observation["visits"])
            ):
                raise ValueError(f"Unexpected body visits: {key}")
            tested.add(key)
    if tested != set(product(ENGINES, POLICIES, SCALES)):
        raise ValueError("Some combinations of engine, rule and input are missing")
    # For score >= t, decisions change only when t passes a distinct observed
    # score. A threshold above the largest score also covers disabled stopping.
    thresholds = sorted({v for curve in curves.values() for v in curve.values()})
    never_stop = float("inf")
    fixed = reachable(curves, [never_stop])
    by_score = reachable(curves, [*thresholds, never_stop])
    rows = []
    for rule in POLICIES:
        signature = tuple(tuple(ks) for ks in VISITS[rule])
        rows.append(
            dict(
                rule=rule,
                fixed_range=signature in fixed,
                fixed_range_and_score_threshold=signature in by_score,
                **{
                    engine: sum((engine, rule, f) in tested for f in SCALES)
                    for engine in ENGINES
                },
            )
        )
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--extract",
        action="store_true",
        help="Extract engine outputs from a completed run",
    )
    parser.add_argument("--results", type=Path, default=HERE / "results")
    args = parser.parse_args()
    if args.extract:
        if args.results.exists():
            parser.error("Choose a new directory for extracted evidence")
        args.results.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=args.results.parent) as scratch:
            staged = Path(scratch) / "results"
            extract(ROOT, staged)
            report = verify(staged)
            (staged / "coverage.json").write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )
            staged.rename(args.results)
    else:
        report = verify(args.results)
        if json.loads((args.results / "coverage.json").read_text()) != report:
            raise SystemExit("Saved coverage differs from the recomputed coverage")
    for row in report:
        print(row)
