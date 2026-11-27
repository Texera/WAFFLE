# Three additional Table 3 tasks

A Yes means a loop operator performed the named task in a verified workflow. A No means the verified route used an extra node for that task. All four systems produced the reference outputs. These rows characterize the tested graphs and do not exhaust alternative implementations.

| Task | WAFFLE | KNIME | n8n | RapidMiner Studio Core |
| --- | --- | --- | --- | --- |
| Read one parameter row at a time | Yes | Yes | Yes | No |
| Record a loop variable each iteration | Yes | Yes | No | No |
| Include the stopping row in the result | Yes | Yes | No | Yes |

- **Parameter row.** In [published example 12](../sources.json), the five parameter values 10, 20, 30, 40 and 50 each apply to four points. WAFFLE selects the current row at LoopStart. KNIME uses Table Row to Variable Loop Start. The [n8n graph](../n8n_results/12-n8n.json) projects the input field and Loop Over Items chooses one item per iteration. In the [RapidMiner process](../rapidminer_results/12.rmp), the body indexes the prepared list using the iteration macro.
- **Variable history.** Published example 16 uses KNIME's Variable Loop End. Its [reference output](../results/16-results.csv) has five rows containing the counter values 0 through 4. The [original WAFFLE translation](../results/16-texera.json) formed the rows in the body. In the additional [native WAFFLE run](workflow.json), a one-row source provides the output schema and a sentinel value of −1. LoopStart writes the current value of its variable into that row, and LoopEnd appends it and advances the variable. The [native output](native.jsonl) matches all five reference rows. The [n8n](../n8n_results/16-n8n.json) and [RapidMiner](../rapidminer_results/16.rmp) runs each use a body node to turn the counter into a result row.
- **Stopping row.** In the [native target-score runs](../../loop_policies/native_controls/), the output includes all visited scores through the first one at or above −100, or through K=4 if none qualifies. WAFFLE collects the current row at LoopEnd. KNIME sets `addLastRows` on Variable Condition Loop End. RapidMiner's Loop Until collects the body's result on its output port including the terminal iteration. Its separate filter computes the stopping signal. In n8n an Edit Fields node appends the current score to the result history before the If node tests whether to continue. This task concerns keeping the final contribution. Flattening a collection of tables into one table is assessed separately.

Run `python verify.py` here and `python verify.py` under `experiments/loop_policies/native_controls/` to check the archived outputs. For a fresh WAFFLE history run, copy `manifest.json` and `workflow.json` to an empty directory and run `experiments/loop_execution/run_native.py DIRECTORY --case-study` with the runtime options in the [case-study instructions](../README.md). The recorded run used prototype revision `a6e394bae138738c2e0aaa03a5bb7f8ec83c6ac6`.
