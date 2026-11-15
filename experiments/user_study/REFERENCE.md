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

The prepared nodes supply an input table, perform one computation and show the results. Add **Loop Start** before the computation and **Loop End** after it. Connect Results after Loop End. Loop End collects the body rows across iterations.

Loop Start has `init()` and `provideData()` fields. Use Python assignments in `init()` to give loop variables initial values. `provideData()` receives the input table as pandas `D`; its final expression is the table sent to the body. For example, `D.assign(column=value)` returns a table with a changed column. Loop End has `update()` assignments and a Boolean `checkCondition()` expression. It evaluates the condition after the current body and update: true starts another iteration, false finishes.

The prepared K-means body reads the row's K, returns K and score, and exposes `score` for the stopping condition. The file starter supplies `index` and `count`. Its prepared body reads the zero-based index and returns that file's name and mean. Loop control can use the count in `D` and the score from the body. The initial starter works without boundaries.

This prototype starts fresh workers each iteration. It runs initialization, then restores saved loop-variable values. Keep initialization free of side effects. Use ordinary Python comparisons, `and`, and increments such as `i += 1`. Do not change the prepared calculation, input fixtures or evidence-writing code. Ask the facilitator when an application failure prevents editing or execution.

## Facilitator only: interpretation

These are matched **loop-authoring** tasks with prepared bodies. The bodies implement deterministic Lloyd clustering in Java and Python, checked against an independent NumPy reference. They are not a comparison of native KNIME versus Texera machine-learning operators. Score is negative within-cluster squared distance, and higher is better for this task. The selected K is a task answer, not a claim about statistical model selection.

The file body reads one selected local CSV and computes its mean in both systems. This keeps file parsing out of the timed work. A literal fixed file count fails the added-file check. Accept any result order for the file task, but require exactly one result per filename. For adaptation, verify actual visits as well as output rows: running every K and filtering afterward does not satisfy early stopping.

Activity 2 starts from the participant's Activity 1 submission. If necessary, supply the facilitator's correct sweep as a fallback and record assistance. Never give reference solutions to one platform only. Prioritize fixing infrastructure before the teammate pilot, then ask a KNIME-experienced teammate to review whether a more convenient valid solution exists.
