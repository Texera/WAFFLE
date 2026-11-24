# Generated loop workflows

WAFFLE's strict compiler produced a physical workflow for **2,000 distinct logical graph topologies**. An in-process driver exercised the prototype's Python loop operators and the generated body code on three inputs per graph. All **6,000 graph/input cases** matched a separate mathematical oracle at every loop visit and every output row.

| Family | Graphs | Graph/input cases | Checked visits | Distinct three-input output profiles |
| --- | ---: | ---: | ---: | ---: |
| Parameter search | 667 | 2,001 | 10,005 | 667 |
| Data-dependent stopping | 667 | 2,001 | 5,395 | 610 |
| Grouped aggregation | 666 | 1,998 | 5,994 | 640 |
| **Total** | **2,000** | **6,000** | **21,394** | **1,917 within families** |

### Where the workflows came from

OpenAI Codex authored a deterministic generator, the nine policy variants, three small integer fixtures, and the checks for this experiment. The generator enumerates a finite grammar. The 2,000 graphs share templates and were generated programmatically in one task. They are synthetic workloads. The JSON operator conventions and coordinator entry point follow the [existing loop experiment](../loop_execution/). The benchmark measures bounded functional correctness; it provides no timing or prevalence estimate.

Every graph has one source, one LoopStart/LoopEnd pair, one reducer and one sorted sink. Inside the loop, one to four consecutive diamonds each fork the data, transform rows along two paths, and reunite them using UNION ALL. A stage chooses one of seven unordered arm-length pairs, from a bypass plus one transform to two arms of length two. Each left-arm hop doubles and offsets the feature; each right-arm hop subtracts an offset. The offset depends on stage and hop. Each stage doubles row multiplicity, including duplicate feature values.

The generator enumerates 7 one-stage, 49 two-stage, and 343 three-stage bodies. From 2,401 four-stage candidates, it takes the 1,601 with the smallest SHA-256 hashes of their ordered arm-length pairs, before examining outputs. It assigns families cyclically and rotates the three policies within each family. Each policy occurs in 222 or 223 graphs per family. A separate parser reconstructs the ordered sequence of unordered arm lengths from the emitted edges alone. Split and rejoin points fix the stage boundaries, and exchanging the arms leaves the signature unchanged. A second check recursively unfolds the DAG at its source and sorts each node's child signatures. All 2,000 unfolded trees differ, which establishes pairwise non-isomorphism without assuming the grammar. Graphs have 7–25 logical operators and 7–28 explicit data links. The loop feedback is implicit in the block pair.

The mixed fixture has nine rows. The low and high fixtures each have six. Each input includes repeated values; bucket assignment follows input position modulo three. Changing the source values creates a new input case for the same graph. The output-profile count groups identical ordered results across all three inputs within each family. Different topologies can agree on the observed inputs.

### What ran

| Layer | Scope | What was checked |
| --- | --- | --- |
| JVM strict compilation | All 2,000 graphs, mixed input | Texera's `TestUtils.buildWorkflow` strictly compiles each logical graph, requires a physical plan, and records the SHA-256 of the consumed JSON. |
| In-process Python operator execution | All 2,000 graphs × 3 inputs | Uses the pinned LoopStart and LoopEnd implementations for initialization, output, update and continuation, runs the generated source and row UDFs, and round-trips feedback through the prototype's State tuple serializer. The test driver supplies union, sort, state delivery, replay and materialization in memory. |
| Native coordinator and workers | 5 selected mixed-input graphs, 17 sink rows | Amber ran each graph to completion with materialized edges. All five terminal Sort outputs matched the oracle row for row. |

