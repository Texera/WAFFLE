"""Run the scale extension with the pinned planner and the original benchmark timer."""

import argparse
import csv
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REVISION = "ddc04792511838d06f982ced01641e7d06ce6524"
SOURCE = Path(
    "amber/src/test/scala/org/apache/texera/amber/engine/architecture/scheduling/NativeBranchXYFixtures.scala"
)
ENTRY = "org.apache.texera.amber.engine.architecture.scheduling.NativeScaleXYBenchmark"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--java", required=True, type=Path)
    parser.add_argument("--sbt-launch", required=True, type=Path)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    series = parser.add_mutually_exclusive_group()
    series.add_argument(
        "--extend-x",
        type=int,
        metavar="SECONDS",
        help="Retry X at 68 through 100 operators, stopping at the first timeout",
    )
    series.add_argument(
        "--branch-gaps",
        action="store_true",
        help="Capped trials at 52 to 92 operators in steps of eight",
    )
    series.add_argument(
        "--filter-gaps",
        action="store_true",
        help="Repeated trials at the six intermediate filter counts",
    )
    series.add_argument(
        "--dense", action="store_true", help="Run the separately capped 12/12 graph"
    )
    args = parser.parse_args()
    if args.extend_x is not None and args.extend_x <= 120:
        parser.error("--extend-x must exceed the original 120-second limit")
    repo, out = args.repo.resolve(), args.output.resolve()
    revision = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()
    if revision != REVISION or subprocess.check_output(
        ["git", "diff", "HEAD", "--name-only"], cwd=repo
    ):
        raise ValueError("Prepare the clean pinned planning checkout first")
    out.mkdir(parents=True, exist_ok=False)
    source = out / SOURCE.name
    shutil.copyfile(repo / SOURCE, source)
    subprocess.run(
        ["git", "apply", "--no-index", "--unidiff-zero", str(HERE / "fixture.patch")],
        cwd=out,
        check=True,
    )
    env = dict(
        os.environ, UDF_PYTHON_PATH=str(args.python.resolve()), TEXERA_HOME=str(repo)
    )
    git = Path(shutil.which("git")).resolve()
    if os.name == "nt":
        env["PATH"] = os.pathsep.join(
            [
                str(git.parents[1] / "bin"),
                str(args.python.resolve().parent),
                env["PATH"],
            ]
        )
    jvm = [
        s
        for s in (repo / ".jvmopts").read_text().splitlines()
        if s.strip() and not s.startswith("#")
    ]
    sbt = [
        str(args.java),
        *jvm,
        "-Xmx6g",
        "-Dsbt.supershell=false",
        "-jar",
        str(args.sbt_launch),
    ]
    setting = (
        "set WorkflowExecutionService / Test / unmanagedSources := "
        f'(WorkflowExecutionService / Test / unmanagedSources).value.filterNot(_.getName == "{SOURCE.name}") :+ file("{source.as_posix()}")'
    )
    metadata = dict(
        revision=revision,
        forks=3,
        warmup_pairs=3,
        measured_pairs=7,
        pruning=True,
        java=subprocess.run(
            [str(args.java), "-version"], capture_output=True, text=True, check=True
        ).stderr.strip(),
        platform=platform.platform(),
        cpu=platform.processor(),
    )
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    if args.dense or args.branch_gaps or args.extend_x:
        java_opts = ", ".join(json.dumps(s) for s in [*jvm, "-Xmx6g"])
        extra_source = (HERE / "DenseXYBenchmark.scala").as_posix()
        entry = ENTRY.replace("NativeScaleXYBenchmark", "DenseXYBenchmark")
        for key in ("forks", "measured_pairs", "warmup_pairs"):
            del metadata[key]
        metadata.update(
            fresh_jvms_per_method=1,
            trials_per_method=1,
            warmup_per_method=3,
            limit_s=args.extend_x or 120,
        )
        (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        commands = [
            setting,
            f'set WorkflowExecutionService / Test / unmanagedSources += file("{extra_source}")',
            "set WorkflowExecutionService / Test / run / fork := true",
            f"set WorkflowExecutionService / Test / run / javaOptions ++= Seq({java_opts})",
        ]
        if args.extend_x:
            for groups in range(8, 13):
                folder = out / f"groups-{groups}" / "X"
                folder.mkdir(parents=True)
                command = f"WorkflowExecutionService/Test/runMain {entry} {folder.as_posix()} X {groups} {args.extend_x}"
                with (folder / "run.log").open("w", encoding="utf-8") as log:
                    subprocess.run(
                        [*sbt, *commands, command],
                        cwd=repo,
                        env=env,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        check=True,
                    )
                with (folder / "outcome.csv").open(newline="") as stream:
                    [result] = csv.DictReader(stream)
                print(f"{4 + 8 * groups} operators: {result}", flush=True)
                if result["status"] == "timeout":
                    break
                if result["status"] != "completed":
                    raise ValueError(f"Unexpected status in {folder}")
            return
        groups_to_run = range(6, 12) if args.branch_gaps else (12,)
        folders = []
        for groups in groups_to_run:
            order = ("Y", "X") if groups % 2 == 0 else ("X", "Y")
            for method in order:
                parent = out / f"groups-{groups}" if args.branch_gaps else out
                folder = parent / method
                folder.mkdir(parents=True)
                folders.append(folder)
                commands.append(
                    f"WorkflowExecutionService/Test/runMain {entry} {folder.as_posix()} {method} {groups}"
                )
        with (out / "run.log").open("w", encoding="utf-8") as log:
            subprocess.run(
                [*sbt, *commands],
                cwd=repo,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
        for folder in folders:
            if not (folder / "outcome.csv").is_file():
                raise RuntimeError(f"No outcome in {folder}")
        return
    for fork in range(metadata["forks"]):
        folder = out / f"fork-{fork}"
        folder.mkdir()
        command = (
            f"WorkflowExecutionService/Test/runMain {ENTRY} {folder.as_posix()} "
            f"{metadata['measured_pairs']} {metadata['warmup_pairs']} {fork}"
        )
        if args.filter_gaps:
            command += " filter-gaps"
        with (folder / "run.log").open("w", encoding="utf-8") as log:
            subprocess.run(
                [*sbt, setting, command],
                cwd=repo,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
        print(f"Completed fresh JVM {fork + 1}/3", flush=True)


if __name__ == "__main__":
    main()
