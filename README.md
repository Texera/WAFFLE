# WAFFLE: control blocks in workflow systems

Experimental scripts, data, recorded results, and figure generation for the WAFFLE paper. The prototype extends [Apache Texera](https://github.com/apache/texera). This is a research artifact; it is not an Apache Software Foundation release.

| Experiment | Directory | Recorded evidence |
| --- | --- | --- |
| §7.2: translate KNIME loop examples | [case_study](experiments/case_study) | WAFFLE, n8n, and RapidMiner each match all 241 KNIME scalar output rows across eight examples; the [recursive example](experiments/case_study/recursive) adds 40 rows and the [hierarchy workflow](experiments/case_study/hierarchy) adds 11 rows with changing feedback tables (292 final rows in ten workflows) |
| §7.2: published loop plans | [published_loops](experiments/case_study/published_loops) | 1,198 distinct plans with connected boundaries, including 801 single-pair plans with 41 boundary-type combinations |
| §7.2: agent-authored workflows | [agent_authoring](experiments/agent_authoring) | Paired WAFFLE and KNIME graph submissions for six numeric loop tasks, native output checks on hidden inputs, and a worked-example sensitivity comparison |
| §7.2: public catalogs | [public_catalogs](experiments/case_study/public_catalogs) | Source inventories and verified structural loop evidence from three comparison systems |
| §7.2: generated loop computations | [generated_loops](experiments/generated_loops) | 16,104 graphs on three inputs each, with every visited score and output row checked |
| Supplemental K-means loop rules | [loop_policies](experiments/loop_policies) | Four control rules on four inputs across four engines, with fixed-range and score-threshold comparisons |
| §7.3: create and adapt loops | [user_study](experiments/user_study) | [Group results from ten included responses](experiments/user_study/results/group-results.csv), protocol, starters, fallbacks and author dry runs. |
| §7.4: control-variable delivery and binding | [control_messages](experiments/control_messages) | Seven complete workflow experiments for scoped bindings, 12 controlled receiver traces, and 378 first-tuple bindings in 18 runs on each of the original and write-once runtimes |
| §§7.5–7.6: global (X) versus modular (Y) planning | [xy_planning](experiments/xy_planning) | 3,600 measured plans on the original six workflows, extended tests up to 100 operators with increased branching and 164 with longer filter chains; all completed pairs attain the same verified minimum |
| §§7.7–7.8: loop versus explicit body copies | [loop_execution](experiments/loop_execution) | 84 native executions, including 14 warm-ups; seven settings up to 20,000 tuples; separate graph-construction checks through 131,072 candidates; all outputs checked |
| Scheduling supplement | [scheduling_oracle](experiments/scheduling_oracle) | Independent scheduling model |

The [Section 7 data index](SECTION7-DATA.md) maps each subsection, figure and table to the files used for it.

## Check the saved results

Python 3.12 and Git are required. These commands do not start Texera or KNIME.

```sh
git clone https://github.com/Texera/WAFFLE.git
cd WAFFLE
python -m venv .venv
# Windows PowerShell: .venv/Scripts/Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt
python tools/verify_results.py
python tools/make_figures.py
```

The checker rebuilds the published-plan counts, compares the four systems’ saved outputs and policy traces, checks generated graphs and worker observations, validates both execution-time batches, and rechecks planner results. It uses temporary directories so saved evidence is not overwritten. Generated figures are written to [figures/](figures/). Section 7 follows published chart types from the group: bars for counts and task comparisons and lines for scaling or ordered measurements ([Pasta, Figs. 16–17 and 20](https://doi.org/10.1145/3698832)). Execution times use box-and-whisker plots ([Amber, Figs. 10–11](https://www.vldb.org/pvldb/vol13/p740-kumar.pdf#page=10)). The WAFFLE boxes use quartiles and the full observed range of five runs.

## Run new measurements

The native runs were collected on Windows with JDK 17 and Python 3.12. A configured Texera build, its Python operator dependencies, and its storage services are required. Follow the README and build instructions in the pinned checkout before running the experiment-specific commands below. The recorded environment and scope are described in each experiment README.

Prepare the exact source trees:

```sh
python tools/prepare_engine.py runtime work/runtime
python tools/prepare_engine.py planning work/planning
```

[implementation.lock.json](implementation.lock.json) pins both source trees. The runtime is reconstructed from a public Texera commit plus [runtime.patch](patches/runtime.patch). The helper checks the patch checksum and the full resulting Git tree. It leaves the patch staged. The planning revision is fetched directly. Both destinations must be new directories.

Then follow:

- [Runtime setup and loop/copies experiment](experiments/loop_execution/README.md)
- [Control messages at a merge](experiments/control_messages/README.md)
- [KNIME source retrieval, execution and translation](experiments/case_study/README.md)
- [X/Y planning experiment](experiments/xy_planning/README.md)

Use a new output directory for every rerun. Captured workflow JSON contains portable path labels and must be regenerated for the new machine. The saved CSV and native JSONL measurements retain their original bytes. Metadata paths have been normalized, and runner arguments made configurable; [EXPORT.json](EXPORT.json) records that export. Hashes labeled as captured refer to the original run, while package input hashes refer to the published files.

## What the results establish

The case study checks ten selected loop examples, not all KNIME workflows or ease of use. The planning experiment compares two searches on one workflow family with a fixed cost model. It does not measure execution of the returned plans. The execution experiment uses materialized edges and one concurrent region. Explicit body copies were faster in all six recorded settings; the loop representation stays at five logical operators as the iteration count grows. These results do not establish a universal runtime advantage for loops.

No benchmark numbers are illustrative or simulated. The saved measurements are from the runs identified in the provenance files; running the verification commands does not collect new performance measurements.

## Sources and license

The code is distributed under [Apache License 2.0](LICENSE), with upstream notices in [NOTICE](NOTICE). See [THIRD_PARTY.md](THIRD_PARTY.md) for Texera and KNIME attribution and the provenance of example data. The paper manuscript, private review comments and individual study records are held separately.
