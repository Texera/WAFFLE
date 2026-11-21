"""Run the scale extension with the pinned planner and the original benchmark timer."""

import argparse
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
    parser.add_argument(
        "--dense", action="store_true", help="Run the separately capped 12/12 graph"
    )
    args = parser.parse_args()
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
    if args.dense:
        java_opts = ", ".join(json.dumps(s) for s in [*jvm, "-Xmx6g"])
        extra_source = (HERE / "DenseXYBenchmark.scala").as_posix()
        entry = ENTRY.replace("NativeScaleXYBenchmark", "DenseXYBenchmark")
        for key in ("forks", "measured_pairs", "warmup_pairs"):
            del metadata[key]
        metadata.update(
            fresh_jvms_per_method=1,
            trials_per_method=1,
            warmup_per_method=3,
            limit_s=120,
        )
        (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        for method in ("Y", "X"):
            folder = out / method
            folder.mkdir()
            commands = [
                setting,
                f'set WorkflowExecutionService / Test / unmanagedSources += file("{extra_source}")',
                "set WorkflowExecutionService / Test / run / fork := true",
                f"set WorkflowExecutionService / Test / run / javaOptions ++= Seq({java_opts})",
                f"WorkflowExecutionService/Test/runMain {entry} {folder.as_posix()} {method}",
            ]
            with (folder / "run.log").open("w", encoding="utf-8") as log:
                subprocess.run(
                    [*sbt, *commands],
                    cwd=repo,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                )
            if not (folder / "outcome.csv").is_file():
                raise RuntimeError(f"No outcome for {method}")
        return
    for fork in range(metadata["forks"]):
        folder = out / f"fork-{fork}"
        folder.mkdir()
        command = (
            f"WorkflowExecutionService/Test/runMain {ENTRY} {folder.as_posix()} "
            f"{metadata['measured_pairs']} {metadata['warmup_pairs']} {fork}"
        )
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
