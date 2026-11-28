import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

here = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument("repo", type=Path)
ap.add_argument("artifact", type=Path)
ap.add_argument("--python", required=True, type=Path)
ap.add_argument("--java-home", required=True, type=Path)
ap.add_argument("--compiler", required=True, type=Path)
ap.add_argument("--run", required=True, type=Path)
args = ap.parse_args()
repo, artifact = args.repo.resolve(), args.artifact.resolve()
out = args.run.resolve()
out.mkdir(parents=True, exist_ok=False)
exp = artifact / "experiments/loop_execution"
rev = subprocess.check_output(["git", "write-tree"], cwd=repo, text=True).strip()
assert rev == "7cb877ac9ebdc8d829ba59b1fb1e20a870e4a344"
assert not subprocess.check_output(["git", "diff", "--name-only"], cwd=repo)
env = os.environ.copy()
for key in ["JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS", "_JAVA_OPTIONS", "CLASSPATH"]:
    env.pop(key, None)
env.update(
    UDF_PYTHON_PATH=str(args.python),
    STORAGE_ICEBERG_CATALOG_TYPE="postgres",
    TEXERA_HOME=str(repo),
    WAFFLE_EXPERIMENT_PACKAGE=str(out / "data"),
    WAFFLE_PHASE_DIR=str(out),
    SCHEDULE_GENERATOR_MAX_CONCURRENT_REGIONS="1",
    OMP_NUM_THREADS="1",
    OPENBLAS_NUM_THREADS="1",
    MKL_NUM_THREADS="1",
)
env["PATH"] = str(args.python.parent) + os.pathsep + env["PATH"]
py = out / "python"
shutil.copytree(
    repo / "amber/src/main/python",
    py,
    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
)
env["WAFFLE_TIMED_PYTHON_SRC"] = str(py)
subprocess.run(
    [
        str(args.python),
        str(exp / "experiment.py"),
        str(out / "data"),
        "--counts",
        "20000",
        "--iterations",
        "1",
        "--pairs",
        "5",
    ],
    env=env,
    check=True,
)
orig = exp / "large-input"
assert (
    hashlib.sha256((out / "data/points-20000.csv").read_bytes()).digest()
    == hashlib.sha256((orig / "points-20000.csv").read_bytes()).digest()
)
manifest = json.loads((out / "data/manifest.json").read_text())
for filename in sorted(orig.glob("n20000-i1-*.json")):
    portable = filename.read_text(encoding="utf8")
    token = "${RUNS}/large-input/points-20000.csv"
    assert portable.count(token) == 1
    actual_path = (out / "data/points-20000.csv").as_posix()
    assert json.loads(portable.replace(token, actual_path)) == json.loads(
        (out / "data" / filename.name).read_text(encoding="utf8")
    )
assert manifest["runs"] == json.loads((orig / "manifest.json").read_text())["runs"]
cp = (
    (repo / "amber/target/streams/test/fullClasspath/_global/streams/export")
    .read_text()
    .strip()
    .split(os.pathsep)
)
cp = [
    x
    for x in cp
    if "org.jacoco" not in x.lower()
    and "org\\jacoco" not in x.lower()
    and "/org/jacoco" not in x.lower()
]
assert not any("jacoco" in x.lower() for x in cp)
probes = [b"$jacocoInit", b"$jacocoData", b"org/jacoco/agent/rt/internal"]
digests = hashlib.sha256()
scanned = 0
for folder in [Path(x) for x in cp if Path(x).is_dir()]:
    for cl in sorted(folder.rglob("*.class")):
        data = cl.read_bytes()
        if any(k in data for k in probes):
            raise RuntimeError(f"Coverage probes: {cl}")
        digests.update(hashlib.sha256(data).digest())
        scanned += 1
classes = out / "classes"
classes.mkdir()
joint = os.pathsep.join([str(classes), *cp])


def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def stage(name, changes):
    if name == "NativeExecutionSpec.scala":
        src = exp / name
    else:
        roots = [
            repo / "amber/src/main/scala",
            repo / "common/workflow-core/src/main/scala",
        ]
        files = [f for r in roots for f in r.rglob(name)]
        assert len(files) == 1, files
        src = files[0]
    t = src.read_text(encoding="utf8")
    for old, new in changes:
        t = replace(t, old, new)
    (out / name).write_text(t, encoding="utf8")


