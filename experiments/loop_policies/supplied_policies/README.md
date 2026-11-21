# Reusing a supplied loop policy

These two workflows test whether a loop can call an existing local Python function unchanged. One function chooses the next cluster count after seeing a score. The other decides whether the improvement warrants another iteration. For both workflows we allow other native nodes and expressions. The invocation test uses stock operators, local data and the supplied file. A new custom operator or a service that runs the file would change that setup.

Each workflow receives two score tables from the [K-means experiment](../results/inputs/) and two interchangeable policy versions. The coarse selector can jump from K=2 to K=4 and return to K=3. The sequential selector advances one step at a time. The stopping functions require gains of 250 and 100 respectively. Every function writes its arguments to a local call log, allowing the verifier to distinguish a real invocation from a translation that returns the same rows.

| Workflow and input | Ordered K with version 1 | Ordered K with version 2 |
| --- | --- | --- |
| Choose K, far | 2, 4, 3 | 2, 3, 4 |
| Choose K, near | 2, 3 | 2, 3 |
| Decide whether to stop, far | 2, 3 | 2, 3, 4 |
| Decide whether to stop, near | 2, 3 | 2, 3, 4 |

WAFFLE's saved graphs consist of CSV File Scan, Loop Start and Loop End. For the selection workflow, Loop End calls the supplied file in the update field. For the stopping workflow it calls the file in the condition field. The input table supplies the file path. The two versions use identical loop fields and graph connections. All eight runs audit the function and its arguments once per iteration.

For each of the same eight cases, we also implemented the policy logic directly in native KNIME, n8n and RapidMiner operators. These 24 executions matched the expected ordered scores, including the revisit to K=3. The [run records](observations.csv) record the implementation used. The [previous experiment](../native_controls/) supplies a further 64 native runs.

The two supplied-function rows in Table 2 mark direct support as **No** when the documented route for executing the Python file uses a separate node. KNIME documents the Python Script node, n8n the Code node and RapidMiner the Execute Python operator. The new benchmark measures a language-specific integration requirement. Its output checks give all four systems credit for equivalent native implementations. The three script-node routes were identified from product documentation and were outside the execution comparison. [KNIME Python integration](https://docs.knime.com/latest/python_installation_guide/index.html) · [n8n Code node](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.code/) · [RapidMiner Execute Python](https://docs.rapidminer.com/10.1/studio/operators/utility/scripting/execute_python.html)

## Reproduce

Run `python check_policies.py` to verify the saved traces against the reference K-means scores and the prescribed sequences. To rerun, first reproduce [the native-controls baseline](../native_controls/README.md). Set `POLICY_RUN` to a fresh absolute directory. From this directory run the following PowerShell commands using the same runtime paths as the baseline.

    python prepare_cases.py $env:POLICY_RUN
    python ../../user_study/run_waffle.py --package $env:POLICY_RUN --repo $env:TEXERA_REPO --python $env:UDF_PYTHON_PATH --java $env:WAFFLE_JAVA --sbt-launch $env:SBT_LAUNCH
    python translations.py $env:POLICY_RUN $env:WAFFLE_NATIVE_CONTROLS_RUN knime
    python translations.py $env:POLICY_RUN $env:WAFFLE_NATIVE_CONTROLS_RUN n8n
    python translations.py $env:POLICY_RUN $env:WAFFLE_NATIVE_CONTROLS_RUN rapidminer
    python check_policies.py --extract $env:POLICY_RUN

The extractor reads the native sink output, checks every argument logged by the original policy, checks the inventory of operators, verifies that the two modules were supplied byte-for-byte, and compares loop-field configurations across input and policy changes.
