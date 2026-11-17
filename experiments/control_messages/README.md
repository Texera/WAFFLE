# Control messages at a merge

This experiment tests §5.2 on the runtime tree pinned in the public WAFFLE artifact (`a6e394bae138738c2e0aaa03a5bb7f8ec83c6ac6`, tree `7cb877ac9ebdc8d829ba59b1fb1e20a870e4a344`). The branch-count sweep follows the diamond workflow used by Ni and Li for [on-demand state retrieval](https://doi.org/10.1145/3736733.3736743). Here the outcome is the value retained at a merge.

**Full workflows.** The native compiler and execution service run eight one-iteration workflows with one worker per operator and materialized edges. LoopStart sends one publication of K=2 and one data row along 1, 2, 4, or 8 paths to the same merge input port. At each width we run one workflow with only those copies and a second in which the first branch also publishes K=3 after its input ends. The merge counts calls to its control-message handler and returns its final K and input row count. All eight outputs are in `results/native.jsonl`. Each configuration was run once for correctness.

**Controlled arrival order.** A separate driver delivers real StateFrames to the Python worker’s merge handling and records the user callback and registered value. Each branch preserves send order, so the publishing branch's K=2 must precede its K=3. For width w there are w distinct value sequences: 1 through w copies of K=2 precede K=3. The worker sees the same sequence twice. In one trace, copies of the initial publication share an ID. In the other, each copy has a distinct ID, so all reach the callback. K=3 always has a fresh ID. All 30 traces, covering 15 sequences under both policies, are in `results/arrival_orders.csv`. These counts enumerate positions and do not estimate their frequency in production.

## Reproduce

From this experiment directory, run the following with the runtime Python environment. The native harness prerequisites and JVM options are documented in [loop_execution](../loop_execution/README.md). Use a new run directory.

```sh
python prepare.py RUN
python ../loop_execution/run_native.py RUN --repo /path/to/runtime
python arrival_orders.py --repo /path/to/runtime --output RUN/arrival_orders.csv
python verify.py RUN
python plot.py merge-orders.pdf --results RUN
```

For the public native runner, set JAVA_HOME and SBT_LAUNCH or supply its --java and --sbt-launch options. Use `python verify.py` to check the saved results without starting Texera. The full-workflow outputs measure delivery and callbacks at the merge. The controlled traces isolate duplicate handling from the order chosen by the scheduler.
