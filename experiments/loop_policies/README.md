# Which K-means loop rules can one workflow express?

The [comparison without separate script nodes](native_controls/README.md) reports the native operators used for the same four rules in Table 2 of the paper.

We tested four rules for choosing the next number of clusters, K. Every rule starts at K=2, stops before K would exceed 4, and retains the score of the last K tested. The body runs Lloyd's algorithm on 16 points and reports the negative sum of squared distances to the nearest center. A higher score indicates a better fit. We scaled the same 16 points by 0.1, 0.7, 1 and 10 to exercise different decisions with the same rule. These are four constructed cases with known answers.

| Rule | Decision after each score |
| --- | --- |
| Fixed sweep | Increase K by one. |
| Score target | Stop when the score reaches −100. Otherwise increase K by one. |
| Adaptive step | Stop at −100. If the score is below −250, double K. Otherwise increase K by one. |
| Improvement since the previous K | After the first score, stop if the improvement over the previous score is below 150. Otherwise increase K by one. |

## Results

We fixed the expected sequence of K values for each case before execution. Each workflow ran its own K-means body. For every run we checked the actual body invocation count and every output pair (K, score) against the expected sequence and an independent NumPy score calculation. For WAFFLE, KNIME and n8n we also checked K and score at each body invocation. RapidMiner Studio Core reported the body's execution count and returned its collected rows.

| Controls available to the workflow author | Rules reproduced on all four inputs |
| --- | ---: |
| Fixed range with a constant stride and upper bound | 1/4 |
| Same range plus a stop threshold on the current score | 2/4 |
| WAFFLE's programmable loop fields | 4/4 |

The first two rows are exhaustive checks on the measured score curves. For each rule one setting must work across all four inputs. The checker enumerates every distinct range starting at 2 and ending at or before 4. For early stopping, it tries each distinct score as a threshold, plus a threshold above all scores. All thresholds between two consecutive scores make the same decisions on these inputs. The fixed-range family can express the sweep. Adding a threshold also expresses stopping at a target. One constant stride cannot both visit K=3 on the near-target input and skip from K=2 to K=4 on the far-below-target input. One current-score threshold also cannot reproduce the rule that compares successive scores across all four inputs.

| Executed implementation | Verified input/rule combinations | Where this implementation expresses the policy |
| --- | ---: | --- |
| WAFFLE | 16/16 | Python fields of LoopStart and LoopEnd |
| KNIME 5.5.3 | 16/16 | Java Snippet with flow variables, Counting Loop Start, and Variable Condition Loop End |
| n8n 2.48.7 | 16/16 | JavaScript Code node and an If node with a feedback edge |
| RapidMiner Studio Core 10.1.0 | 16/16 | Groovy script, process macros, and Loop Until |

Within each tested system all four rules reuse the same graph connections and clustering calculation. In WAFFLE the target rule changes the continuation condition. The adaptive rule also changes the update expression. For the improvement rule, the loop saves the previous score. The KNIME, n8n, and RapidMiner workflows use a separate node for the update so that the clustering code can be reused. These are working implementations. The experiment measures rule coverage on these inputs. It does not measure authoring time or minimal edits over all possible implementations.

The [engine observations](results/observations.csv) include the output scores and body invocation counts. The [coverage table](results/coverage.json) gives the result for each rule.

## Verify or reproduce

From this directory, Python 3.12 with NumPy can recheck the saved evidence:

    python evidence.py

For fresh runs, set `WAFFLE_POLICY_RUN` to a new absolute directory and `KNIME_HOME` to the KNIME 5.5.3 installation. The KNIME launcher used here is for Windows. For WAFFLE use the pinned prototype and the [native study harness](../user_study/) with its PostgreSQL, Python, JDK and sbt prerequisites. Use the same K-means body as the study. For n8n and RapidMiner install Docker and build the RapidMiner runner from [the case study](../case_study/rapidminer/).

    python prepare.py
    python knime_workflows.py
    docker build -t waffle-rapidminer:10.1.0 ../case_study/rapidminer
    python container_workflows.py n8n
    python container_workflows.py rapidminer

Run the following in PowerShell with the four tool and checkout paths set for your machine:

    python ../user_study/run_waffle.py --package $env:WAFFLE_POLICY_RUN --repo $env:TEXERA_REPO --python $env:UDF_PYTHON_PATH --java $env:WAFFLE_JAVA --sbt-launch $env:SBT_LAUNCH
    python evidence.py --extract --results "$env:WAFFLE_POLICY_RUN/verified"
