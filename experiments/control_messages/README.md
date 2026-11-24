# Control messages at a merge

This experiment tests §5.2 on the runtime tree pinned in the public WAFFLE artifact (`a6e394bae138738c2e0aaa03a5bb7f8ec83c6ac6`, tree `7cb877ac9ebdc8d829ba59b1fb1e20a870e4a344`). The branch-count sweep follows the diamond workflow used by Ni and Li for [on-demand state retrieval](https://doi.org/10.1145/3736733.3736743). Here the outcome is the value retained at a merge.

**Full workflows.** The native compiler and execution service run eight one-iteration workflows with one worker per operator and materialized edges. LoopStart sends one publication of K=2 and one data row along 1, 2, 4, or 8 paths to the same merge input port. At each width we run one workflow with only those copies and a second in which the first branch also publishes K=3 after its input ends. The merge counts calls to its control-message handler and returns its final K and input row count. All eight outputs are in `results/native.jsonl`. Each configuration was run once for correctness.

**Controlled arrival order.** A separate driver delivers real StateFrames to the Python worker’s merge handling and records the user callback and registered value. Each branch preserves send order, so the publishing branch's K=2 must precede its K=3. For width w there are w distinct value sequences: 1 through w copies of K=2 precede K=3. The worker sees the same sequence twice. In one trace, copies of the initial publication share an ID. In the other, each copy has a distinct ID, so all reach the callback. K=3 always has a fresh ID. All 2,046 traces, covering 1,023 sequences at widths from 1 to 512 in powers of two under both policies, are in `results/arrival_orders.csv`. These counts enumerate positions and do not estimate their frequency in production.

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

## Binding across workers

The multiworker experiment runs a two-iteration loop with K=2 and then K=3. Each iteration supplies the integers 0 through 4095 to a native Filter with predicate x >= $K. The Filter uses 1, 2, 4, or 8 workers, with three complete workflow runs per count. All workers run on one machine, and all edges are materialized. A single upstream LoopStart supplies the common value on the data edge.

The harness compiles the ordinary Filter graph and verifies that its descriptor references K. It then sets the Filter's worker count and installs an observing subclass of the native Filter executor. The subclass reads the inherited descriptor at entry to the first tuple callback and delegates filtering to the original implementation. The engine's normal ExecFactory and DataProcessor perform binding. Each observation contains the real worker index, worker count, received K, bound property and first tuple. Other operators keep the ordinary generated workflow configuration.

The saved records include all first-tuple observations and all filtered output rows. The checker requires every worker index in both iterations and every expected output row, retaining duplicate counts. The number of machines and competing updates from multiple branches are separate experimental dimensions.

```sh
python prepare_binding.py BINDING_RUN
python ../loop_execution/run_native.py BINDING_RUN --repo /path/to/runtime --binding
python verify_binding.py BINDING_RUN
```

Use `python verify_binding.py` and `python test_verify_binding.py` to check the saved binding records and the checker's rejection of incomplete or incorrect evidence. The setup and native runner options above also apply.
