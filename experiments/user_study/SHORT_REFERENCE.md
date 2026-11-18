# Field guide: 35-minute study

Use only the section for your current tool. The organizer supplies the starter for your assigned workflow. Keep the prepared calculation unchanged. Higher scores are better; the negative sign is expected. Save a different workflow copy for each task.

## KNIME

Import `sweep-starter.knwf` into Local space. Execute all and open the Results output table. The connected loop initially runs once, at K=2.

- **Counting Loop Start:** the iteration count is a maximum. The prepared body uses its zero-based iteration number plus 2 as K.
- **Variable Condition Loop End:** select a flow variable, comparison and target. It can stop before the count limit. Keep all iterations and include the final iteration. The supplied threshold is 0, which these negative scores do not reach.
- **Results:** view the collected K and score rows. Reset the loop before rerunning an edited configuration. Press **Ctrl+S before Export** so the file contains your latest controls, then export a separate `.knwf` for each task.

## Texera (WAFFLE)

Open your private prepared starter. Run it and double-click Results to open the output table and see K=2 once. CSV File Scan reads the points; Sort displays the collected results. Clustering and scoring are prepared because this prototype has no built-in K-means operator.

- **Loop Start:** initialization sets K; the output expression `D` sends the points to the body.
- **Loop End:** update changes K after the body. The condition is checked after this update: true runs another iteration; false finishes. The starter condition is `False`.
- The body makes the current `score` available to Loop End. Python comparisons and `and` combine conditions. Loop End collects the rows produced by all iterations.
- Use the download-arrow button to export a separate `.json` for each task. Rename each downloaded file to your participant/task name before continuing. Do not edit the prepared body, data reader or result node.

## Timing and saving

Practice: run the unchanged starter and find the controls and output (two minutes). Each task then has four minutes, including execution waits. Stop at the cap even if unfinished. Record elapsed seconds; use `not recorded` rather than guessing. Save the sweep before adapting it. Allow two minutes per tool for exports and form answers. If infrastructure prevents progress, mark a technical problem. Use the same supplied help in both tools.
