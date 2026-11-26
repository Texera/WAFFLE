# Paired loop-workflow authoring experiment

| Instructions | System | Correct on first submission | Correct within three submissions | Submissions used |
| --- | --- | ---: | ---: | ---: |
| Node documentation | WAFFLE | 6/12 | 10/12 | 18 |
| Node documentation | KNIME | 0/12 | 0/12 | 35 |
| Documentation and worked example | WAFFLE | 5/12 | 6/12 | 22 |
| Documentation and worked example | KNIME | 0/12 | 2/12 | 34 |
| Documentation and wiring diagram | WAFFLE | 8/12 | 8/12 | 16 |
| Documentation and wiring diagram | KNIME | 0/12 | 2/12 | 33 |
| Wiring diagram with emission and update order | WAFFLE | 7/12 | 9/12 | 16 |
| Wiring diagram with emission and update order | KNIME | 0/12 | 2/12 | 36 |
| Timing explanation and graph rule | WAFFLE | 9/12 | 10/12 | 14 |
| Timing explanation and graph rule | KNIME | 0/12 | 0/12 | 36 |
| Fifth prompt repeated | WAFFLE | 7/12 | 8/12 | 18 |
| Graph rule plus loop-end ports and sink | KNIME | 0/12 | 0/12 | 36 |
| WAFFLE initializer and temporary-field rules | WAFFLE | 7/12 | 9/12 | 18 |
| Sixth prompt repeated | KNIME | 1/12 | 1/12 | 34 |
| Output row numbering | WAFFLE | 9/12 | 9/12 | 14 |
| Output row numbering | KNIME | 0/12 | 2/12 | 35 |
| WAFFLE expression strings | WAFFLE | 7/12 | 10/12 | 19 |
| Eighth prompt repeated | KNIME | 0/12 | 1/12 | 36 |
| Ninth prompt repeated | WAFFLE | 10/12 | 10/12 | 14 |
| KNIME feedback flag and filter | KNIME | 0/12 | 1/12 | 35 |
| Tenth prompt repeated | WAFFLE | 7/12 | 10/12 | 16 |
| KNIME filter reads flag setter | KNIME | 0/12 | 0/12 | 36 |
| Eleventh prompt repeated | WAFFLE | 8/12 | 10/12 | 16 |
| KNIME required filter and sink connections | KNIME | 0/12 | 3/12 | 35 |
| Twelfth prompt repeated | WAFFLE | 8/12 | 10/12 | 16 |
| KNIME continue flag and updates after filtering | KNIME | 0/12 | 3/12 | 35 |

All eight successful WAFFLE sessions with the wiring diagram passed on the first submission. Compared with the solved example, both cooldown sessions recovered and both running-sum sessions continued to fail. The two successful KNIME sessions with the diagram solved a recurrence and a running sum. With the solved example, its two successes were on the advance and crossing tasks.

With emission and update order explained, WAFFLE solved the running sum on submission two for seed 397 and submission one for seed 811. KNIME solved it on submission three for both seeds. Compared with wiring alone, both systems lost their recurrence success on seed 397. WAFFLE also needed a second submission for recurrence on seed 811. WAFFLE's two crossing graphs and KNIME's crossing graph for seed 811 passed the public example and failed a held-out input.

With the scratch fields listed, the WAFFLE agent solved the recurrence on submission two for seed 397 and submission one for seed 811. With the earlier-node rule, KNIME seed 397 used preceding-node references in all three submissions. Its first graph named undeclared columns. Its next two fed back the row preceding the update to the second output column. Both WAFFLE crossing graphs passed the public example and failed a held-out input. KNIME lost both of its previous running-sum successes. None of its 12 sessions passed the public example, so the protocol ended them before native held-out scoring.

In the sixth condition, 30 of 36 KNIME submissions had exactly one sink with a direct reference to an earlier loop end, compared with 26 of 36 under the fifth prompt. This check counts the submitted edge even when another node fails validation. No KNIME session passed the public input in either condition. On the running sum, seed 397 put a comparison where the row filter required a column name, and seed 811 read the feedback flag from the row before the flag was set. With identical WAFFLE prompt hashes and seeds, fresh inference produced 7 first-submission and 8 within-budget successes, compared with 9 and 10 in the previous run.

In the seventh condition, the WAFFLE running sum for seed 397 used a string initializer and recurrence for seed 811 saved the sum in the declared field `u`. Both passed on the first submission. Zigzag for seed 811 exhausted its three submissions after passing in the sixth condition. Both WAFFLE crossing sessions passed the public input and failed a held-out input. With identical KNIME instructions and seeds, advance for seed 811 passed all inputs on its first submission. Crossing for the same seed passed the public input on its third submission and failed a held-out input.

