# WAFFLE: control blocks in workflow systems

Experimental scripts, data, recorded results, and figure generation for the WAFFLE paper. The prototype extends [Apache Texera](https://github.com/apache/texera). This is a research artifact; it is not an Apache Software Foundation release.

| Experiment | Directory | Recorded evidence |
| --- | --- | --- |
| §7.2: translate KNIME loop examples | [case_study](experiments/case_study) | WAFFLE, n8n, and RapidMiner each match all 241 KNIME scalar output rows across eight examples; the [recursive example](experiments/case_study/recursive) adds 40 checked rows across two result tables |
| §7.2: published loop plans | [published_loops](experiments/case_study/published_loops) | 798 distinct labeled structures, 39 boundary-type pairs, compared with nine runnable examples |
| §7.2: generated loop computations | [generated_loops](experiments/generated_loops) | 2,800 graphs on three inputs each, with every visited score and output row checked |
| Supplemental K-means loop rules | [loop_policies](experiments/loop_policies) | Four control rules on four inputs across four engines, with fixed-range and score-threshold comparisons |
| §7.3: create and adapt loops | [user_study](experiments/user_study) | Proposed protocol only; no participant results |
| §7.4: control-variable delivery and binding | [control_messages](experiments/control_messages) | Eight merge workflows, 255 arrival orders under two policies, and 90 first-tuple bindings in 12 multiworker runs |
| §§7.5–7.6: global (X) versus modular (Y) planning | [xy_planning](experiments/xy_planning) | Six compiled workflows, three JVMs, 3,600 measured plans; equal minimum costs |
| §§7.7–7.8: loop versus explicit body copies | [loop_execution](experiments/loop_execution) | 72 native executions, including 12 warm-ups; all outputs checked |
| Scheduling supplement | [scheduling_oracle](experiments/scheduling_oracle) | Independent scheduling model |

The user-study protocol is included, but no participant measurements have been collected here. Source data, workflow definitions, raw outputs, checks, and plotting code for the other experiments are included.

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

The checker compares every case-study output, checks the merge-worker traces, validates all 72 loop-versus-copies records, and rechecks all 3,600 planning results with an independent oracle. It uses temporary directories so saved evidence is not overwritten. Generated figures are written to [figures/](figures/).

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

The case study checks eight selected loop examples, not all KNIME workflows or ease of use. The planning experiment compares two searches on one workflow family with a fixed cost model. It does not measure execution of the returned plans. The execution experiment uses materialized edges and one concurrent region. Explicit body copies were faster in all six recorded settings; the loop representation stays at five logical operators as the iteration count grows. These results do not establish a universal runtime advantage for loops.

No benchmark numbers are illustrative or simulated. The saved measurements are from the runs identified in the provenance files; running the verification commands does not collect new performance measurements.

## Sources and license

The code is distributed under [Apache License 2.0](LICENSE), with upstream notices in [NOTICE](NOTICE). See [THIRD_PARTY.md](THIRD_PARTY.md) for Texera and KNIME attribution and the provenance of example data. This repository contains no paper manuscript, private review comments, or participant data.
