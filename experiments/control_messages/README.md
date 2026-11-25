# Control messages at a merge

## Scoped bindings in Figure 23

Two branches publish the same name and value, different names, or conflicting values. Each pair is tried in both branch layouts. The observer counts callbacks for the tested names and returns its visible bindings and data row count. The common `seed` travels before the branch publications and is excluded from the callback count. For a conflict, the harness records the merge worker's error from the coordinator and ends the run. A timeout, an error from another operator, or a completed conflicting workflow fails the check. A seventh workflow publishes equal K values on both branches for two iterations, changing K from 2 to 3 between iterations.

The [full workflow files and results](scoped_results/) and [controlled receiver driver](scoped_orders.py) use the additional worker patch pinned as `runtime-scoped`. The driver sends frames to two registered input channels on fresh native workers. It records each callback, the state handed to the output manager, the visible map after each delivery, and any error. It covers the six paired orders, the three FIFO orders in the paper's branching example, nesting, a partial duplicate, and a conflict in a mixed frame. The Figure 23 baseline uses the original runtime. Its raw receiver observations are preserved alongside the scoped observations.

Prepare a separate engine with `python tools/prepare_engine.py runtime-scoped work/scoped-runtime` from the repository root. Configure it as described in [loop execution](../loop_execution/README.md). From this experiment directory run:

```sh
python prepare_scoped.py RUN
python ../loop_execution/run_native.py RUN --repo /path/to/scoped-runtime --scoped-merge
python scoped_orders.py --repo /path/to/scoped-runtime RUN/receiver.json
python scoped_orders.py --original --repo /path/to/original-runtime RUN/receiver-original.json
python verify_scoped.py RUN
python plot_scoped.py merge.pdf --results RUN
```

To check the archived results, run `python verify_scoped.py`. The earlier branch-width sweep below and the multiworker binding study use the original runtime pinned as `runtime`.

## Earlier message-ID experiment

This historical experiment measures duplicate message IDs on the original runtime (`a6e394bae138738c2e0aaa03a5bb7f8ec83c6ac6`, tree `7cb877ac9ebdc8d829ba59b1fb1e20a870e4a344`). The branch-count sweep follows the diamond workflow used by Ni and Li for [on-demand state retrieval](https://doi.org/10.1145/3736733.3736743).

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

The multiworker experiment runs a two-iteration loop with K=2 and then K=3. Each iteration supplies the integers 0 through 4095 to a native Filter with predicate x >= $K. The Filter uses 1, 2, 4, 8, 16, or 32 workers, with three complete workflow runs per count. All workers run on one machine, and all edges are materialized. A single upstream LoopStart supplies the common value on the data edge.

The harness compiles the ordinary Filter graph and verifies that its descriptor references K. It then sets the Filter's worker count and installs an observing subclass of the native Filter executor. The subclass reads the inherited descriptor at entry to the first tuple callback and delegates filtering to the original implementation. The engine's normal ExecFactory and DataProcessor perform binding. Each observation contains the real worker index, worker count, received K, bound property and first tuple. Other operators keep the ordinary generated workflow configuration.

The original [12 runs](binding_results/) contain 90 first-tuple observations. The [six additional runs](binding_wide_results/) contain 96 observations at 16 workers and 192 at 32 workers. All 378 bindings matched the expected K, and each run returned the expected 8,187 pairs of K and x. Both batches use the same workflow, native test harness, runtime tree, and inputs. The saved records include all first-tuple observations and all filtered output rows. The checker requires every worker index in both iterations and every expected output row, retaining duplicate counts. The number of machines and competing updates from multiple branches are separate experimental dimensions.

```sh
python prepare_binding.py BINDING_RUN
python ../loop_execution/run_native.py BINDING_RUN --repo /path/to/runtime --binding
python verify_binding.py BINDING_RUN
python prepare_binding.py WIDE_RUN --wide
python ../loop_execution/run_native.py WIDE_RUN --repo /path/to/runtime --binding
python verify_binding.py WIDE_RUN --wide
```

Use `python verify_binding.py` and `python test_verify_binding.py` to check the saved binding records and the checker's rejection of incomplete or incorrect evidence. The setup and native runner options above also apply.
