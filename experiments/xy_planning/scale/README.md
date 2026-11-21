# Planner scale experiment

The two figures extend the original six graphs with new measurements on the same Windows Ryzen 9 9950X workstation, Texera planner revision and JBR 17.0.14. The compiler expands a group into four physical operators, two for aggregation and two for the hash join. Counts of 44, 68 and 100 refer to compiled physical operators.

| Groups inside / outside | Filters per group | Physical operators | Measurement |
| --- | ---: | --- | --- |
| 1 / 1 through 5 / 5 | 0 | 12, 20, 28, 36, 44 | Repeated pairs, equal branch counts |
| 1 / 4 and 4 / 1 | 0 | 24 | Repeated pairs, unequal branch counts |
| 4 / 4 | 0 through 8 | 36 to 100 in steps of 8 | Repeated pairs, fixed branch counts |
| 6 / 6 through 12 / 12 | 0 | 52 to 100 in steps of 8 | One separately capped search per method and size |

Each serial filter excludes a distinct value before its group's aggregate and join branches. The compiler's mandatory ports, the two fixed loop-boundary cuts, pruning flags and unit operator estimates match the original experiment. The filter series isolates graph length at fixed branching. Compilation and workflow execution are outside the planning timers. Y's timer includes decomposition and composition.

The original six workflows retain their 20 warm-up and 100 measured pairs per JVM. The 44-operator branching workflow and all nine filter lengths use three warm-up and seven timed pairs per graph in each of three fresh JVMs. Graph order is shuffled and planner order alternates. The 36-operator graph was independently rerun as the filter-series anchor. The earlier 168 measured plans are in `raw/`. The 252 plans for one, two, three, five, six and seven filters per group are in `intermediate/filter/`.

Each branching workflow from 52 through 100 operators receives one timed search per planner, with a separate JVM for each size and planner. Each JVM first runs three warm-ups on the 36-operator graph. The 120-second limit applies to the search after compilation and warm-up. Each planner receives the same compiled graph. The inventories and outcomes are under `intermediate/branch/` (52–92 operators) and `dense/` (100 operators). A timeout returns neither a plan nor a completed state count.

In each figure the left panel grows a balanced pair of branch groups at a time; isolated crosses mark the two unequal 24-operator layouts. The right panel adds one filter per group at each step. In the timing figure filled points are pooled medians and whiskers span the three JVM medians. Open points and dotted segments identify the single-trial series. Arrows mark the deadline at sizes that timed out. No timing or state count is imputed.

The verifier reconstructs each returned plan from its cuts and independently checks its cost. Along a directed path, every mandatory cut forces a new region. With unit weights, one plus the largest number of mandatory cuts along any path is a lower bound on the total cost. In every completed run the chosen plan attains this bound, proving its cost is minimal. The check also compares compiled port inventories, graph sizes and timed sample keys.

At 44 operators with five branch groups per side, X visited 1,024 states and Y visited 64. At four groups per side, adding filters increased the graph from 36 to 100 operators while the state counts stayed at 256 and 32. On that 100-operator graph the median planning times were 1.18 seconds for X and 297 milliseconds for Y. On the separate 100-operator graph with 12 groups per side, Y reached the verified minimum cost of 51 in 36.2 seconds and X reached the 120-second limit.

## Reproduce

Prepare the pinned planning checkout and prerequisites as described in the [planning experiment](../README.md). From this directory, run the following commands with fresh output directories and local paths to the indicated executables.

    python run.py PLANNING_CHECKOUT NEW_RUN --java JAVA17 --sbt-launch SBT_LAUNCH_JAR --python TEXERA_PYTHON
    python run.py PLANNING_CHECKOUT NEW_DENSE_RUN --dense --java JAVA17 --sbt-launch SBT_LAUNCH_JAR --python TEXERA_PYTHON
    python run.py PLANNING_CHECKOUT NEW_BRANCH_GAPS --branch-gaps --java JAVA17 --sbt-launch SBT_LAUNCH_JAR --python TEXERA_PYTHON
    python run.py PLANNING_CHECKOUT NEW_FILTER_GAPS --filter-gaps --java JAVA17 --sbt-launch SBT_LAUNCH_JAR --python TEXERA_PYTHON
    python verify.py NEW_RUN --write NEW_SUMMARY.json
    python -c "from pathlib import Path; from verify import verify_intermediate; print(verify_intermediate(Path('NEW_BRANCH_GAPS'), Path('NEW_FILTER_GAPS'), Path('NEW_DENSE_RUN')))"

For the published observations, run `python verify.py` and `python charts.py` in this directory. The runner applies the fixture patch to a copy of the pinned source and supplies it to the benchmark build. The planner implementation is unchanged.
