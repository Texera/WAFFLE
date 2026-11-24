# Recursive parent–child hierarchy

Brian Bates published this example on October 29, 2024 to trace descendants when a child can have multiple parents. The embedded input has 11 parent–child rows, including three repeated edges. After deduplication it has eight edges and three roots (A, Y and Z). The original sorts its final rows by root, depth and descendant. [Published workflow](https://kni.me/w/NDWM1k2Aq_TL-nce) · [Author's discussion and input example](https://forum.knime.com/t/parent-child-hierarchy-w-multiple-parents/84137) · [Version and archive hash](source.json)

| Boundary | Pairs to expand | Working relation for the join |
|---|---:|---:|
| Before iteration 1 | 5 | 8 |
| After iteration 1 | 6 | 11 |
| After iteration 2 | 0 | 11 |

Each iteration emits the current root–descendant pairs and extends them by joining each descendant to its children. The second feedback table combines the new pairs with the working-relation rows whose parents did not participate in that join. The loop stops when the first feedback table is empty. The five depth-one rows and six depth-two rows form the 11-row result.

**Reference.** We ran the published workflow from reset in KNIME Analytics Platform 5.5.3 with CSV writers observing its input, initial feedback tables, collected rows and final sorted result. Two additional runs redirected the collecting port to observe each feedback stream in turn. Both feedback connections, body operators and the original 100-iteration limit were preserved. The empty terminal frontier contributes zero rows to its observation CSV. The collection of depth-two results and the second pass through the working-relation port independently identify that iteration.

**Translations.** All three translations receive only the original input rows. WAFFLE serializes both tables into control variables at each iteration and reconstructs the input table at LoopStart. n8n uses a feedback edge to carry the two collections. RapidMiner Studio Core uses Loop Until and stores the two collections in process macros. Each body computes the expansion during execution. This is an output comparison with programmable body operators. The separate policy experiment in §7.2 measures which operations can be expressed using loop operators alone.

**Verification.** All four systems returned the same 11 ordered rows, including the depth column. For each iteration the checker also compares the two incoming tables, both feedback results, and the pairs contributed to the final output. Intermediate comparisons preserve duplicate counts and ignore row order. Generated row IDs are excluded. A separate traversal of the input graph checks the original result and its order. [Recorded inputs, workflows and outputs](results)

## Reproduce

Run `python verify.py` from this directory to check the archived outputs. To rerun the engines, supply fresh paths for REFERENCE and TRANSLATIONS. The parent [setup instructions](../README.md) specify the runtimes and example 05 CSV-writer template.

```sh
python original.py REFERENCE WRITER_TEMPLATE_FOLDER KNIME_INSTALL
python translate.py REFERENCE/input.csv TRANSLATIONS
python containers.py n8n TRANSLATIONS
python containers.py rapidminer TRANSLATIONS
python ../../loop_execution/run_native.py TRANSLATIONS --case-study --repo RUNTIME --python PYTHON --java JAVA --sbt-launch SBT_LAUNCH
python verify.py REFERENCE TRANSLATIONS
```
