# Breadth-first traversal of Zachary’s karate club

We asked Qwen to build a loop that emits one row per nonempty distance layer, starting with the chosen vertex at distance zero. The output contains the distance and a 34-bit mask identifying every vertex at that distance. We used the 34 vertices and 78 undirected edges in NetworkX 3.4.2 and ignored edge weights. [Dataset documentation](https://networkx.org/documentation/stable/reference/generated/networkx.generators.social.karate_club_graph.html) · [Original study](https://doi.org/10.1086/jar.33.4.3629752)

| System | Successful sessions | Submissions that passed public validation | Native reference runs matching every row |
| --- | ---: | ---: | ---: |
| WAFFLE | 0/2 | 0/6 | 3/3 |
| KNIME | 0/2 | 0/6 | 3/3 |

We used the documentation-only condition, the same Qwen3.8-Flash-Next-Uncensored W4A16 checkpoint, seeds 397 and 811, and three submissions per session. Each retry received the diagnostic for its preceding submission. The parent harness specifies decoding and increments the request seed by one at each retry. Both graph interfaces gained the same one-hop neighbor lookup, set union and set difference on named columns. The agent had to keep track of the visited vertices, emit each layer, and stop the loop. The public example started at vertex 0. We reserved vertices 16 and 33 for native scoring.

Six submissions referred to undeclared fields, four supplied expressions where set operations required column names, and two contained invalid JSON. These are the first diagnostics for each submission. No agent submission qualified for execution. Hand-authored controls in WAFFLE and KNIME 5.5.3 produced exactly the rows computed independently by NetworkX for all three roots. The comparison uses every vertex in each layer. A set of the right size with different vertices would fail.

The [records](results) contain the fixed prompts, full responses and repair feedback, edge list, expected rows, reference plans, and native engine outputs. From this directory, run `python verify.py` with NetworkX 3.4.2 to replay all 12 diagnostics and compare the six archived outputs with shortest-path distances.

To repeat the experiment, supply the same model endpoint and the engine dependencies listed in the [parent experiment](../README.md). Use a fresh working directory for RUN.

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
