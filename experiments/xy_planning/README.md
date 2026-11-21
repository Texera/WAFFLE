# Global (X) versus modular (Y) planning

Sections 7.5 and 7.6 now include two 100-operator workflows. The [scale experiment](scale/README.md) records the added graph layouts, direct X/Y measurements, time limit and independent cost checks. The original six-workflow experiment is documented below.

Six compiled native workflows contain aggregation/join groups inside and before one loop. Group counts are 1/1, 2/2, 3/3, 4/4, 1/4 and 4/1, giving 12, 20, 28, 36, 24 and 24 physical operators. The compiler supplies actual blocking ports; the research adapter adds the two loop-boundary cuts.

Pruning is on. Every original operator has estimate 1, each region costs its maximum operator estimate, and Y's collapsed macro costs zero. X and Y find the same minimum costs: 7, 11, 15, 19, 13 and 13. These are model estimates, not runtime measurements.

## Recorded run

Revision ddc04792511838d06f982ced01641e7d06ce6524; November 6, 2026 UTC. Three fresh JBR 17.0.14 JVMs on Windows/AMD Ryzen 9 9950X. Each JVM runs 20 warm-up pairs and 100 measured pairs per graph. Strategy order alternates, and graph order is deterministically shuffled. No CPU isolation.

All 3,600 measured plans are retained, including 234 that overlap garbage collection. total_ns includes decomposition, search/cost evaluation/pruning, and composition. Compilation and workflow execution are excluded.

The figure shows pooled medians over 300 measurements per graph/strategy. Whiskers span the three JVM medians, not confidence intervals. Markers on the logarithmic axis represent categories.

## Files and verification

- measurements.csv: 13 original measurement columns from the three raw files, without filtering rows.
- raw/: original per-fork CSVs, logical graphs, physical manifests, metadata and independent-oracle verification.
- provenance.json: original raw-file hashes and benchmark settings.
- runner/ and scala/: source snapshots for inspection. Machine paths in the copied runner are normalized; execute the pinned checkout rather than this snapshot.
- plot.py: validates sample keys, counts, timers, costs and state counts, then rebuilds the figure.

The independent checker enumerates each sealed module, validates the composed minimum on the whole graph, and enumerates the whole graph for the two smallest cases. It checks all 3,600 returned plans. Run the root tools/verify_results.py to repeat these checks in temporary files.

## Rerun

Prepare the public planning checkout and build/configure it with its own README. The original runner requires Windows PowerShell, sbt on PATH, JDK 17 and a working Texera Python environment:

```sh
python tools/prepare_engine.py planning work/planning
python tools/run_planning.py --repo work/planning --java-home /path/to/jdk17 --python /path/to/texera-python
```

The wrapper supplies native-large, three forks, 20 warm-ups and 100 measured repetitions. New data goes to the checkout's target/xy-planning-native-large/ timestamped directory. --dry-run prints the command without starting it.

The research harness directly calls the planner. The normal dispatcher at this revision requires materialized loop execution. These timings do not show execution of the returned pipelined plans, and apply only to this workflow family and cost model.
