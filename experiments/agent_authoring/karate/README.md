# Breadth-first traversal of Zachary’s karate club

We asked Qwen to build a loop that emits one row per nonempty distance layer, starting with the chosen vertex at distance zero. The output contains the distance and a 34-bit mask identifying every vertex at that distance. We used the 34 vertices and 78 undirected edges in NetworkX 3.4.2 and ignored edge weights. [Dataset documentation](https://networkx.org/documentation/stable/reference/generated/networkx.generators.social.karate_club_graph.html) · [Original study](https://doi.org/10.1086/jar.33.4.3629752)

| Instructions and system | Successful sessions | Submissions evaluated on the public example | Submissions matching the public example |
| --- | ---: | ---: | ---: |
| Original, WAFFLE | 0/2 | 0/6 | 0/6 |
| Original, KNIME | 0/2 | 0/6 | 0/6 |
| Clarified, WAFFLE | 0/2 | 2/6 | 0/6 |
| Clarified, KNIME | 0/2 | 2/6 | 0/6 |

We used the documentation-only condition, the same Qwen3.8-Flash-Next-Uncensored W4A16 checkpoint, seeds 397 and 811, and three submissions per session. Each retry received the diagnostic for its preceding submission. The parent harness specifies decoding and increments the request seed by one at each retry. Both graph interfaces gained the same one-hop neighbor lookup, set union and set difference on named columns. The agent had to keep track of the visited vertices, emit each layer, and stop the loop. The public example started at vertex 0. We reserved vertices 16 and 33 for native scoring.

With the original instructions, six submissions referred to undeclared fields, four supplied expressions where set operations required column names, and two contained invalid JSON. These are the first diagnostics for each submission. Hand-authored controls in WAFFLE and KNIME 5.5.3 produced exactly the rows computed independently by NetworkX for all three roots. Scoring compares every vertex in each layer.

The [clarified prompts and responses](results/clarified) add the same paragraph to both systems. It names the four scratch fields, explains that each set-operation argument must be a bare column name, and spells out the JSON syntax. Four submissions reached the public preview. WAFFLE seed 811 emitted cumulative vertex sets on attempts 2 and 3. KNIME seed 397 emitted just the starting vertex on attempt 3, and seed 811 emitted no rows on attempt 2. No submission in either condition qualified for native scoring on the two held-out roots.

The [records](results) include the fixed prompts, full responses and repair feedback, edge list, expected rows, reference plans, and native reference outputs. Run `python verify.py` with NetworkX 3.4.2 to replay all 24 attempts and compare the six archived reference outputs with shortest-path distances.

To repeat the experiment, supply the same model endpoint and the engine dependencies listed in the [parent experiment](../README.md). Use a fresh working directory for RUN in each condition. Add `--clarified` to the freeze command for the second condition.

```text
python run.py freeze RUN
python run.py sessions RUN --endpoint ENDPOINT --key-file KEY_FILE
python run.py prepare RUN --stage controls
python run.py knime RUN --stage controls --runtime KNIME_DIRECTORY
python ../../loop_execution/run_native.py RUN/controls --case-study --repo ENGINE_CHECKOUT --java JAVA --python PYTHON --sbt-launch SBT_LAUNCH_JAR
python run.py score RUN --stage controls
python run.py prepare RUN --stage agent
```

For any accepted agent graphs, run the corresponding engines on RUN/agent, then use `python run.py score RUN --stage agent`. The WAFFLE engine revision was `a6e394bae138738c2e0aaa03a5bb7f8ec83c6ac6`.
