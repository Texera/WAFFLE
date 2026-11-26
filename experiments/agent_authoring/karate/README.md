# Breadth-first traversal of Zachary’s karate club

We asked Qwen to build a loop that emits one row per nonempty distance layer, starting with the chosen vertex at distance zero. The output contains the distance and a 34-bit mask identifying every vertex at that distance. We used the 34 vertices and 78 undirected edges in NetworkX 3.4.2 and ignored edge weights. [Dataset documentation](https://networkx.org/documentation/stable/reference/generated/networkx.generators.social.karate_club_graph.html) · [Original study](https://doi.org/10.1086/jar.33.4.3629752)

| Instructions and system | Successful sessions | Submissions evaluated on the public example | Submissions matching the public example |
| --- | ---: | ---: | ---: |
| Original, WAFFLE | 0/2 | 0/6 | 0/6 |
| Original, KNIME | 0/2 | 0/6 | 0/6 |
| Clarified, WAFFLE | 0/2 | 2/6 | 0/6 |
| Clarified, KNIME | 0/2 | 2/6 | 0/6 |
| Format plus output and state, WAFFLE | 1/2 | 1/6 | 1/6 |
| Format plus output and state, KNIME | 0/2 | 0/6 | 0/6 |
| Plus literal limit and loop repetition, WAFFLE | 0/2 | 3/6 | 0/6 |
| Plus literal limit and loop repetition, KNIME | 0/2 | 2/6 | 0/6 |

All four conditions used the same Qwen3.8-Flash-Next-Uncensored W4A16 checkpoint, seeds 397 and 811, and a limit of three submissions per session. Each retry received the diagnostic for its preceding submission. The parent harness specifies decoding and increments the request seed by one at each retry. Both graph interfaces provided the same one-hop neighbor lookup, set union and set difference on named columns. The agent had to keep track of the visited vertices, emit each layer, and stop the loop. The public example started at vertex 0. We reserved vertices 16 and 33 for native scoring.

With the original instructions, six submissions referred to undeclared fields, four supplied expressions where set operations required column names, and two contained invalid JSON. These are the first diagnostics for each submission. Hand-authored controls in WAFFLE and KNIME 5.5.3 produced exactly the rows computed independently by NetworkX for all three roots. Scoring compares every vertex in each layer.

The [clarified prompts and responses](results/clarified) add the same paragraph to both systems. It names the four scratch fields, explains that each set-operation argument must be a bare column name, and spells out the JSON syntax. Four submissions reached the public preview. WAFFLE seed 811 emitted cumulative vertex sets on attempts 2 and 3. KNIME seed 397 emitted just the starting vertex on attempt 3, and seed 811 emitted no rows on attempt 2. No submission in either condition qualified for native scoring on the two held-out roots.

The [third condition](results/state-and-branch) retains the format reminder and adds a task-neutral explanation of output and state. WAFFLE's text describes what the emission expressions read and what the end node carries forward. KNIME's text describes how the collection and feedback inputs each read their own branch. Neither prompt assigns task-specific meanings to fields or supplies a traversal algorithm.

WAFFLE seed 397 passed on attempt 3. The submitted loop emitted the current layer, added it to the visited set, and excluded visited vertices when forming the next layer. Its native outputs matched every vertex at each distance from roots 0, 16, and 33. All other third-condition submissions failed validation. KNIME seed 397 passed a constant where a set operation required a column name. Its next two submissions used the same constant in an expression, exceeding the allowed literal range. All three submissions from KNIME seed 811 reached the 4,096-token limit with incomplete JSON.

The [fourth condition](results/literal-repeat) adds identical text to both third-condition prompts. It specifies the inclusive range from −1,000 to 1,000 for integer literals and explains that the engine runs the same body nodes again each iteration. WAFFLE seed 397 attempt 2 reintroduced the starting vertex at distance two. For seed 811, attempt 2 emitted cumulative sets and attempt 3 emitted empty sets after the starting vertex. KNIME seed 397 attempts 2 and 3 returned no rows. All three KNIME seed 811 submissions were complete 15-node graphs, but failed validation. None of the four sessions qualified for native scoring.

The [records](results) include the fixed prompts, full responses and repair feedback, edge list, expected rows, reference plans, and native outputs. Run `python verify.py` with NetworkX 3.4.2 to replay all 48 attempts and compare archived native outputs with shortest-path distances.

To repeat the experiment, supply the same model endpoint and the engine dependencies listed in the [parent experiment](../README.md). Use a fresh working directory for RUN in each condition. Add `--clarified` for condition two, `--state-and-branch` for condition three, or `--literal-repeat` for condition four to the freeze command.

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
