# Cost of the extra timers on 20,000 tuples

The [original coverage-free run](../) and the [detailed trace](../residual/) reported median paired gaps of 8.28 s and 16.62 s outside Python startup and output writes. Those measurements were taken in separate campaigns. Here the benchmark switches the detailed timers on and off within one JVM to estimate their incremental effect.

## Results

Enabling detailed tracing narrowed the residual gap in five of eight matched blocks and widened it in three. Its median effect on the gap was **−4.41 s**, with individual changes ranging from −9.37 to +3.71 s (mean −3.65 s). The previously observed increase of 8.34 s exceeded the increase in every matched block. All 36 executions, including the four warm-ups, returned the expected K and score.

| LoopBlock minus explicit copies | Detailed timers off | Detailed timers on | Within-block change, on minus off |
| --- | ---: | ---: | ---: |
| Total workflow latency | 21.66 s | 15.63 s | −5.52 s |
| Residual outside startup and writes | 15.13 s | 10.48 s | −4.41 s |

Each table entry is the median of eight block-level quantities, so subtracting the first two columns can differ from the last column. At the individual workflow level, the median paired change in total latency was −0.39 s for the LoopBlock and +0.38 s for explicit copies. The corresponding changes in residual time were −0.06 s and −0.08 s. All runs are retained, including a block in which tracing-on explicit copies took 24.39 s longer than their tracing-off counterpart.

With detailed tracing disabled, the residual gap alone ranged from 8.52 to 21.41 s across blocks. The controlled experiment did not reproduce the historical increase when the extra timers were enabled. The negative median is specific to these eight blocks. The source of the timing difference between the two earlier campaigns remains unknown.

## Design

Each block runs the same K=2 iteration on the same 20,000 points four ways. The two workflows are the materialized LoopBlock and explicit copies. Each runs once with detailed tracing enabled and once with it disabled. One block warms up all four combinations. The eight measured blocks use two four-block balanced Latin squares. Each combination occupies each run position twice and immediately precedes every other combination twice within blocks. The second square takes the four block orders in reverse. A single JVM runs the workflows serially with fresh Python workers. The engine tree, inputs, graphs, worker counts, native result oracle, JaCoCo exclusion and execution-time boundaries match the earlier comparison.

Both settings keep the original startup and output-write timers. Subtracting the union of those intervals from total workflow latency gives the residual used in §7.6. With tracing on, Python also measures reads, iterator advances, batch processing and end-of-input handling. The JVM also times planning, worker lifecycle operations and result retrieval. With tracing off, workers run the original coarse-timer Python source and the JVM bypasses the extra timers. One inexpensive switch remains at the instrumented JVM methods. This design measures the cost of **adding** detailed tracing to the original benchmark.

For each block we compute the loop time minus the explicit-copy time under each setting, then subtract the off gap from the on gap. A positive result means that enabling extra timers made the LoopBlock slower relative to copies. The per-workflow on-minus-off differences show overhead shared by both workflows. All statistics exclude the warm-up block and retain all eight measured blocks. Each median is calculated from its own matched differences.

## Evidence and reproduction

Follow the [parent setup](../README.md). Add `--compare-tracing` to the `measure.py` command and choose a fresh output directory. Run `python analyze.py <output-directory>` from this directory. To reproduce the published results from the archived raw traces, run `python analyze.py capture`.

The [workflow records](capture/per-workflow.csv) include observed strategy, trace setting, block, wall time, covered phases and residual. The [block comparisons](capture/per-block.csv) and [summary](capture/summary.json) retain both gap measures and each workflow's on-minus-off times. The [capture](capture/) also includes all native outputs, phase traces, the fixed execution order and the build receipt. The validator checks each output against the independent score oracle, verifies the balanced order, checks worker counts, and checks that only the tracing-on executions emitted detailed Python and JVM events.
