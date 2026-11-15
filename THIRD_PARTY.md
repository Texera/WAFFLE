# Sources and attribution

## Texera

The runtime patch and planning implementation derive from Apache Texera and the research branch at [aglinxinyuan/texera](https://github.com/aglinxinyuan/texera). Exact commits and Git trees are in [implementation.lock.json](implementation.lock.json). Upstream license headers are retained; the upstream Apache 2.0 LICENSE and NOTICE are included.

The copied planning runner and Scala files provide a readable snapshot. Captured machine paths in runner/ are normalized placeholders; use the pinned engine checkout and tools/run_planning.py to rerun that experiment.

## KNIME examples

The case study uses the official [KNIME loop example collection](https://hub.knime.com/knime/spaces/Examples/latest/06_Control_Structures/04_Loops/), examples 09–16. The recorded authors, item IDs, versions, timestamps and archive checksums, including the CSV writer template, are in [sources.json](experiments/case_study/sources.json).

Original KNIME workflow archives and the KNIME application are not bundled. download.py retrieves the public examples and verifies their captured hashes. Derived CSV inputs and outputs are included to make the comparison inspectable. Attribution and any upstream terms for those examples remain applicable; the repository's code license does not relicense third-party example content.

## Generated data and measurements

The execution dataset is synthetic, generated with the seed and parameters in experiment.py. Planning inputs and recorded benchmark measurements are described in their provenance files. No participant or private user dataset is included.
