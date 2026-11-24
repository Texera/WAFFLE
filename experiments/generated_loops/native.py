"""Strict-compile the mixed-input corpus and execute four coordinator sentinels."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

from provenance import pinned_runtime


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("package", type=Path)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--sbt-launch", type=Path, required=True)
    p.add_argument("--match", help="optional ScalaTest test name substring")
    args = p.parse_args()
    root, repo = args.package.resolve(), args.repo.resolve()
    pinned_runtime(repo)
    if any((root / n).exists() for n in ("compiled.jsonl", "executed.jsonl", "engine.log")):
        p.error("generate a fresh package")
    env = dict(os.environ, WAFFLE_GENERATED_RUN=str(root), UDF_PYTHON_PATH=sys.executable,
               STORAGE_ICEBERG_CATALOG_TYPE="postgres", TEXERA_HOME=str(repo),
               SCHEDULE_GENERATOR_MAX_CONCURRENT_REGIONS="1")
    env.pop("AMBER_TEST_FILTER", None)
    flags = [s.strip() for s in (repo / ".jvmopts").read_text().splitlines()
             if s.strip() and not s.lstrip().startswith("#")]
    spec = Path(__file__).with_name("GeneratedLoopSpec.scala").resolve().as_posix()
    test = "WorkflowExecutionService/testOnly *GeneratedLoopSpec -- -oD"
    if args.match:
        test += ' -z "' + args.match + '"'
    cmd = ["java", *flags, "-Dsbt.supershell=false", "-jar", str(args.sbt_launch.resolve()),
           "set DAO / jooqGenerate := Seq.empty",
           f'set WorkflowExecutionService / Test / unmanagedSources += file("{spec}")',
           test]
    with (root / "engine.log").open("w") as log:
        code = subprocess.run(cmd, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    (root / "exit-code.txt").write_text(str(code))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
