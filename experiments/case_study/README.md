# KNIME loop translation study

Eight consecutive official KNIME loop examples, numbered 09–16, were selected before translation. `sources.json` records URLs, authors, versions and archive hashes. No original `.knwf` archive is redistributed here. The official collection is https://hub.knime.com/knime/spaces/Examples/latest/06_Control_Structures/04_Loops/ .

The [published-plan analysis](published_loops/README.md) examines 1,198 distinct archived plans and compares boundary types and path structure in the 801 single-pair plans with the original eight examples and a [ninth published recursive workflow](recursive/README.md). A [tenth workflow](hierarchy/README.md) exercises changing table sizes with the same recursive boundaries.

This is a bounded correctness study of these examples, not a random sample of workflows, a full-system equivalence test or a usability study. Long counts and intervals are reduced to five iterations in both systems. Case12 uses the first five of the original 38 loop-table rows. Every adjustment is recorded by `prepare_knime.py`. Cases09 and11 retain their original iteration settings and datasets (four chunks and thirteen groups). The computations inside each iteration are retained.

Comparison protocol, set before the final KNIME runs:

- Re-execute the originals with `-reset`; cached KNIME outputs do not count as execution evidence. Force UTF-8 for CSV export so statistics column names retain their Unicode symbols.
- Export the loop result and source tables through additional CSV writers; do not change existing data connections or computations.
- Manually translate the computation into Python UDFs between native Texera LoopStart and LoopEnd operators. This tests the loop abstraction; it does not test an automatic translator or claim that Texera has a native counterpart for every KNIME body node.
- Compare scalar result tables as multisets, preserving duplicate multiplicities and every scalar result column. Compare strings exactly and numbers with absolute and relative tolerance `1e-9`. Convert KNIME missing cells to null.
- Undefined statistics represented by KNIME as NaN use a JSON-safe `{"__float__":"NaN"}` tag in both outputs. This is distinct from missing/null, finite numbers and the string "NaN". The three-point group in case11 exercises this rule.
- Ignore generated row IDs, except that Value Counter uses the row ID as a category key; retain that key as `value`. Histogram image cells in case11, display colors and interactive views are outside the comparison. Case14 checks the table at Loop End, before color/plot display.
- Case14 replaces X with X times the interval value, then replaces Y with the new X times the negative interval value, matching the sequential KNIME formulas.
- Case15 accumulates rows at Texera LoopEnd and pivots them into columns afterward. It does not use a native column-appending LoopEnd.
- Retain failures and report only verified cases. Do not count a load failure as an expressiveness limitation.

The runtime directory on the study machine is named `knime-5.4.4`, but the active product/core/base bundles are **KNIME 5.5.3**. The missing Data Generation extension was installed before the final runs. Exact active versions are saved with the results.

## Reproduction

Use Python 3.12, a KNIME installation with batch execution and the Data Generation extension, and the runtime checkout prepared by the root `tools/prepare_engine.py`. First complete the build and schema preparation in `../loop_execution/README.md`. Run the commands below from `experiments/case_study/`; the Windows paths are examples.

```powershell
python download.py C:/scratch/knime-sources
python prepare_knime.py C:/scratch/knime-sources C:/scratch/knime-cases
python run_knime.py C:/scratch/knime-cases --runtime C:/path/to/knime
python translate.py C:/scratch/knime-cases
python ../loop_execution/run_native.py C:/scratch/knime-cases --repo C:/path/to/texera --python C:/path/to/texera-python.exe --java C:/path/to/jdk17/bin/java.exe --sbt-launch C:/path/to/sbt-launch.jar --case-study
python check.py C:/scratch/knime-cases
python -m unittest test_check.py
```

The native harness records real compiled workflow output in `native.jsonl`. `check.py` refuses to classify an unsuccessful KNIME run or absent native result as a match. Each package is immutable evidence: use a new output directory for a rerun.

## n8n comparison

The eight importable graphs in [n8n_results](n8n_results) use the same saved input tables and bounds. Seven run the body with a Loop Over Items node. The condition workflow uses an If node with a feedback edge and tests the updated counter after each body execution. JavaScript Code nodes implement the table computations. In case 15 a final Code node turns the five iteration results into columns.

Run the following command from this directory with Python 3.12 and Docker. Use a new output directory. The generator embeds only the input rows in each workflow. Docker runs the pinned n8n image with networking disabled and mounts only that workflow. The host reads the executed body's iteration count and final output rows, then compares the rows with the saved KNIME output using the same checker as the Texera runs.

    python n8n_cases.py n8n-rerun

The recorded run used n8n 2.48.7. All eight translations matched (241 scalar output rows). Each run file records the workflow hash, image digest, body execution count, and final rows. The comparison covers these inputs, iteration bounds, and scalar columns.

## RapidMiner comparison

The [RapidMiner processes and recorded outputs](rapidminer_results) cover the same eight inputs and iteration bounds. Seven processes use RapidMiner's Loop operator. The conditional process uses Loop Until to stop after the counter reaches four, including that iteration's row. Groovy scripts implement the body computations. For column collection, a final script turns five iteration values into one row with five columns.

Run this command from this directory with Python 3.12 and Docker, using a new output directory:

    python rapidminer/run.py rapidminer-rerun

The runner builds RapidMiner Studio Core 10.1.0 and runs each process with networking disabled. The container receives the process and its input data. The host checks the executed body's iteration count and compares the returned rows with the saved KNIME output. All eight processes matched across 241 scalar output rows.
