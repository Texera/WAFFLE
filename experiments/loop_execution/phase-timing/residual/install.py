"""Apply extra timing hooks to the private source copies used by measure.py."""

import shutil
from pathlib import Path


def install(repo, out, py, stage, replace):
    base = Path(__file__).parent
    trace = "org.apache.texera.profile.Phase"
    p = out / "Phase.scala"
    t = replace(
        p.read_text(),
        "Files.writeString(path,",
        'Files.writeString(if (kind.startsWith("r_")) path.resolveSibling("lifecycle.tsv") else path,',
    )
    marker = "  def beginSample"
    method = """  def async[T](kind:String,id:String)(f: => com.twitter.util.Future[T]):com.twitter.util.Future[T]={
    val lo=now
    f.ensure {val hi=now; emit(kind,id,lo,hi)}
  }
"""
    p.write_text(replace(t, marker, method + marker))
    stage(
        "CostBasedScheduleGenerator.scala",
        [
            (
                "def generate(): (Schedule, PhysicalPlan) = {",
                f'def generate(): (Schedule, PhysicalPlan) = {trace}.timed("r_plan","plan") {{',
            )
        ],
    )
    changes = [
        (
            "private def initRegionExecution(): Unit = {",
            f'private def initRegionExecution(): Unit = {trace}.timed("r_allocate",region.id.id.toString) {{',
        ),
        (
            "val terminationFuture = terminateWorkersWithRetry(regionExecution).flatMap",
            f'val terminationFuture = {trace}.async("r_retire",region.id.id.toString)(terminateWorkersWithRetry(regionExecution)).flatMap',
        ),
    ]
    for kind, call in [
        ("mount", "mountRegionRepositories()"),
        ("init", "initExecutors(operatorsToRun, resourceConfig)"),
        ("assign", "assignPortsLogic()"),
        ("connect", "connectChannelsLogic()"),
        ("open", "openOperators(operatorsToRun)"),
        ("start", "startWorkersLogic()"),
    ]:
        changes.append(
            (
                f".flatMap(_ => {call})",
                f'.flatMap(_ => {trace}.async("r_{kind}",region.id.id.toString)({call}))',
            )
        )
    stage("RegionExecutionManager.scala", changes)
    p = repo / "amber/src/test/scala/org/apache/texera/amber/engine/e2e/TestUtils.scala"
    t = p.read_text(encoding="utf8")
    call = "readMaterializedResults(workflow.context.executionId, operatorIds, extract)"
    (out / p.name).write_text(
        replace(
            t, "Try(" + call + ")", f'Try({trace}.timed("r_sink_read","sink")({call}))'
        ),
        encoding="utf8",
    )
    shutil.copy2(base / "trace_python.py", py / "trace_python.py")

    def edit(path, changes):
        p = py / path
        t = p.read_text(encoding="utf8")
        for a, b in changes:
            t = replace(t, a, b)
        p.write_text(t, encoding="utf8")

    # Insert decorators through module imports to preserve @staticmethod ordering.
    def decorate(path, pairs):
        p = py / path
        t = p.read_text(encoding="utf8")
        for sig, deco in pairs:
            t = replace(t, "    def " + sig, "    @" + deco + "\n    def " + sig)
        p.write_text("import trace_python\n" + t, encoding="utf8")

    decorate(
        "core/storage/runnables/input_port_materialization_reader_runnable.py",
        [("run(self)", "trace_python.read_port")],
    )
    decorate(
        "core/runnables/main_loop.py",
        [
            ("_read_loop_input_table(self)", "trace_python.read_loop"),
            ("_process_data_element(self,", "trace_python.tuple_batch"),
        ],
    )
    edit(
        "core/runnables/main_loop.py",
        [
            (
                "        self.process_input_tuple()\n\n        finishing = (",
                "        trace_python.finish_rows(self)\n\n        finishing = (",
            )
        ],
    )
    decorate(
        "core/storage/document_factory.py",
        [("open_document(uri:", "trace_python.read_call")],
    )
    decorate(
        "core/storage/iceberg/iceberg_document.py",
        [
            ("__next__(self)", "trace_python.read_call"),
            ("get(self)", "trace_python.read_call"),
        ],
    )