With output rows numbered from one, both WAFFLE zigzag sessions passed on their first submission. In condition seven they took three submissions for seed 397 and exhausted the budget for seed 811. Both new graphs added on the first transition. The WAFFLE running sum at seed 811 lost its pass: all three submissions wrapped the two output expressions and the continuation expression in arrays where the interface requires strings. Both WAFFLE crossing sessions again matched the public example and failed a held-out input. KNIME passed running sum on submission three for seed 397 and submission two for seed 811. Its previous advance success at seed 811 did not recur. Neither KNIME zigzag session passed the public example.

In condition nine, 19 of 19 WAFFLE submissions used two plain strings for the EMIT outputs and a plain string for the END continuation test, compared with 11 of 14 in condition eight. Both running-sum sessions initially emitted the input before updating it; their third submissions applied the first update in START and passed all three inputs. Seed 811 recovered its pass, and seed 397 took three submissions after previously passing on its first. Cooldown at seed 397 also required a repair. Both zigzag sessions passed on their first submissions. The two crossing graphs passed the public input and failed a held-out input. With the identical eighth-condition KNIME prompts, running sum for seed 397 passed on the third submission and seed 811 lost its pass. The formatting counts are per submitted graph; task success is per session.

In condition ten, the KNIME loop end took feedback directly from a filter in 20 of 35 submitted graphs, compared with 9 of 36 in condition nine. This count checks the connection even when the graph has errors elsewhere. It does not test whether the filter receives all state updates. Recurrence for seed 811 passed on submission two. Running sum for seed 811 stopped after three rows but kept the old sum on its feedback path in all three attempts. For seed 397, the final running-sum graph read the flag before the assignment and stopped after its first row. KNIME passed one session in each condition, on different tasks. With the same WAFFLE prompts and seeds, first-submission passes rose from 7 to 10. The same 10 sessions passed within three submissions.

In condition eleven, the KNIME feedback filter read directly from the node assigning its tested flag and fed the loop end's feedback port in 14 of 36 submissions, compared with 17 of 35 in condition ten. This count measures both connections even if the graph is invalid elsewhere. No KNIME session passed the public example, so none qualified for held-out execution. The last running-sum submission for seed 397 contained a filter, but its input preceded the flag assignment and the loop end read the assignment directly. With unchanged prompts, WAFFLE solved the same ten sessions within three submissions. Running sum and recurrence on seed 811 and cooldown on seed 397 each required a second submission.

In condition twelve, KNIME passed three sessions on both held-out inputs: cooldown (seed 397, submission two), running sum (811, submission three), and zigzag (811, submission three). All three passed the public example as well. The feedback input read directly from a filter and the sink read directly from the loop end in 15 of 35 submitted graphs, compared with 19 of 36 in condition eleven. This counts the two connections even when a graph contains errors elsewhere. Running sum and cooldown used both connections. The successful zigzag graph placed its filter before the state updates and returned the updated row to the feedback input. The primary score measures output sequences. With the same prompts and seeds, WAFFLE again solved the same ten sessions within three attempts and solved eight on the first attempt, compared with seven previously.

In condition thirteen, KNIME passed three sessions on the public example and both held-out inputs: advance (seed 811, submission three), crossing (397, submission two), and cooldown (811, submission three). All three task–seed pairs differed from the three that passed in condition twelve. Advance returned the filtered row directly to the feedback port. Crossing updated x after filtering. Cooldown updated x and its counter. Both sent the updated row to the feedback port. The WAFFLE rerun passed the same ten sessions within budget and again passed eight on the first submission.

Reference workflows produced every expected trace in both engines (six tasks × two held-out inputs × two systems). A session that passed the public input stopped receiving repair feedback, even when its graph subsequently failed on a hidden input.

The fixed protocol uses six tasks, two fresh sessions per task and system, and up to three graph submissions per session. Each matched pair uses the same model alias, seed, temperature (0.6), token budget (4096 per submission), task and public example. System order alternates across pairs. The task setter provides node documentation and one input/output example. No starter graph or repair from a human is supplied.

The agent gets deterministic graph diagnostics or the public example's actual output after each failed submission. A session ends at the first graph that passes that example or after three submissions. Two additional fixtures per task are withheld from the model. Success requires exact ordered outputs from the native engine on both held-out inputs and a passing public example. Record first-submission success and success by the budget, keeping failures in the denominator. The sessions share six tasks and one model. Input fixtures and generated output rows are checks within a session.

