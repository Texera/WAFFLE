# Native-operator study rehearsal, November 15, 2026

This revision replaces prepared Python I/O and averaging with native Texera operators where available. These are author correctness checks, not participant results or evidence of greater usability.

## Workflow changes

The sweep and adaptation use CSV File Scan, a prepared K-means/scoring node, the ordinary Loop Start and Loop End operators, and Sort for output. The tested Texera revision has no built-in K-means operator. The prepared calculation and independent expected scores are unchanged.

The file loop uses a prepared local path lister, Loop Start, native File Scan and Aggregate, a filename/audit adapter, Loop End and Sort. Loop Start sends `file` through File Scan's control-variable port; `$file` selects the current file. Aggregate computes the mean. The adapter only attaches the filename and records the visit. The single-file starter has a constant path and the prepared lister already on the canvas, ready for loop wiring.

File Scan reads these one-column numeric fixtures with a fixed double schema and skips one header line. This is not general CSV parsing. The local lister remains prepared because the native File Lister needs the dataset service, which is unavailable in this local setup. Participants edit loop controls and native properties, not helper code. KNIME retains the same prepared calculation and convenient valid loop baseline; a KNIME-experienced teammate should still review it before the pilot.

## Execution evidence

All **36 native checks pass: 18 WAFFLE and 18 KNIME**, with no changed input files. The nine checks per pack remain: sweep starter, sweep visible, sweep changed points, adaptation visible, adaptation immediate stop, adaptation cap, file starter, file loop, and file loop with one added CSV. Both packs are checked. Actual body visits and sink rows match the independent reference, including the stopping row and no extra iterations.

WAFFLE ran on prototype `a6e394bae138738c2e0aaa03a5bb7f8ec83c6ac6`, using its real coordinator and Scala/Python workers in materialized mode. Prepared UDFs use one worker; native Aggregate can expand into multiple physical operators and workers. The harness captures the actual native Sort sink output separately from body-visit logging. No prototype source or paper changes were made. KNIME ran version 5.5.3 with Java Snippet. The Windows environment used Python 3.12 and JDK 17.

The accepted WAFFLE and KNIME executions used separate generated packages with byte-identical input fixtures. `native-checks.json` combines their checker reports; `data/` holds the common fixtures; `raw/` contains all visits, outputs and exit codes. `waffle-test-summary.txt` records 18 passing ScalaTest cases. `log-hashes.json` records full local log hashes. The earlier capture remains intact.

During development, rejected candidates exposed unordered sink rows, a File Scan filename/schema mismatch, and a misnamed Sort property. The accepted graphs use native Sort, a separate filename adapter, and the correct `attribute` property. Only the final passing executions are in this capture. Iceberg commit-contention retries recovered during native aggregation; the tests finished successfully.

Run the commands in the parent study README to execute fresh workflows. To independently recheck this saved evidence without launching the applications:

```text
python -m unittest discover -s experiments/user_study -v
python experiments/user_study/verify_recorded.py 2026-11-15-native-operators
```

## GUI rehearsal

The revised Pack A file starter, sweep starter, sweep, adaptation and file loop were imported separately into the local Texera GUI. The native file loop returns `01-jan.csv`/20, `02-feb.csv`/40 and `03-mar.csv`/15. The adaptation returns K=2,3 and includes the stopping row. The single-input starters return K=2 and the first file's mean, respectively. The sweep returns K=2,3,4 with the reference scores.

KNIME graphs are unchanged from the earlier GUI rehearsal; all 18 native checks were repeated for this record. Pack B and hidden variants have native checks only. This rehearsal runs prepared reference workflows rather than timing a participant's construction. Repeat the GUI rehearsal after moving to the hosted study server, and pilot the materials with a teammate before recruitment. Dataset-browser uploads are not validated by this local-path test.
