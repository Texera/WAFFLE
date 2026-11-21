# Planner scale experiment

The two figures extend the original six graphs with new measurements on the same Windows Ryzen 9 9950X workstation, Texera planner revision and JBR 17.0.14. The compiler expands a group into four physical operators, two for aggregation and two for the hash join. Counts of 44, 68 and 100 refer to compiled physical operators.

| Groups inside / outside | Filters per group | Physical operators | What varies |
| --- | ---: | ---: | --- |
| 4 / 4 | 0 | 36 | Repeat the original balanced graph as a timing reference |
| 5 / 5 | 0 | 44 | Add one branch group on each side |
| 4 / 4 | 4 | 68 | Add 32 native serial filters |
| 4 / 4 | 8 | 100 | Add 64 native serial filters |
| 12 / 12 | 0 | 100 | Continue the original branch-only series, with a time limit |

Each serial filter excludes a distinct value before its group's aggregate and join branches. The compiler's mandatory ports, the two fixed loop-boundary cuts, pruning flags and unit operator estimates match the original experiment. The filter series isolates graph length at fixed branching. Compilation and workflow execution are outside the planning timers. Y's timer includes decomposition and composition.

For the first four rows, the original timing harness runs three warm-up pairs and seven measured X/Y pairs per graph in each of three fresh JVMs, shuffling graph order and alternating method order. All 168 measured plans and their cuts are in `raw/`. Points are pooled medians, and bars span the three JVM medians. The original six graphs retain their published 20 warm-ups and 100 measured pairs per JVM.

The last row uses one fresh forked JVM per planner, three warm-ups of that planner on the 36-operator graph, then one trial with 120 seconds for the search. Each method receives the identical 100-operator graph. The deadline starts after compilation and warm-up. A timeout has no returned cost or completed state count. The separate trial records are in `dense/`. The open marker identifies a completed single trial and the arrow marks a timeout.

The verifier reconstructs each returned plan from its cuts and independently checks its cost. Along a directed path, every mandatory cut forces a new region. With unit weights, one plus the largest number of mandatory cuts along any path is a lower bound on the total cost. In every completed run the chosen plan attains this bound, proving its cost is minimal. The check also compares compiled port inventories, graph sizes and timed sample keys.

At 44 operators with five branch groups per side, X visited 1,024 states and Y visited 64. At four groups per side, adding filters increased the graph from 36 to 100 operators while the state counts stayed at 256 and 32. On that 100-operator graph the median planning times were 1.18 seconds for X and 297 milliseconds for Y. On the separate 100-operator graph with 12 groups per side, Y reached the verified minimum cost of 51 in 36.2 seconds and X reached the 120-second limit.

## Reproduce

Prepare the pinned planning checkout and prerequisites as described in the [planning experiment](../README.md). From this directory, run the following commands with fresh output directories and local paths to the indicated executables.

    python run.py PLANNING_CHECKOUT NEW_RUN --java JAVA17 --sbt-launch SBT_LAUNCH_JAR --python TEXERA_PYTHON
    python run.py PLANNING_CHECKOUT NEW_DENSE_RUN --dense --java JAVA17 --sbt-launch SBT_LAUNCH_JAR --python TEXERA_PYTHON
    python verify.py NEW_RUN --write NEW_SUMMARY.json
    python -c "from pathlib import Path; from verify import verify_dense; verify_dense(Path('NEW_DENSE_RUN'))"

For the published observations, run `python verify.py` and `python charts.py` in this directory. The runner applies the fixture patch to a copy of the pinned source and supplies it to the benchmark build. The planner implementation is unchanged.