Both arms expose a restricted catalog and the same arithmetic expression syntax. The agent specifies all graph nodes and their connections. The adapter serializes them and supplies fixed input and output plumbing. The catalogs exercise single-row numeric loops. They do not measure GUI manipulation or performance across unrestricted operator catalogs. Repeated identical graphs can share a native verification run for the same input. Infrastructure failures must be reported separately from task failures.

After inspecting graph-construction errors in the original sessions, we fixed a second condition before collecting its responses. Both arms now receive an equivalent complete worked example for a separate task, emitting the same pair exactly twice. The tasks, inputs, sessions, budgets, success criterion, and evaluator are otherwise identical. This checks how sensitive the result is to showing the model a valid wiring pattern.

After auditing the worked-example failures, we froze a third condition at commit `e0f0fad` before generating any responses. Both tools received a symbolic diagram with the arithmetic, state updates, and continuation test left open. The KNIME diagram labels the separate collection and feedback inputs. The WAFFLE diagram labels both output expressions. Each session still received its task-specific public input and required output. All other generation and scoring settings were identical.

The fourth condition was fixed at commit `5e4ecca` before collecting its 24 sessions. It appended a short explanation to each wiring diagram. The WAFFLE explanation specifies which state is visible to the output expressions, successive assignments, and the continuation test. The KNIME explanation specifies which row each formula reads, which row is collected, and which row becomes feedback. Both explanations describe what happens to the final collected row. Neither supplies a task expression.

The fifth condition was fixed at commit `ee6c7bb` before collecting its 24 sessions. It retained the timing explanation. WAFFLE received the names of the four scratch fields and the assignment restrictions. KNIME received the requirement that each input reference name a preceding node, including both inputs to the loop end. The added text was identical for all six tasks within a system and supplied no expressions.

The sixth condition was fixed at commit `78db167` before generation. We reran both systems in fresh sessions. WAFFLE received the identical fifth-condition prompt. KNIME received that condition plus a task-neutral description of the collection input, empty feedback, and the required connection from the loop end to the sink. This supplement gives no graph, expression, or stopping predicate.

The seventh condition was fixed at commit `c6df789` before generation. It adds the same three sentences to all six WAFFLE prompts. START initializers must be JSON expression strings, including numeric constants, and temporary values must use a declared scratch field. The text supplies no task expression. All twelve KNIME sessions received the identical sixth-condition prompts and seeds in a fresh run.

The eighth condition was frozen at commit `ed1c0ba` before generation. For every task in both systems, we added one sentence to the seventh prompt: "The first row emitted is output row 1, even when the workflow counter starts at 0." The sentence gives no update expression or branching rule.

The ninth condition was frozen at commit `d74226b` before generation. Every WAFFLE task received the same clarification about JSON argument types: EMIT takes two separate plain expression strings and END takes one plain string for its continuation test. No task expression or example was supplied. All 12 KNIME sessions received their eighth-condition prompts and seeds in fresh runs.

The tenth condition was frozen at commit `9091800` before generation. For each KNIME task the supplement specifies that the continuation flag reads the row after state updates and that a filter drops a false-flag row before the feedback input. It supplies no task variables, predicate or example. All twelve WAFFLE sessions repeated the ninth-condition prompts and seeds in fresh runs.

We froze the eleventh condition at commit `47d6ac0` before inference. The only new instruction specified that the KNIME feedback filter must take its input directly from the node that assigns the flag it tests. It supplied no task expression or node index. We repeated all twelve WAFFLE sessions with the tenth-condition prompts and seeds.

We froze condition twelve at commit `7617e51` before collecting its 24 fresh sessions. Each KNIME prompt required the feedback filter, its direct connection to the loop end's feedback input, and the sink's direct connection to the loop end. The preceding condition already specified the filter's input. The supplement used the same wording for all six tasks and supplied no formulas or task-specific node indexes. The WAFFLE prompt was identical to condition eleven for each task.

We froze condition thirteen at commit `1059a5c` before generating any graphs. We replaced the two KNIME instructions that had required all state updates before filtering and a direct edge from the filter to the loop end. The revised wording defines 1 as continue and 0 as stop. After filtering, a retained row may go directly to feedback or pass through state-update nodes. The filter still reads its flag setter and the sink still reads the loop end. The instruction gives no task formula or node index. WAFFLE received its condition-twelve prompts in fresh sessions.

### Reproduce the comparison

