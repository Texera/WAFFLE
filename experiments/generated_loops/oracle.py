"""Independent checks using unlabeled adjacency and path-wise affine maps."""
from itertools import product


def topology(graph):
    """Decode serial diamonds using direction and degree alone."""
    ids = [op["operatorID"] for op in graph["operators"]]
    children = {v: [] for v in ids}
    parents = {v: [] for v in ids}
    for edge in graph["links"]:
        u, v = (edge[x]["operatorID"] for x in ("source", "target"))
        children[u].append(v)
        parents[v].append(u)

    def require(ok):
        if not ok:
            raise ValueError("graph is outside the serial-diamond grammar")

    roots = [v for v in ids if not parents[v]]
    require(len(roots) == 1 and len(set(ids)) == len(ids))
    root = roots[0]
    require(len(children[root]) == 1)
    tip = children[root][0]
    seen = {root, tip}
    signature = []
    while len(children[tip]) == 2:
        ends, lengths = [], []
        for v in children[tip]:
            hops = 0
            while len(parents[v]) == 1:
                require(v not in seen and len(children[v]) == 1)
                seen.add(v)
                hops += 1
                v = children[v][0]
            ends.append(v)
            lengths.append(hops)
        require(ends[0] == ends[1] and ends[0] not in seen and len(parents[ends[0]]) == 2)
        tip = ends[0]
        seen.add(tip)
        signature.append(tuple(sorted(lengths)))
    # Reducer, LoopEnd, sorted sink.
    for _ in range(3):
        require(len(children[tip]) == 1)
        tip = children[tip][0]
        require(tip not in seen and len(parents[tip]) == 1)
        seen.add(tip)
    require(not children[tip] and seen == set(ids) and signature)
    return tuple(signature)


def expected(family, policy, arms, values):
    # Enumerate source-to-reducer paths. Compose an affine map per path
    # without running node code, routing a row, or interpreting loop cells.
    maps = []
    for choices in product((0, 1), repeat=len(arms)):
        a, b = 1, 0
        for stage, (lengths, side) in enumerate(zip(arms, choices), 1):
            n = lengths[side]
            if side == 0:
                shift = sum((stage + j) * 2 ** (n - 1 - j) for j in range(n))
                a, b = a * 2 ** n, b * 2 ** n + shift
            else:
                b -= n * stage + n * (n - 1) // 2
        maps.append((a, b))
    expanded = [(i % 3, a * x + b) for i, x in enumerate(values) for a, b in maps]
    xs = sorted(x for _, x in expanded)
    if family == "stopping":
        # The required order statistic gives the first passing integer
        # directly. Clamp it to the inclusive observation window [0,5].
        rank = ((2 + policy) * len(xs) + 5) // 6
        last = max(0, min(5, xs[rank - 1]))
        return [(k, sum(x <= k for x in xs)) for k in range(last + 1)]
    if family == "aggregation":
        groups = [[x for g, x in expanded if g == k] for k in range(3)]
        return [(k, (sum(g), sum(map(abs, g)), sum(x**2 for x in g))[policy])
                for k, g in enumerate(groups)]
    if family != "search":
        raise ValueError(family)
    rows = []
    for k in range(-2, 3):
        residuals = [x - k for x in xs]
        absolute = sum(map(abs, residuals))
        objectives = (absolute, sum(r*r for r in residuals),
                      absolute - sum(min(0, r) for r in residuals))
        rows.append((k, objectives[policy]))
    return rows
