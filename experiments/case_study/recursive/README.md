# A published recursive workflow

[Official workflow 07](https://kni.me/w/94VEz513hTMYvFuz) has two disconnected branches. We chose it because the recursive-start/recursive-end pair was absent from the initial eight examples. We count it as one additional published workflow. The [source manifest](source.json) pins the original archive and author. The original contains two Table Creator inputs and both algorithms. We obtained reference outputs by running the original from reset in KNIME Analytics Platform 5.5.3 with a CSV writer added at each seed and result port. No recurrence, seed, or limit was changed.

| Branch | Seed | Original rule | Iterations | Last row | Rows matched by each translation |
|---|---|---|---:|---|---:|
| Triangular sums | (0, 0) | Increment the first value, then add it to the running sum | 10 | (10, 55) | 10/10 |
| Fibonacci pairs | (0, 1) | Shift the second value left and replace it with the sum of the pair | 30 | (832040, 1346269) | 30/30 |

Each translation runs the two independent branches separately. WAFFLE executes native LoopStart and LoopEnd and a body operator. The body emits the new pair as a row and as control values for LoopEnd to retain for the next iteration. n8n executes a feedback edge through an If node. RapidMiner uses a serial Loop and two process macros to carry the pair, and collects each body's output. Each system computes a new pair once per iteration. The graphs contain only the seed values and rules.

The [recorded outputs](results) include both original input tables, both KNIME reference outputs, the translated workflows, and all three systems' returned rows. The checker maps the two result columns by meaning, omits KNIME's generated row IDs and compares integer pairs as multisets with exact equality and duplicate counts. An independent triangular-number formula and fast-doubling Fibonacci calculation check the reference sequence in iteration order. All 40 reference rows matched. This example tests one-row feedback and leaves general recursive-table support open.

## Reproduce

From this directory, `python verify.py` rechecks the saved outputs without starting an engine. To repeat the runs, use the pinned WAFFLE runtime and the n8n and RapidMiner images documented in the [case-study setup](../README.md). The writer template is example 05 from the parent setup. Supply fresh absolute directories for REFERENCE and TRANSLATIONS.

```sh
python original.py REFERENCE WRITER_TEMPLATE_FOLDER KNIME_INSTALL
python translate.py REFERENCE/07_Example_for_Recursive_Looping/workflow.knime TRANSLATIONS
python containers.py n8n TRANSLATIONS
python containers.py rapidminer TRANSLATIONS
python ../../loop_execution/run_native.py TRANSLATIONS --case-study --repo RUNTIME --python PYTHON --java JAVA --sbt-launch SBT_LAUNCH
python verify.py REFERENCE TRANSLATIONS
```
