# When workflow branches rejoin

Input: the published [Chowder 6K-Set archive](https://github.com/Texera/Chowder/tree/e054e86a6a239b15783b8884e675a5f43a36f38d/experiments/workflows/6k_set). One observation is one archived JSON plan. Operator implementations and loop control values are unavailable in this collection. We inspect each recorded directed topology without executing its operators.

    curl -L https://raw.githubusercontent.com/Texera/Chowder/e054e86a6a239b15783b8884e675a5f43a36f38d/experiments/workflows/6k_set/plans_json.tar.gz -o plans_json.tar.gz
    python -m unittest -v test_topologies
    python analyze.py plans_json.tar.gz

The script verifies the input SHA-256 and reads all 6,191 JSON files directly from the archive. Parallel port links between the same ordered pair of operators count as one edge. A merge counts if two distinct predecessors have a common ancestor, including either predecessor itself. This detects direct and indirect paths from the same operator. Independent inputs that meet at a join do not suffice. A second implementation propagates path counts from each source and checks agreement for every graph. Counts describe archive entries, without assuming distinct topologies or independent sampling. The graphs admit a duplicate if one assignment is forwarded on every path from the split. How often a workflow actually sent a control message is unknown.

The four bins use the number of recorded logical operators, including disconnected components. The total with a reconvergence is 3,115 of 6,191 graphs. All graphs passed endpoint and acyclicity checks. The script prints the full summary in the format of [results.json](results.json).