The native sample consisted of the first graph of each family (IDs 0, 1 and 2) plus a three-stage aggregation (ID 59) and the first four-stage graph (ID 399, parameter search). The search returned five candidate/loss pairs with its minimum at 0 (loss 47). Stopping reached quorum at 0 (11 of 18 rows). The two group aggregations returned `[-20, -18, 4]` and `[152, 82, 120]` in bucket order. The four-stage search returned five candidate/loss pairs with its minimum at −2 (loss 52,176). These five cases are already included among the 6,000 operator cases. The native sample covers one fixture on one machine; the full sweep exercises a single loop block with serial diamonds. Distributed scheduling, nested blocks and fault recovery are outside the measurements.

Search scores all five integer candidates from −2 to 2 using absolute, squared or asymmetric absolute loss. Its output is the complete loss curve. Stopping increases the candidate from 0 toward 5 until at least one third, one half or two thirds of expanded rows fall at or below the candidate. Of 2,001 stopping cases, 1,347 reached quorum and 654 reached the cap below quorum. Exactly 1,306 stopped on the first visit. Aggregation selects one input bucket per iteration and returns its sum, absolute sum or sum of squares after the branch transformations.

The driver observed **15,394 continuations**, **80,607 union invocations**, **4,257,501 feature-row calls**, and **1,693,182 reducer input rows**. The oracle enumerates entire source-to-reducer paths, composes one affine transform per path, then calculates each score directly. It derives the stopping iteration from a sorted order statistic. It uses neither the loop implementation nor the generated Python code. The comparison checks every visited step, score, sorted sink row, and duplicate contribution with exact integer equality. The verifier also derives operator counts from path multiplicities.

### Verify or reproduce

From this directory, Python 3.12 alone rechecks the saved aggregates, digests, topology counts and native output rows. The tests include relabeling, a removed link, a missing native row and a changed visit count.

```sh
python -m unittest -v test_generated
python verify.py
```

For fresh executions, build the pinned runtime using the repository's [engine preparation instructions](../../README.md#run-new-measurements). Its runtime tree is `7cb877ac9ebdc8d829ba59b1fb1e20a870e4a344`. For the native run, follow the [schema and storage setup](../loop_execution/README.md) and use a Texera Python environment, JDK 17, and an sbt launcher. On Windows put Git Bash's bin directory on PATH for the sbt build. Set `RUNTIME` to the prepared checkout, `PACKAGE` to a new scratch path, and `SBT_LAUNCH` to the launcher JAR. Commands below use shell variable syntax.

```sh
python evaluate.py --repo "$RUNTIME"
python corpus.py "$PACKAGE"
python native.py "$PACKAGE" --repo "$RUNTIME" --sbt-launch "$SBT_LAUNCH"
python verify.py --capture "$PACKAGE"
```

The recorded runs took place on November 23, 2026 (Pacific), using Windows 11, JBR 17.0.14, Python 3.12.10, pandas 2.2.3, and PyArrow 21.0.0. One sbt invocation compiled all 2,000 graphs and ran all five native cases successfully. The native adapter uses the existing Amber integration-test harness and reads the PostgreSQL-backed Iceberg results after completion.

Fresh packages contain the expanded workflows, compiler records and engine log. Published digests use SHA-256 over canonical UTF-8 JSON with sorted keys and compact separators. The committed evidence comprises the [operator counts and trace digest](operators.json) and [native compilation digest and sink rows](native.json).

### Matched stopping-threshold comparison

The sensitivity sweep holds the 667 stopping graphs fixed. Each graph runs on the low, mixed and high inputs at fractions of one third, one half and two thirds. This gives 6,003 operator runs and 16,110 checked visits. One run per graph/input pair repeats the policy in the original sweep. Each recorded row gives the visits, the number of qualifying rows, the total row count and whether the target was met. Reaching the target on the sixth visit counts as success.

From the artifact root, use the prepared runtime with generated Python protobuf modules and the Python dependencies used by the original operator driver.

```sh
python experiments/generated_loops/stopping_sensitivity.py . "$RUNTIME" sensitivity.csv
python experiments/generated_loops/plot.py
```

The plotting command reads the [recorded measurements](stopping_sensitivity.csv). The two panels distinguish targets met on the first visit from targets met at any visit.
