# Coverage-free timing of one materialized loop iteration

This experiment repeats the 20,000-point, one-candidate comparison in [large-input](../large-input/). The input bytes, K=2, independent scikit-learn oracle, two workflows, alternating order, and one warm-up plus five measured pairs match the original protocol. Compilation, fixture setup and JVM startup are outside the per-workflow timer. All twelve executions share one JVM and start fresh Python workers. The classpath uses the compiled project classes directly. The launcher rejects JaCoCo entries and compiled project classes containing coverage probes and removes inherited JVM launch options.

Across five measured pairs, the median paired difference in total latency was 12.76 s. The median paired difference outside both measured phases was 8.28 s.

The [follow-up trace](residual/) measures table reads and replay, tuple processing, and worker scheduling within that remaining interval.

| Median time per workflow (s) | LoopBlock (5 workers) | Explicit copies (3 workers) |
| --- | ---: | ---: |
| Total execution | 30.79 | 17.94 |
| Python worker startup | 8.69 | 5.27 |
| Output-table materialization | 2.47 | 1.39 |
| Time outside both phases | 19.41 | 11.12 |

## What the timers cover

- **Workflow latency** goes from native region planning through sink-result retrieval.
- **Python startup** starts immediately before the JVM launches a Python process and ends when the JVM receives its Arrow Flight handshake. User operator execution falls outside this interval.
- **Output-table materialization** includes JVM catalog/table creation, Python setup of the result and control-state writers, and nonempty buffer flushes (serialization, data-file write, and commit). The hooks cover both Python and JVM flushes. Data reads, downstream replay, and time a writer waits for more rows are outside this measure.
- Each phase is the **union of its time intervals** within one execution, measured on the same machine. A worker starting while a table is created counts toward both phase totals, once in each. The CSV also gives the overlap and time spent outside both phases. Reported medians are calculated separately for the five measured runs of each strategy. The difference between two medians can differ from the median paired difference.
- The two benchmark campaigns took place at different times. The coverage-free measurements give a fresh comparison of the two workflow representations. Differences from historical latency cannot isolate the cost of JaCoCo probes.

## Evidence and reproduction

The [capture](capture/) contains the per-execution oracle outputs, assigned sample order, raw phase intervals, class-scan receipt, and computed statistics. The [per-run CSV](capture/phase-times.csv) includes both warm-ups, flagged and excluded from the medians. The original [input CSV](../large-input/points-20000.csv) has the digest recorded in the receipt.

From this directory, run `python analyze_phases.py capture` to recheck the events and regenerate the CSV and summary. To capture new data, prepare the runtime source and database environment as described in the [parent README](../README.md), including the generated DAO classes, the Python worker dependencies and a running Iceberg catalog. Use JDK 17, Scala 2.13.18, the prior single-thread settings, and the sbt export at `amber/target/streams/test/fullClasspath/_global/streams/export` pointing at ordinary compiled classes. On Windows run:

```text
python measure.py <runtime-checkout> <artifact-root> --python <venv-python.exe> --java-home <jdk17> --compiler <scala-compiler-2.13.18.jar> --run <fresh-output-dir>
python analyze_phases.py <fresh-output-dir>
```

The launcher compiles a small set of instrumented source copies against the existing classpath and prepends the resulting classes; the measurement hooks are the only engine changes. It runs the original ScalaTest suite with a copy of the Python worker source. All working files and logs go under the supplied output directory.
