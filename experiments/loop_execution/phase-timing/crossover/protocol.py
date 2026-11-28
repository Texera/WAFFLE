"""Switch the extra timers per execution in the same native ScalaTest suite."""

import json

# Balanced Latin square. Each treatment precedes every other one once per square.
ORDERS = ((0, 1, 3, 2), (1, 2, 0, 3), (2, 3, 1, 0), (3, 0, 2, 1))
CELLS = (("loop", False), ("copies", False), ("loop", True), ("copies", True))


def configure(out, manifest, replace):
    templates = {r["strategy"]: r for r in manifest["runs"]}
    samples = []
    # Reverse the square's block order on the second pass. Fix the entire
    # schedule before the JVM starts, independent of any observed timings.
    for block, order in enumerate(((0, 3, 1, 2), *ORDERS, *reversed(ORDERS)), -1):
        for cell in order:
            strategy, trace = CELLS[cell]
            samples.append(
                dict(templates[strategy], pair=block, warmup=block < 0, trace=trace)
            )
    manifest.update(runs=samples, pairs=8)
    (out / "data/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Crossover schedule: {len(samples)} native executions", flush=True)

    def edit(file, replacements):
        p = out / file
        source = p.read_text(encoding="utf8")
        for old, new in replacements:
            source = replace(source, old, new)
        p.write_text(source, encoding="utf8")

    phase = "org.apache.texera.profile.Phase"
    edit(
        "NativeExecutionSpec.scala",
        [
            (
                "      val graph =",
                f'      {phase}.detail = run.get("trace").asBoolean\n      val graph =',
            ),
            ('"sample"->index,', f'"sample"->index,"trace"->{phase}.detail,'),
        ],
    )
    edit(
        "Phase.scala",
        [
            (
                "  private val starts=",
                "  @volatile var detail = false\n  private val starts=",
            ),
            (
                "    val lo=now\n    f.ensure",
                "    if (!detail) return f\n    val lo=now\n    f.ensure",
            ),
            (
                "(f: =>T):T={val lo=now;",
                '(f: =>T):T={if (!detail && kind.startsWith("r_")) return f;val lo=now;',
            ),
        ],
    )
    edit(
        "PythonWorkflowWorker.scala",
        [
            (
                'sys.env("WAFFLE_TIMED_PYTHON_SRC")',
                f'sys.env(if ({phase}.detail) "WAFFLE_TIMED_PYTHON_SRC" else "WAFFLE_COARSE_PYTHON_SRC")',
            ),
        ],
    )
