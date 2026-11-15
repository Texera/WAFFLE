# Author rehearsal, November 15, 2026

This is a correctness rehearsal of prepared study materials. It contains no participant outcomes, authoring-time measurements, or evidence that either platform is easier to use.

## Native execution

All **36 checks pass: 18 KNIME and 18 WAFFLE**. Each platform runs two packs, with nine checks per pack:

| Check | Required behavior |
| --- | --- |
| Sweep starter | One K=2 result |
| Sweep, visible points | K=2,3,4 and matching scores |
| Sweep, changed points | K=2,3,4 and recomputed scores |
| Adaptation, visible points | K=2,3; stop when the target is reached |
| Adaptation, target reached immediately | K=2 only |
| Adaptation, target never reached | K=2,3,4; stop at the cap |
| File starter | First CSV and its mean |
| File loop, visible folder | All three filenames and means |
| File loop, additional CSV | All four filenames and means |

The checks compare both body visits and output rows with an independent NumPy reference. Return codes are zero and the generated input fingerprints are unchanged. The prepared bodies perform the actual computations in Java and Python; no answer table is substituted for execution.

Environment: Windows, Python 3.12, JDK 17, KNIME **5.5.3** (the active product version in its Equinox bundle configuration), and Texera prototype commit `a6e394bae138738c2e0aaa03a5bb7f8ec83c6ac6`. The installed KNIME directory retains an older 5.4.4 name; that name is not the running version. The WAFFLE harness uses the real coordinator and Python workers in materialized mode, one worker per operator, with the prototype's normal test infrastructure. It does not execute the browser frontend. No Texera source changes were needed.

`native-checks.json` is the captured checker report; `data/` contains synthetic fixtures; `raw/` contains the matching CSV traces and return codes. The selected KNIME traces were also reproduced in the GUI. `waffle-test-summary.txt` records all 18 ScalaTest cases. Full local engine logs are represented by SHA-256 hashes in `log-hashes.json`; they are not required to recompute the expected answers. See the parent README for the exact runner commands. Run `python experiments/user_study/verify_recorded.py` from the repository root to validate the capture without starting either application.

## GUI rehearsal and remaining gate

KNIME imports individual `.knwf` files, executes the prepared single-input starters, and shows the expected result tables. All three facilitator solutions also execute: the sweep returns K=2,3,4, the conditional loop returns K=2,3 including the final row, and the file loop returns `01-jan.csv`/20, `02-feb.csv`/40 and `03-mar.csv`/15. The file-loop reference gives a load warning that Counting Loop Start changes from CONFIGURED to IDLE before its input-count variable exists; Execute All configures it after the prepared input runs and completes successfully. This warning does not occur in the participant's single-input file starter.

The local Texera frontend and core backend services start, sign-in succeeds, and **both starters and all three Pack A reference solutions import and execute in the browser**. The starter tables show K=2/score=-343.56333333333333 and `01-jan.csv`/20. The sweep returns K=2,3,4 with scores -343.56333333333333, -130.23000000000002 and -2.2300000000000004. Adaptation returns only the first two rows. The folder loop returns the same three filename/mean pairs as KNIME. The result nodes show Completed.

The frontend first opened before the backend was ready and retained missing operator metadata. Reloading after the backend started and importing a clean copy resolved it. Start the services before the browser rehearsal. A separate study PostgreSQL database and Iceberg catalog were used. A local object store was started, but the dataset file service still lacks LakeFS; the study's prepared local-CSV readers and result tables work without that service. This rehearsal does not validate uploading datasets through Texera's dataset browser.

The materials are ready for a **teammate pilot on this local setup**, not main-study recruitment. Review the baseline with a KNIME-experienced teammate and pilot the cards and time limits. Pack B and all hidden variants have native checks; only Pack A was additionally rehearsed in the GUI. The reference solution rehearsal is not a timed human construction of each workflow. Repeat the GUI checks on the eventual study server.
