# Native loop versus explicit body copies

Both variants execute through Texera's compiler, coordinator and Python workers. This measures total workflow latency, including region planning, scheduling, worker startup, materialization and result retrieval. Compilation, fixture setup, cleanup and JVM startup are outside the timer.

## Protocol and evidence

- Runtime source: original revision a6e394bae138738c2e0aaa03a5bb7f8ec83c6ac6, reproduced by the root implementation lock and patch.
- 200 or 2,000 synthetic 2D points; seed 20261114; four Gaussian clusters.
- The first 1, 4 or 8 K values starting at 2; identical scikit-learn KMeans bodies (n_init=10, random_state=0, Lloyd). Output is K and negative inertia.
- Five logical operators for the loop; N+2 for explicit copies. Compare outputs as multisets with duplicates retained.
- One worker per operator, one concurrent region, one BLAS thread; fully materialized edges. Explicit branches run sequentially.
- One warm-up pair and five measured pairs per setting, alternating strategy order. One shared JVM, fresh Python workers, no cache flush or CPU isolation.
- JaCoCo-instrumented Amber JVM classes from the existing sbt test configuration. Probe overhead is included and has not been separately quantified.
- Every output checked against an independent scikit-learn calculation, with absolute/relative tolerance 1e-9. analyze.py requires successful execution, all 72 ordered records and matching input hashes.
- The box plot summarizes the five measured runs per strategy and setting. Each box spans the first and third quartiles, the line marks the median, and whiskers show the minimum and maximum.

The recorded machine used Windows 11 Pro, AMD Ryzen 9 9950X (16 cores), 192 GiB RAM, JBR 17.0.14 and Python 3.12. Python package versions are pinned in the root requirements.txt. Explicit copies were faster in all six settings. This experiment does not isolate control-message overhead or establish a general speed advantage for loops.

A supplemental native run held the candidate count at one and raised the input from 2,000 to 20,000 rows. The twelve runs used one fresh JVM, one warm-up pair and five measured pairs. The median was 50.1 seconds for the loop and 26.1 seconds for explicit copies. The [captured evidence](large-input/) includes the native timings and outputs, fixture, and workflow files with portable input paths. To reproduce it, generate a new package with the additional arguments --counts 20000 --iterations 1 --pairs 5, then run the same native runner and analyzer. To plot both batches, pass --additional-summary experiments/loop_execution/large-input to the plotting command.

The separate [workflow-size sweep](size_sweep.csv) constructs both representations at every candidate count from 1 through 1,024 and at successive doublings through 131,072. It checks every operator and link. At 131,072 candidates the explicit graph contains 131,074 operators and 262,144 links. The loop contains five operators and four links. These are construction measurements.

## Reproduce

Run commands from the repository root. First prepare work/runtime with tools/prepare_engine.py, build it using its own README, and configure its storage services and Python operator environment. Install the root requirements into that Python environment. Set JAVA_HOME to JDK 17. The helpers accept explicit paths and do not alter tracked engine source.

Before execution, generate DAO classes against this checkout's DDL, not a newer running server schema. The helper uses embedded PostgreSQL through Texera's MockTexeraDB and requires the built Test/fullClasspath export plus the named JARs from the build dependency cache:

```sh
python experiments/loop_execution/prepare_schema.py --repo work/runtime --output work/schema --java-home /path/to/jdk17 --jooq-codegen /path/to/jooq-codegen-3.19.36.jar --jooq-meta /path/to/jooq-meta-3.19.36.jar --jaxb /path/to/jakarta.xml.bind-api-4.0.0.jar
python experiments/loop_execution/experiment.py work/execution-run
python experiments/loop_execution/run_native.py work/execution-run --repo work/runtime --python /path/to/texera-python --java /path/to/jdk17/bin/java --sbt-launch /path/to/sbt-launch.jar
python experiments/loop_execution/analyze.py work/execution-run work/execution-summary --plot work/execution-time.pdf
```

On Windows, use the corresponding java.exe and Python Scripts/python.exe paths. SBT_LAUNCH can supply the launcher JAR; JAVA_HOME supplies the default Java executable. --dry-run prints the native launch command without executing or altering the results. The runner disables automatic jOOQ regeneration after the explicit schema preparation.

The tracked results/ directory is immutable captured evidence. Always generate new workflow JSON in a new package: its file inputs must point to the new machine. Prepare/rerun KNIME separately; do not run it concurrently with execution timing.
