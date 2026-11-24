# Loop boundaries in published plans

This structural sample uses the [6K-Set from Chowder](https://github.com/Texera/Chowder/tree/e054e86a6a239b15783b8884e675a5f43a36f38d/experiments/workflows/6k_set). Its archive SHA-256 is pinned in `analyze.py`. [Pasta §6.2 and Table 4](https://doi.org/10.1145/3698832) report 6,148 workflows for analysis, 849 for materialization-size evaluations, and two executable workflows for clock-time evaluations. [Chowder Table 2](https://github.com/Texera/Chowder/blob/e054e86a6a239b15783b8884e675a5f43a36f38d/Chowder_Full_Technical_Report.pdf) reports 6,191 plans for the planner and six end-to-end workflows. The [released Pasta archive](https://github.com/Texera/Pasta/blob/288f25009f10a142300a14bcfd85710be8c87adf/pasta_experiment_inputs/mat_size_experiment_workflows.zip) contains 6,191 JSON files. A multiset comparison of SHA-256 hashes matched all 6,191 JSON payloads to the Chowder archive, including entries with different filenames. We count this as one source.

The archived plans retain operator display names, port identifiers and edges. The two boundary nodes in each sampled plan substitute dummy operators for the original configurations.

Of 6,191 entries, 1,159 had a directed path from a node labeled “Loop Start” to one labeled “Loop End”. The labels may include a prefix such as “Counting”. We restricted eligibility to the 832 entries with exactly one start and one end and a directed path between them. This avoids guessing pairings in nested or disjoint loops. Alternative names for loop operators can escape this screen.

We fingerprint each labeled directed graph using the multisets of its labeled predecessors and successors recursively, including the source and target ports of every edge. Node IDs, filenames, display coordinates and edge ordering do not affect the fingerprint. Different fingerprints distinguish different labeled structures. We retained one entry per fingerprint and selected the first 500 of 798 fingerprints in SHA-256 order. Frequencies describe this sample of structures, not a prevalence estimate for all uses of either system.

The 500 plans contained 36 distinct pairs of normalized boundary labels. In 267 plans the pair also appeared among the eight output-checked examples; seven of those examples' eight pairs occurred in the sample. The other 233 include 39 recursive-start/recursive-end plans. A matching pair does not validate the body's behavior or a configuration. In 297 plans all edges entering a start-to-end path from outside that region entered at the start, and every edge leaving it exited at the end. The other 203 have side links to or from that path region. A branch ending at its own sink can be legal in WAFFLE, so a side link by itself does not establish incompatibility.

The [sample](sample.csv) publishes fingerprints, boundary labels, side-link counts and SHA-256 hashes of archive member names. Source attribution stays with the upstream archive. The [eight reference pairs](reference_pairs.json) were read from the saved workflow settings after checking the published archive hashes against the [source manifest](../sources.json). Names are case-folded, punctuation is normalized and “TableRow” is treated as “Table Row”. Port suffixes and deprecated labels remain distinct.

To reproduce from the [pinned archive](https://raw.githubusercontent.com/Texera/Chowder/e054e86a6a239b15783b8884e675a5f43a36f38d/experiments/workflows/6k_set/plans_json.tar.gz), run:

```sh
python analyze.py plans_json.tar.gz replay
python -m unittest -v
```

The two generated files should match the committed CSV and JSON. These observations describe the archived graphs. Whole-workflow output comparisons use the eight runnable examples separately.