From this directory, run `python evidence.py results` to verify the prompt hashes, all 312 sessions, their native held-out outputs, and the independently authored feasibility controls for each task in both systems. The recorded prompts are reconstructed from `protocol.py` and `worked_example.py`. The model responses, public-example errors, token usage, and submitted graphs are in `results/sessions.jsonl`. Each record in `results/native.jsonl` contains one engine's actual output for the graph and fixture identified by its hash. `results/outcomes.csv` gives one row per session. Two sessions per task are repeat measurements of the same task.

The inference service used vLLM's four-bit W4A16 checkpoint of Qwen3.8-Flash-Next-Uncensored, served as `flash-next`, with thinking disabled. Sessions share no chat history. A new submission follows a public diagnostic within the same session. The interface accepts node connections and expressions, supplies native serialization, and bounds execution at eight iterations. WAFFLE has a fixed five-node pattern in this catalog. KNIME's recursive loop has separate collection and feedback inputs, and the agent can add formula and filter nodes. The worked example shows both wiring patterns explicitly. This is an interface-specific comparison on six numeric loop tasks.

To repeat generation, provide an OpenAI-compatible inference endpoint and a token through the environment (`INFERENCE_TOKEN`). Run the following commands with fresh output directories, using Python 3.12 with `requests`. The feasibility-control graphs in `controls.py` are never included in prompts.

```text
python trials.py RUN/trials --endpoint ENDPOINT --model MODEL
python trials.py RUN/worked --endpoint ENDPOINT --model MODEL --worked-example
python trials.py RUN/wiring --endpoint ENDPOINT --model MODEL --wiring-only
python trials.py RUN/timing --endpoint ENDPOINT --model MODEL --wiring-timing
python trials.py RUN/rules --endpoint ENDPOINT --model MODEL --wiring-rules
python trials.py RUN/ports --endpoint ENDPOINT --model MODEL --end-ports
python trials.py RUN/assignments --endpoint ENDPOINT --model MODEL --assignment-format
python trials.py RUN/numbering --endpoint ENDPOINT --model MODEL --row-numbering
python trials.py RUN/expressions --endpoint ENDPOINT --model MODEL --expression-strings
python trials.py RUN/feedback --endpoint ENDPOINT --model MODEL --feedback-filter
python trials.py RUN/flag-source --endpoint ENDPOINT --model MODEL --flag-source
python trials.py RUN/required-connections --endpoint ENDPOINT --model MODEL --required-connections
python trials.py RUN/filtered-updates --endpoint ENDPOINT --model MODEL --filtered-updates
python native.py prepare RUN/native --trials RUN/trials
python native.py prepare RUN/native-worked --trials RUN/worked
python native.py prepare RUN/native-wiring --trials RUN/wiring
python native.py prepare RUN/native-timing --trials RUN/timing
python native.py prepare RUN/native-rules --trials RUN/rules
python native.py prepare RUN/native-ports --trials RUN/ports
python native.py prepare RUN/native-assignments --trials RUN/assignments
python native.py prepare RUN/native-numbering --trials RUN/numbering
python native.py prepare RUN/native-expressions --trials RUN/expressions
python native.py prepare RUN/native-feedback --trials RUN/feedback
python native.py prepare RUN/native-flag-source --trials RUN/flag-source
python native.py prepare RUN/native-required-connections --trials RUN/required-connections
python native.py prepare RUN/native-filtered-updates --trials RUN/filtered-updates
python controls.py RUN/controls
```

Run the following two commands for each PACKAGE (`RUN/native`, `RUN/native-worked`, `RUN/native-wiring`, `RUN/native-timing`, `RUN/native-rules`, `RUN/native-ports`, `RUN/native-assignments`, `RUN/native-numbering`, `RUN/native-expressions`, `RUN/native-feedback`, `RUN/native-flag-source`, `RUN/native-required-connections`, `RUN/native-filtered-updates`, and `RUN/controls/engines`). The first uses portable KNIME Analytics Platform 5.5.3 on Windows. The second uses the existing native CaseExecutionSpec with the WAFFLE engine revision `a6e394bae138738c2e0aaa03a5bb7f8ec83c6ac6`. See the loop execution experiment for its Java, Python, sbt, and database prerequisites. Independent WAFFLE runs may be partitioned across manifests in separate subdirectories, retaining the graph identifiers and output rows.

```text
python native.py knime PACKAGE --runtime KNIME_DIRECTORY
python ../loop_execution/run_native.py PACKAGE --case-study --repo ENGINE_CHECKOUT --java JAVA --python PYTHON --sbt-launch SBT_LAUNCH_JAR
python evidence.py YOUR_RESULTS --collect RUN
```

Run the evidence command after all fourteen packages finish. The scoring program rejects missing engine outputs and fails if any reference workflow produces the wrong trace.