trace = "org.apache.texera.profile.Phase"
stage(
    "PythonWorkflowWorker.scala",
    [
        (
            'pythonSrcDirectory.resolve("texera_run_python_worker.py")',
            'java.nio.file.Paths.get(sys.env("WAFFLE_TIMED_PYTHON_SRC")).resolve("texera_run_python_worker.py")',
        ),
        (
            "    pythonServerProcess = Process(",
            f"    {trace}.launch(workerConfig.workerId.name)\n    pythonServerProcess = Process(",
        ),
    ],
)
stage(
    "PythonProxyServer.scala",
    [
        (
            "        promise.setValue(strPortNumber.toInt)",
            f"        {trace}.ready(actorId.name)\n        promise.setValue(strPortNumber.toInt)",
        )
    ],
)
stage(
    "IcebergUtil.scala",
    [
        (
            "  ): Table = {\n\n    val tableProperties",
            f'  ): Table = {trace}.timed("create", tableNamespace + "." + tableName) {{\n\n    val tableProperties',
        )
    ],
)
stage(
    "IcebergTableWriter.scala",
    [
        (
            "private def flushBuffer(): Unit = {\n    if (buffer.nonEmpty) {",
            f'private def flushBuffer(): Unit = {{\n    if (buffer.nonEmpty) {trace}.timed("jvm_flush", tableNamespace + "." + tableName) {{',
        )
    ],
)
stage(
    "NativeExecutionSpec.scala",
    [
        (
            "        val started=System.nanoTime()",
            f"        {trace}.beginSample(index)\n        val started=System.nanoTime()",
        ),
        (
            "        val elapsed=System.nanoTime()-started",
            f"        val elapsed=System.nanoTime()-started\n        {trace}.endSample(index)",
        ),
    ],
)
shutil.copy2(here / "Phase.scala", out / "Phase.scala")
shutil.copy2(here / "waffle_phase.py", py / "waffle_phase.py")
p = py / "core/architecture/packaging/output_manager.py"
t = p.read_text(encoding="utf8")
p.write_text(
    replace(
        t,
        "    def set_up_port_storage_writer(",
        "    from waffle_phase import timed_setup\n    @timed_setup\n    def set_up_port_storage_writer(",
    ),
    encoding="utf8",
)
p = py / "core/storage/iceberg/iceberg_table_writer.py"
t = p.read_text(encoding="utf8")
p.write_text(
    replace(
        t,
        "    def _flush_buffer(",
        "    from waffle_phase import timed_flush\n    @timed_flush\n    def _flush_buffer(",
    ),
    encoding="utf8",
)
j = args.java_home / "bin/java.exe"


def invoke(name, opts):
    argfile = out / (name + ".args")
    argfile.write_text(
        "\n".join('"' + str(v).replace("\\", "/") + '"' for v in opts), encoding="utf8"
    )
    with (out / (name + ".log")).open("w") as log:
        return subprocess.run(
            [str(j), "@" + str(argfile)],
            cwd=repo,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
        ).returncode


compiler_cp = os.pathsep.join([str(args.compiler), joint])
status = invoke(
    "compiler",
    [
        "-cp",
        compiler_cp,
        "scala.tools.nsc.Main",
        "-classpath",
        joint,
        "-d",
        str(classes),
        *sorted(out.glob("*.scala")),
    ],
)
if status:
    raise RuntimeError(
        "scalac failed: " + (out / "compiler.log").read_text(errors="replace")[-1800:]
    )
flags = [
    s.strip()
    for s in (repo / ".jvmopts").read_text().splitlines()
    if s.strip() and not s.strip().startswith("#")
]
prov = dict(
    tree=rev,
    compiled_classes_scanned=scanned,
    class_sha256_aggregate=digests.hexdigest(),
    coverage_probe_matches=0,
    java_flags=flags,
    original_input_sha256=hashlib.sha256(
        (orig / "points-20000.csv").read_bytes()
    ).hexdigest(),
    utc=datetime.now(timezone.utc).isoformat(),
)
(out / "verification.json").write_text(json.dumps(prov, indent=2), encoding="utf8")
status = invoke(
    "native",
    [
        *flags,
        "-Dfile.encoding=UTF-8",
        "-cp",
        joint,
        "org.scalatest.tools.Runner",
        "-oD",
        "-s",
        "org.apache.texera.amber.engine.e2e.NativeExecutionSpec",
    ],
)
(out / "data/exit-code.txt").write_text(str(status))
sys.exit(status)
