# Planner scale experiment

The two figures extend the original six graphs with new measurements on the same Windows Ryzen 9 9950X workstation, Texera planner revision and JBR 17.0.14. The compiler expands a group into four physical operators, two for aggregation and two for the hash join. Counts of 44, 68 and 100 refer to compiled physical operators.

| Groups inside / outside | Filters per group | Physical operators | Measurement |
| --- | ---: | --- | --- |
| 1 / 1 through 5 / 5 | 0 | 12, 20, 28, 36, 44 | Repeated pairs, equal branch counts |
| 1 / 4 and 4 / 1 | 0 | 24 | Repeated pairs, unequal branch counts |
| 4 / 4 | 0 through 8 | 36 to 100 in steps of 8 | Repeated pairs, fixed branch counts |
| 6 / 6 through 12 / 12 | 0 | 52 to 100 in steps of 8 | One two-minute trial per method and size, followed by longer X trials starting at 68 operators |

Each serial filter excludes a distinct value before its group's aggregate and join branches. The compiler's mandatory ports, the two fixed loop-boundary cuts, pruning flags and unit operator estimates match the original experiment. The filter series isolates graph length at fixed branching. Compilation and workflow execution are outside the planning timers. Y's timer includes decomposition and composition.

The original six workflows retain their 20 warm-up and 100 measured pairs per JVM. The 44-operator branching workflow and all nine filter lengths use three warm-up and seven timed pairs per graph in each of three fresh JVMs. Graph order is shuffled and planner order alternates. The 36-operator graph was independently rerun as the filter-series anchor. The earlier 168 measured plans are in `raw/`. The 252 plans for one, two, three, five, six and seven filters per group are in `intermediate/filter/`.

In the original branching trials from 52 through 100 operators, each planner had 120 seconds per search after compilation and three warm-ups on the 36-operator graph. Every timed search used a fresh JVM and the same compiled graph as the other planner. The inventories and outcomes are under `intermediate/branch/` (52–92 operators) and `dense/` (100 operators).

We retried X with a 900-second limit, starting at its first original timeout (68 operators) and advancing eight operators after each completed search. This sweep stopped at its first timeout (76 operators). The raw retries are in `extended-x/`. We then gave X 3,600 seconds on the 76-operator graph alone, keeping the same benchmark and warm-up. That trial is in `hour-x76/`. At larger sizes the arrows retain the original 120-second limit. A timeout supplies only a lower bound on elapsed time.

In each figure the left panel grows a balanced pair of branch groups at a time; isolated crosses mark the two unequal 24-operator layouts. The right panel adds one filter per group at each step. In the timing figure filled points are pooled medians and whiskers span the three JVM medians. Open points and dotted segments identify the single-trial series. Arrows mark the deadline at sizes that timed out. No timing or state count is imputed.

The verifier reconstructs each returned plan from its cuts and independently checks its cost. Along a directed path, every mandatory cut forces a new region. With unit weights, one plus the largest number of mandatory cuts along any path is a lower bound on the total cost. In every completed run the chosen plan attains this bound, proving its cost is minimal. The check also compares compiled port inventories, graph sizes and timed sample keys.

At 44 operators with five branch groups per side, X visited 1,024 states and Y visited 64. At four groups per side, adding filters increased the graph from 36 to 100 operators while the state counts stayed at 256 and 32. On that 100-operator graph the median planning times were 1.18 seconds for X and 297 milliseconds for Y. On the separate 100-operator graph with 12 groups per side, Y reached the verified minimum cost of 51 in 36.2 seconds and X reached the 120-second limit.

With the 15-minute limit X completed the 68-operator graph in 8.91 minutes, visiting 65,536 states. Y visited 512 states in 1.34 seconds. Both plans attained the verified minimum cost of 35. X timed out at 76 operators after 15 minutes. In the one-hour retry it completed that graph in 2,974.745 seconds and visited 262,144 states. Y took 3.389 seconds and visited 1,024 states on the same graph. Both returned plans with verified minimum cost 39. Sizes above 76 retain their original two-minute trials.

## Reproduce

Prepare the pinned planning checkout and prerequisites as described in the [planning experiment](../README.md). From this directory, run the following commands with fresh output directories and local paths to the indicated executables.

    python run.py PLANNING_CHECKOUT NEW_RUN --java JAVA17 --sbt-launch SBT_LAUNCH_JAR --python TEXERA_PYTHON
    python run.py PLANNING_CHECKOUT NEW_DENSE_RUN --dense --java JAVA17 --sbt-launch SBT_LAUNCH_JAR --python TEXERA_PYTHON
    python run.py PLANNING_CHECKOUT NEW_BRANCH_GAPS --branch-gaps --java JAVA17 --sbt-launch SBT_LAUNCH_JAR --python TEXERA_PYTHON
    python run.py PLANNING_CHECKOUT NEW_FILTER_GAPS --filter-gaps --java JAVA17 --sbt-launch SBT_LAUNCH_JAR --python TEXERA_PYTHON
    python run.py PLANNING_CHECKOUT NEW_EXTENDED_X --extend-x 900 --java JAVA17 --sbt-launch SBT_LAUNCH_JAR --python TEXERA_PYTHON
    python run.py PLANNING_CHECKOUT NEW_X76 --extend-x 3600 --operators 76 --java JAVA17 --sbt-launch SBT_LAUNCH_JAR --python TEXERA_PYTHON
    python verify.py NEW_RUN --write NEW_SUMMARY.json
    python verify.py NEW_RUN --branches NEW_BRANCH_GAPS --filters NEW_FILTER_GAPS --dense NEW_DENSE_RUN --extended NEW_EXTENDED_X --single-x NEW_X76 --write-intermediate NEW_INTERMEDIATE.json

For the published observations, run `python verify.py` and `python charts.py` in this directory. The runner applies the fixture patch to a copy of the pinned source and supplies it to the benchmark build. The planner implementation is unchanged.
