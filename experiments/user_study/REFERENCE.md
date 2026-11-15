# Participant reference sheets

Give only the sheet for the platform in use. The facilitator supplies one task card at a time. Leave the prepared computation nodes unchanged. Any correct loop construction is accepted.

## KNIME

Import the `.knwf` starter into Local space. Execute all, then select the last node to view its output. Save a separate copy for each activity.

The annotated nodes prepare the inputs, perform one computation and show the results. Add loop controls around the computation. A **Counting Loop Start** repeats its input table and supplies the zero-based `currentIteration` flow variable. Configure its iteration count, or bind that count to an incoming flow variable through the configuration dialog's Flow Variables tab. A **Loop End** collects the rows from successive iterations.

The prepared K-means node converts `currentIteration` into K by adding 2. It returns K and score, and exposes `score` as a flow variable. The prepared file node uses `currentIteration` to select a filename. Its input preparation exposes `input_count`, the current number of CSV files. The starter supplies iteration zero so it runs before you add a loop.

**Variable Condition Loop End** can stop on a flow-variable comparison. Select the variable, comparison and target. Its collection settings control whether to include the final iteration and whether to keep earlier rows. When paired with Counting Loop Start, it can finish early or at the count limit. Other valid loop nodes and equivalent expressions are allowed.

Reset a previously executed loop before rerunning after a change. View errors on the affected node. Do not change the calculation, input fixtures or evidence-writing code. Ask the facilitator when an application failure prevents editing or execution.

## WAFFLE in Texera

Import the `.json` starter with the workflow upload button. Open it, run it and select Results to see the output. Save a separate copy for each activity.

The prepared computation uses ordinary Texera nodes where available. **CSV File Scan** reads the points. **File Scan** reads a price file, and **Aggregate** computes its average. **Sort** orders the result rows for viewing. Add Loop Start and Loop End around the computation to repeat it. Connect Results after Loop End, which collects the body rows across iterations.

Loop Start has `init()` and `provideData()` fields. Use Python assignments in `init()` to give loop variables initial values. `provideData()` receives the input table as pandas `D`; its final expression is the table sent to the body. For example, `D.assign(column=value)` returns a table with a changed column. Loop End has `update()` assignments and a Boolean `checkCondition()` expression. It evaluates the condition after the current body and update: true starts another iteration, false finishes.

The prepared K-means node reads points from its input and uses the loop variable `K` (or K=2 before a loop is added). It returns K and score and exposes `score` for the stopping condition. Clustering is the prepared Python node because this Texera version has no built-in K-means operator; participants do not edit its calculation.

For files, **List files - prepared** supplies a table with a `file` column. It is already on the starter canvas, separately from the single-file computation. A source such as File Scan receives variables through its purple control-variable port. Connect the loop to that port and use `$file` in the File property to select the current file. `provideData()` can assign a variable from a row of `D` without returning data. Use `len(D)` for the number of rows. The prepared reader skips the header and reads numeric prices; Aggregate and the filename/audit adapter need no code changes.

This prototype starts fresh workers each iteration. It runs initialization, then restores saved loop-variable values. Keep initialization free of side effects. Use ordinary Python comparisons, `and`, and increments such as `i += 1`. Do not change the prepared calculation, input fixtures or evidence-writing code. Ask the facilitator when an application failure prevents editing or execution.

## Facilitator only: interpretation

These are matched **loop-authoring** tasks with prepared bodies. The bodies implement deterministic Lloyd clustering in Java and Python, checked against an independent NumPy reference. They are not a comparison of native KNIME versus Texera machine-learning operators. Score is negative within-cluster squared distance, and higher is better for this task. The selected K is a task answer, not a claim about statistical model selection.

The file body reads one selected local CSV and computes its mean in both systems. Texera's native File Scan uses a fixed double column and skips one header line for these one-column fixtures, then native Aggregate computes the mean. This is not a general CSV parser for arbitrary schemas. The local-path lister remains a prepared adapter because the native File Lister targets the dataset service; the filename/audit adapter only labels results and records visits. Keep parsing and calculation out of timed work in both tools. A literal fixed file count fails the added-file check. Accept any file result order, but require exactly one row per filename. For adaptation, verify actual visits as well as output rows: running every K and filtering afterward does not satisfy early stopping.

Activity 2 starts from the participant's Activity 1 submission. If necessary, supply the facilitator's correct sweep as a fallback and record assistance. Never give reference solutions to one platform only. Prioritize fixing infrastructure before the teammate pilot, then ask a KNIME-experienced teammate to review whether a more convenient valid solution exists.
