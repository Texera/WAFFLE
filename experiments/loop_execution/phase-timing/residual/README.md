# Where time goes in the 20,000-point comparison

The previous [native benchmark](../) found an 8.28 s median paired difference outside Python process startup and output-table materialization. This capture repeats the same comparison with additional timers. It uses the same input file, materialized execution mode, one K=2 iteration, loop and explicit-copy graphs, runtime tree, independent score oracle, alternating run order and coverage-free classpath. The JVM runs one warm-up pair followed by five measured pairs. Each workflow starts fresh workers.

## Results

LoopStart takes in the 20,000 points and emits them for the body. The explicit graph sends the points directly to the body. In the **original capture**, a median **8.08 s** outside startup and writes elapsed between completion of LoopStart's writer setup and the end of its last flush (range 8.02–8.55 s). This interval includes all work and waiting in that window. Those timestamps locate the delay but cannot split it by activity. The same window in the more heavily traced run lasted 13.79 s at the median.

Tuple processing contributed the largest extra time in every traced pair. The table uses means of the five paired runs so the differences add up. The totals are rounded after aggregation.

| Wall time outside startup and output writes (s) | LoopBlock | Explicit copies | Paired difference |
| --- | ---: | ---: | ---: |
| Tuple processing alone | 26.84 | 12.59 | +14.24 |
| Table reads and replay alone | 0.76 | 0.18 | +0.58 |
| Planning and worker setup alone | 2.40 | 1.83 | +0.57 |
| Worker retirement alone | 0.16 | 0.09 | +0.07 |
| Two or more traced activities | 0.71 | 0.26 | +0.45 |
| Outside these timers | 0.44 | 0.19 | +0.24 |
| **Total residual** | **31.29** | **15.15** | **+16.15** |

Within LoopStart, mean elapsed time outside the prior phases was 8.01 s handling incoming batches and 5.81 s handling the end-of-input call that emits the points. These worker-level timers include overlaps. Python readers advanced over 60,004 records in the loop graph and 20,001 with copies, including control-state records. The median elapsed time in the Python storage calls was 0.88 s and 0.24 s, respectively. LoopEnd's direct reread of the 20,000 input points took a median 0.35 s, and plan generation took about 3 ms with the loop and 2 ms with copies.

The residual varied from 9.20 to 22.44 s across traced pairs (median 16.62 s). Both strategies ran slower in this campaign. All 12 executions produced the expected K=2 and score of −345545.1404924168. The trace identifies the dominant work in this workload. The original recording supports the LoopStart window, but lacks timers for retroactively assigning exact seconds to each activity.

## How to read the measurements

- The analyzer first removes every interval covered by the original startup or output-materialization timers. It then splits the remaining wall time into disjoint intervals. Each interval belongs to a single category, the overlap of two or more categories, or the untraced remainder. This avoids counting table replay and tuple processing twice when they run concurrently.
- **Read and replay** covers opening and iterating materialized data and control-state tables, framing and queuing replayed rows, reading the loop input table directly at LoopEnd, and retrieving the final sink result. The CSV separately reports the elapsed time inside Python reader calls to open a document, get its iterator and advance it. This last measure sums time across reader threads and includes decoding. It is a diagnostic, separate from the wall-time partition.
- **Tuple processing** covers dispatching an input batch, running its tuple and control handlers, and handling the end-of-input call that can emit an operator's output. It includes in-memory row handling and output buffering. Time already attributed to measured writes is removed. The worker and batch traces permit separate totals for LoopStart and LoopEnd.
- **Scheduling and worker setup** covers plan generation, region allocation and the coordinator's worker setup, including waiting for executor initialization, port assignment, channel connection, opening operators and starting workers. The CSV gives planning time separately. **Worker retirement** measures the termination request through completion. These intervals measure elapsed time.
- Each run's partition adds up to its original residual within the recorded harness-clock offset. Per-run medians describe typical latency. The mean of the five paired differences is additive across the disjoint categories. The median of each component can come from a different pair.

## Reproduction

Use the [parent setup](../README.md) and add `--trace-residual` to the `measure.py` command, with a fresh output directory. From this directory, run `python analyze.py <output-directory>`. To check the published results using the standard Python library, run `python analyze.py capture`. The [run-level CSV](capture/residual-times.csv) includes the two flagged warm-ups, the [interval intersections](capture/residual-overlap.csv) preserve the overlap breakdown, and the [summary](capture/residual-summary.json) contains the per-strategy medians and the paired statistics. The capture also contains the original JVM and Python event intervals, each native output, the sample order and the class-scan receipt.

Run `python compare_window.py ../capture capture` to reconstruct the [LoopStart interval in both captures](capture/loopstart-window.csv) using only the timers present in both.
