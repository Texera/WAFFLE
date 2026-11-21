# Loop rules without separate script nodes

Four rules run on four measured K-means score tables in each of four systems. The experiment isolates loop control by replaying the scores from the [full K-means runs](../results/observations.csv). All 64 native workflows produced the prescribed ordered pairs of K and score. Each system could use expressions in its ordinary operator fields. Each loop ran on its own engine.

| System | Rules | Extra native node types used to implement the rule |
| --- | --- | --- |
| WAFFLE | All four | None |
| KNIME 5.5.3 | Sweep, target | None |
| | Adaptive, gain | Math Formula and Row Filter |
| n8n 2.48.7 | Sweep | None |
| | Target, adaptive, gain | Edit Fields |
| RapidMiner Studio Core 10.1.0 | Sweep | None |
| | Target | Filter Examples |
| | Adaptive, gain | Set Macros, Extract Macro, Generate Macro and Filter Examples |

The table describes the workflows tested. A shorter implementation may exist. We omit nodes used only to load or represent the inputs, retrieve a score or collect outputs. A node that also initializes or advances loop state counts. Multiple uses of the same node type count once. In n8n the sweep uses Loop Over Items. The other rules use If with a feedback edge as the loop.

- The **sweep** visits K = 2, 3, 4.
- The **target** rule stops at the first score of at least −100, or after K = 4.
- The **adaptive** rule has the same target. After a score below −250 it doubles K, otherwise it increments K by one. It stops before K exceeds 4.
- The **gain** rule tries the first two values. It continues when the score improves by at least 150 and the next K is at most 4.

For example, the adaptive rule visits 2 and 4 on the third input. The gain rule visits 2 and 3 on the second input. The [64 individual results](observations.csv) include all ordered outputs and the node types in each saved graph.

### Where the rules are expressed

WAFFLE uses the initialization, update and condition fields on Loop Start and Loop End. KNIME's simple cases iterate through the supplied score rows. Its Variable Condition Loop End can test the current score directly. Its adaptive and gain cases use a recursive loop. Math Formula computes state and Row Filter returns a row to the next iteration when the loop should continue. n8n uses Edit Fields to carry updated state on the feedback edge. RapidMiner's fixed Loop supplies an iteration macro. Its Loop Until tests whether Filter Examples returns a stop row. The adaptive and gain workflows also use macros to carry state between iterations.

### Reproduction

From this directory, run `python verify.py` to check the saved data. The verifier checks the native operator inventory against an allowlist and compares each ordered output with the independently calculated K-means scores and the prespecified sequence for its rule and input. Numeric comparisons use relative and absolute tolerances of 1e-9.

To execute fresh workflows, install the [parent experiment prerequisites](../README.md), set `WAFFLE_NATIVE_CONTROLS_RUN` to a new absolute directory, and set `KNIME_HOME` to the KNIME installation. The following PowerShell commands use the same prototype checkout and test harness as the full K-means experiment.

    python inputs.py
    python ../../user_study/run_waffle.py --package $env:WAFFLE_NATIVE_CONTROLS_RUN --repo $env:TEXERA_REPO --python $env:UDF_PYTHON_PATH --java $env:WAFFLE_JAVA --sbt-launch $env:SBT_LAUNCH
    python knime_native.py
    python n8n_native.py
    docker build -t waffle-rapidminer:10.1.0 ../../case_study/rapidminer
    docker build -t waffle-native-controls-rapidminer:10.1 .
    python rapidminer_native.py
    python verify.py --extract

The run directory contains the workflow files and native outputs for each case. RunNative.java reads RapidMiner's result collection and operator execution count after the workflow finishes.
