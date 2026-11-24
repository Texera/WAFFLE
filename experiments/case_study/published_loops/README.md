# Loop boundaries in published plans

This structural census uses the [6K-Set from Chowder](https://github.com/Texera/Chowder/tree/e054e86a6a239b15783b8884e675a5f43a36f38d/experiments/workflows/6k_set). Its archive SHA-256 is pinned in `analyze.py`. [Pasta §6.2 and Table 4](https://doi.org/10.1145/3698832) report 6,148 workflows for analysis, 849 for materialization-size evaluations, and two executable workflows for clock-time evaluations. [Chowder Table 2](https://github.com/Texera/Chowder/blob/e054e86a6a239b15783b8884e675a5f43a36f38d/Chowder_Full_Technical_Report.pdf) reports 6,191 plans for the planner and six end-to-end workflows. The [released Pasta archive](https://github.com/Texera/Pasta/blob/288f25009f10a142300a14bcfd85710be8c87adf/pasta_experiment_inputs/mat_size_experiment_workflows.zip) contains 6,191 JSON files. A multiset comparison of SHA-256 hashes matched all 6,191 JSON payloads to the Chowder archive, including entries with different filenames. We count this as one source.

The archived plans retain operator display names, port identifiers and edges. The two boundary nodes in each eligible plan substitute dummy operators for the original configurations.

Of 6,191 entries, 1,159 had a directed path from a node labeled “Loop Start” to one labeled “Loop End”. The labels may include a prefix such as “Counting”. The screen identified 832 entries with exactly one start and one end and 327 with additional named boundaries. Every retained plan contains at least one connected start and end. Alternative names for loop operators can escape this screen.

We fingerprint each labeled directed graph using the multisets of its labeled predecessors and successors recursively, including the source and target ports of every edge. Node IDs, filenames, display coordinates and edge ordering do not affect the fingerprint. Different fingerprints distinguish different labeled structures. We retained one entry per fingerprint and examined 1,119 distinct labeled structures. The 798 single-pair structures allow an unambiguous boundary-type and side-link comparison. For the remaining 321, we recorded the number of distinct labeled starts and ends and the number of reachable start/end combinations. Reachability alone cannot identify the matching end of a nested or sequential loop.

The census found 39 distinct pairs of normalized boundary labels. The original eight output-checked examples cover pairs present in 423 structures. The ninth example adds the recursive/recursive pair found in 64 more, bringing coverage by boundary type to 487. Sharing a boundary type does not verify the computation on that plan's inputs. In 453 structures outside edges to and from the start-to-end paths pass through the corresponding boundary. The other 345 contain a side link. Some lead to legal side sinks.

The [multi-boundary inventory](multiple.csv) supplies the other 321 fingerprints. The [boundary-count histogram](../../../figures/published-loop-boundaries.pdf) groups the 1,119 plans by their number of labeled starts plus ends. The [single-pair census](plans.csv) records fingerprints, boundary labels and side-link counts. Archive member names are represented by hashes. The old 500-structure sample is retained in [sample.csv](sample.csv) with its original eight-example coverage flag. The [reference pairs](reference_pairs.json) identify the [original eight](../sources.json) and the [targeted recursive example](../recursive/source.json). Label normalization retains port suffixes and deprecated labels and treats “TableRow” as “Table Row”.

To reproduce from the [pinned archive](https://raw.githubusercontent.com/Texera/Chowder/e054e86a6a239b15783b8884e675a5f43a36f38d/experiments/workflows/6k_set/plans_json.tar.gz), run:

```sh
python analyze.py plans_json.tar.gz replay
python -m unittest -v
```

The three generated files should match the committed CSV and JSON. These observations describe the archived graphs. Whole-workflow output comparisons use ten runnable examples separately. The tenth uses the same recursive boundary pair as the ninth, leaving the coverage of 487 structures unchanged.
