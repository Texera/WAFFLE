# Published loop plans

This November 24, 2026 snapshot extends the [fixed Chowder census](../published_loops/README.md) with public workflows from the three comparison systems. The [coverage file](snapshot/coverage.json) records the number examined, the evidence of iteration, and the retrieval failures for each source. The [plan files](plans/) contain the operator and connection records that support each positive identification. Each compressed manifest has a row for every inventoried item. A value of 1 in `loop_witness` means the plan contains the structural evidence defined below. A blank means the available representation did not settle the question.

| Source | Unit in the inventory | Evidence in the published plan |
| --- | --- | --- |
| KNIME Community Hub | One public workflow item ID at its observed revision | A directed port path from a native loop start to a native loop end in the same workflow or nested component |
| n8n template directory | One template ID in the union of the sitemap and the search API | A directed cycle of enabled nodes connected through main data ports |
| n8n community archive | One JSON file at a pinned revision | The same directed-cycle check |
| RapidMiner Studio 10.1 | One bundled process, identified by JAR digest, member path, and in-file ordinal | An enabled iteration operator with a subprocess and enabled ancestors |
| RapidMiner on GitHub | One distinct Git blob containing a process, with links to its published locations | The same subprocess check |

### Snapshot totals

| Collection | Inventoried | Readable | Records with loop evidence | Distinct recorded loop projections |
| --- | ---: | ---: | ---: | ---: |
| KNIME Community Hub | 54,955 workflow IDs | 54,955 node indexes, 9,145 candidate archives | 8,987 | 5,925 |
| n8n directory | 14,330 template IDs | 12,964 graphs including 45 partial | 2,949 | 2,831 |
| n8n community archive, earlier revision | 2,057 files | 2,047 graphs including 11 partial | 310 | 263 |
| n8n community archive, later revision | 2,061 files | 698 graphs plus 1,363 partial | 0 witnessed | 0 |
| RapidMiner bundled samples and tutorials | 605 processes | 605 | 102 | 95 |
| RapidMiner files on GitHub | 3,188 distinct external file blobs at 3,987 locations | 3,181 processes | 990 | 771 |

The earlier n8n community archive has 24 loop projections absent from the official directory under the same encoding. For RapidMiner, 39 recorded loop projections occur in both the bundled and GitHub collections. The manifest distinguishes inaccessible, incomplete, and unrecognized plans. For example, the n8n directory listed 1,364 paid templates and two public records with unsupported connection layouts. The snapshot covers one observed current state per Hub item and template. It does not enumerate their historical versions.

### Collection and verification

**KNIME.** Follow the current-state workflow listing to its terminal cursor. We use the public node registry to identify factories classified as LoopStart or LoopEnd, including cross-validation. We check the archive of every candidate containing both roles. Inside each archive we read the native workflow XML and match node instance IDs to metadata at the catalog revision. The plan projection records the operator types and the port connections in scopes that contain both roles. A start reaching an end establishes a path. With multiple boundaries it does not identify a unique matching pair. An opaque component, an unknown factory, or a loop implemented in user code can escape this screen. [KNIME catalog API](https://api.hub.knime.com/catalog/api-doc/catalog/openapi)

**n8n.** We visited each page of the directory API and merged the template IDs with the sitemap. Live pagination can repeat IDs or omit an item while the index changes. We counted the IDs actually observed. Paid entries were skipped. For public graphs, we discarded settings, credentials, pinned data, and annotations. We matched endpoints by unambiguous node names and excluded disabled nodes and connections on auxiliary ports. A partially readable graph can supply positive cycle evidence. It cannot rule out another cycle. A cycle is a property of the graph. It says nothing about whether particular input data traverses it. [Public sitemap](https://n8n.io/sitemap-workflows.xml) · [Template API](https://api.n8n.io/templates/search?rows=1&page=1)

We also inspected the workflow JSON directory in two revisions of a public community archive. The earlier revision preserves connections that do not resolve by node name in many files at the later revision. The manifests retain both revisions separately. Matching projection digests identify overlap with the official directory under our encoding. Different digests can still represent equivalent computations. [Earlier revision](https://github.com/Zie619/n8n-workflows/tree/54688735f7043504a561565f2c2df3e8a9e835cc/workflows) · [Later revision](https://github.com/Zie619/n8n-workflows/tree/94007c1445d9258a7da116646b79473e7c7c3282/workflows)

**RapidMiner.** We enumerated process files and embedded tutorial processes in Studio's bundled library and extension JARs. Separately, we searched GitHub's public code index for `operator extension:rmp`, partitioning queries by byte length to avoid the per-query retrieval cap. We verified Git blob hashes before parsing, collapsed identical file contents, and excluded the WAFFLE artifact's own translations. The program recognizes loop operators and the named validation and parameter-search operators listed in `rapidminer.py`. Opaque custom operators and processes outside the public index remain outside this count. The myExperiment search surfaced additional records, but access to their process files was blocked during this snapshot. They have no verified loop count here. [Studio samples](https://docs.rapidminer.com/latest/studio/getting-started/studio-samples.html) · [GitHub code search](https://docs.github.com/en/rest/search/search#search-code) · [myExperiment directory](https://www.myexperiment.org/workflows?query=rapidminer)

**Using the counts.** Catalog IDs, template IDs, bundled examples, and distinct file blobs describe different populations. We report them separately. The Chowder archive does not retain public Hub IDs suitable for cross-source deduplication. The ten published workflows with independently checked execution results remain a separate experiment. Manifests identify where to obtain the original plans. The JSON Lines projections omit executable parameters, inputs, credentials, and user annotations. SHA-256 covers the sorted compact JSON representation of each graph. It identifies the recorded projection and is sensitive to local node numbering.

### Reproduce

Use Python 3.12 with `requests` and `defusedxml`. The GitHub search also uses an authenticated `gh` CLI. Supply the Studio 10.1 distribution's `lib` directory for the vendor sample pass. A fresh cache takes a fresh snapshot of live directories. Reuse a cache to resume the same scan.

```sh
python collect.py knime cache
python knime_plans.py cache
python knime_nodes.py cache
python collect.py n8n cache
python n8n_archive.py cache
python rapidminer.py cache --studio-lib /path/to/rapidminer-studio/lib --github
python package_plans.py cache plans snapshot
```

To verify the published files without contacting the original catalogs, run `python verify_snapshot.py plans snapshot` from this directory. To test the boundary, cycle, and subprocess checks on positive and negative examples, run `python -m unittest -v`.

The packaging command independently checks KNIME reachability in reverse, n8n cycles by indegree elimination, and RapidMiner witnesses against the active subprocess ancestry. It also checks catalog cursor continuity, graph endpoints, and recorded revisions. Each local positive graph carries its source and SHA-256 digest.
