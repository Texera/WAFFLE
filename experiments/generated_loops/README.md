# Generated loop workflows

WAFFLE's strict compiler produced a physical workflow for **16,104 distinct logical graph topologies**. An in-process driver exercised the prototype's Python loop operators and the generated body code on three inputs per graph. All **48,312 graph/input cases** matched a separate mathematical oracle at every loop visit and every output row.

| Family | Graphs | Graph/input cases | Checked visits | Distinct three-input output profiles |
| --- | ---: | ---: | ---: | ---: |
| Parameter search | 5,368 | 16,104 | 80,520 | 5,367 |
| Data-dependent stopping | 5,368 | 16,104 | 41,177 | 4,455 |
| Grouped aggregation | 5,368 | 16,104 | 48,312 | 4,960 |
| **Total** | **16,104** | **48,312** | **170,009** | **14,782 within families** |

### Where the workflows came from

OpenAI Codex authored a deterministic generator, the nine policy variants, three small integer fixtures, and the checks for this experiment. The generator enumerates a finite grammar. The 16,104 graphs share templates and were generated programmatically in one task. They are synthetic workloads. The JSON operator conventions and coordinator entry point follow the [existing loop experiment](../loop_execution/). The benchmark measures bounded functional correctness; it provides no timing or prevalence estimate.

Every graph has one source, one LoopStart/LoopEnd pair, one reducer and one sorted sink. Inside the loop, one to four consecutive diamonds each fork the data, transform rows along two paths, and reunite them using UNION ALL. A stage chooses one of eleven unordered arm-length pairs. The shorter arm has zero to two transforms and the longer arm has one to four. Each left-arm hop doubles and offsets the feature; each right-arm hop subtracts an offset. The offset depends on stage and hop. Each stage doubles row multiplicity, including duplicate feature values.

The generator enumerates 11 one-stage, 121 two-stage, 1,331 three-stage and 14,641 four-stage bodies. The first 4,680 IDs are preserved. Each of the 11,424 appended bodies contains at least one four-transform arm. It assigns families cyclically and rotates the three policies within each family. Each policy occurs in 1,789 or 1,790 graphs per family. A separate parser reconstructs the ordered sequence of unordered arm lengths from the emitted edges alone. Split and rejoin points fix the stage boundaries, and exchanging the arms leaves the signature unchanged. A second check recursively unfolds the DAG at its source and sorts each node's child signatures. All 16,104 unfolded trees differ, which establishes pairwise non-isomorphism without assuming the grammar. Graphs have 7–33 logical operators and 7–36 explicit data links. The loop feedback is implicit in the block pair.

The mixed fixture has nine rows. The low and high fixtures each have six. Each input includes repeated values; bucket assignment follows input position modulo three. Changing the source values creates a new input case for the same graph. The output-profile count groups identical ordered results across all three inputs within each family. Different topologies can agree on the observed inputs.

### What ran

| Layer | Scope | What was checked |
| --- | --- | --- |
| JVM strict compilation | All 16,104 graphs, mixed input | Texera's `TestUtils.buildWorkflow` strictly compiles each logical graph, requires a physical plan, and records the SHA-256 of the consumed JSON. |
| In-process Python operator execution | All 16,104 graphs × 3 inputs | Uses the pinned LoopStart and LoopEnd implementations for initialization, output, update and continuation, runs the generated source and row UDFs, and round-trips feedback through the prototype's State tuple serializer. The test driver supplies union, sort, state delivery, replay and materialization in memory. |
| Native coordinator and workers | 8 selected mixed-input graphs, 26 sink rows | Amber ran each graph to completion with materialized edges. All eight terminal Sort outputs matched the oracle row for row. |

The initial native sample consisted of the first graph of each family (IDs 0, 1 and 2) plus a three-stage aggregation (ID 59) and the first four-stage graph (ID 399, parameter search). The search returned five candidate/loss pairs with its minimum at 0 (loss 47). Stopping reached quorum at 0 (11 of 18 rows). The two group aggregations returned `[-20, -18, 4]` and `[152, 82, 120]` in bucket order. The four-stage search returned five candidate/loss pairs with its minimum at −2 (loss 52,176). The expanded sample adds a one-stage workflow with a four-transform arm in each family (IDs 4,680–4,682). Their terminal outputs contained five, one and three rows, respectively. The eight native cases are included among the 48,312 operator cases. The native sample covers one fixture on one machine; the full sweep exercises a single loop block with serial diamonds. Distributed scheduling, nested blocks and fault recovery are outside the measurements.

Search scores all five integer candidates from −2 to 2 using absolute, squared or asymmetric absolute loss. Its output is the complete loss curve. Stopping increases the candidate from 0 toward 5 until at least one third, one half or two thirds of expanded rows fall at or below the candidate. Of 16,104 stopping cases, 11,294 reached quorum and 4,810 reached the cap below quorum. Exactly 10,953 stopped on the first visit. Aggregation selects one input bucket per iteration and returns its sum, absolute sum or sum of squares after the branch transformations.

The driver observed **121,697 continuations**, **662,935 union invocations**, **46,985,685 feature-row calls**, and **14,320,278 reducer input rows**. The oracle enumerates entire source-to-reducer paths, composes one affine transform per path, then calculates each score directly. It derives the stopping iteration from a sorted order statistic. It uses neither the loop implementation nor the generated Python code. The comparison checks every visited step, score, sorted sink row, and duplicate contribution with exact integer equality. The verifier also derives operator counts from path multiplicities.

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

The recorded runs took place on November 23–24, 2026 (Pacific), using Windows 11, JBR 17.0.14, Python 3.12.10, pandas 2.2.3, and PyArrow 21.0.0. The first sbt invocation compiled IDs 0 through 1,999 and executed the five native cases. Three subsequent runs compiled IDs 2,000–2,799, 2,800–4,679 and 4,680–16,103. The verifier checks for missing or overlapping compilations and compares all graph hashes. The native adapter uses the existing Amber integration-test harness and reads the PostgreSQL-backed Iceberg results after completion.

Fresh packages contain the expanded workflows, compiler records and engine log. Published digests use SHA-256 over canonical UTF-8 JSON with sorted keys and compact separators. The committed evidence comprises the [operator counts and trace digest](operators.json) and [native compilation digest and sink rows](native.json).

### Matched stopping-threshold comparison

The sensitivity sweep holds the 5,368 stopping graphs fixed. Each graph runs on the low, mixed and high inputs at fractions of one third, one half and two thirds. This gives 48,312 operator runs and 123,574 checked visits. One run per graph/input pair repeats the policy in the original sweep. Each recorded row gives the visits, the number of qualifying rows, the total row count and whether the target was met. Reaching the target on the sixth visit counts as success.

From the artifact root, use the prepared runtime with generated Python protobuf modules and the Python dependencies used by the original operator driver.

```sh
python experiments/generated_loops/stopping_sensitivity.py . "$RUNTIME" sensitivity.csv
python experiments/generated_loops/plot.py
```

The plotting command reads the [recorded measurements](stopping_sensitivity.csv). The two panels distinguish targets met on the first visit from targets met at any visit.
