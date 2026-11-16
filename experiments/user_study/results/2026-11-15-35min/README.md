# Connected-loop rehearsal: 35-minute protocol

Author-run correctness evidence, not participant results or a timing pilot.

KNIME 5.5.3 and Texera prototype `a6e394bae138738c2e0aaa03a5bb7f8ec83c6ac6` each passed 12 native execution checks. Each pack has a connected single-iteration starter, two sweep fixtures, and three adaptation fixtures (target reached at K=3, reached immediately, never reached). All 24 runs had exit code 0 and matched the independent NumPy reference for both actual body visits and collected result rows; no input fingerprints changed.

KNIME starts with Counting Loop Start (one iteration) and Variable Condition Loop End (score >= 0). Increasing the count to three produces the sweep; changing its threshold produces early stopping. Texera starts with Loop Start, a prepared clustering body and Loop End with condition False. CSV File Scan and Sort remain native. The sweep/stop-rule changes affect only loop control.

The tiny synthetic fixtures and raw traces are included. Recheck with `python experiments/user_study/verify_recorded.py 2026-11-15-35min`. This recomputes expected values from fixtures and compares the saved engine evidence; it does not launch either engine. Generate fresh native runs with `study.py prepare <new-folder> --short` and the two documented runners.

Recorded output values for pack A: K=2 score -343.56333333333333; K=3 score -130.23000000000002; K=4 score -2.2300000000000004. The target -236.896667 stops after K=3 and includes that result. Pack B uses different coordinates and target -299.230000. Hidden cases verify immediate stopping and the K=4 cap.

Six relocated KNIME archives (two packs, starter/sweep/adaptation) also passed native execution. `portable-checks.json` records those exact outputs. Participant KNIME archives embed the input fixture and use a unique temporary directory for traces.

Pack A was then rehearsed through both GUIs. The operator controls were edited from a one-iteration starter to the sweep, then to the target-based stopping rule. Both result viewers showed K=2 initially, K=2,3,4 for the sweep, and K=2,3 for adaptation. Each task was exported separately and its saved controls inspected. `gui-checks.json` records the observations, export hashes and actual body-visit trace. Pack B was checked natively, not through the GUI. These are author checks, not participant timings or ease ratings.

The first KNIME exports contained the last saved controls rather than the current GUI edits. Saving before Export corrected this, and all four final exports were inspected. The field guide and form now explicitly require Ctrl+S before every KNIME export.

The single seven-section Google Form was previewed through its final page without submitting a response. It remains an unpublished draft in the organizer's UCI account. Upload and final submission have not been exercised. Hosted setup/import/run/export and a teammate timing pilot remain necessary before recruitment. Do not distribute absolute-path facilitator workflows to another machine without regenerating or packaging their inputs.
