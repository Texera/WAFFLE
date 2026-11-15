"""Brute-force oracle validating Theorem 5.1 (X = Y for well-formed loop
blocks) and measuring the search-space reduction of recursive scheduling.

Model (paper Section 5.1):
  - A workflow is a DAG. A *region plan* labels every edge pipelined or
    materialized (some edges may be *forced* materialized: blocking ports,
    loop boundary edges).
  - A *region* is a connected component after removing materialized edges.
  - Each materialized edge induces a region edge (multigraph). A plan is
    *schedulable* iff the region graph is acyclic (a materialized edge with
    both endpoints in one region is a self-loop, i.e., a cycle).

Methods (paper Section 5.4):
  - X (global): force the loop boundary edges materialized, enumerate all
    labelings of the remaining edges over the WHOLE workflow, keep the
    schedulable ones.
  - Y (recursive, ours): schedule the body alone and the workflow with the
    block collapsed into one operator, innermost block first; compose.

Well-formedness (paper Section 3.4): single entering edge into LoopStart,
single leaving edge out of LoopEnd, no side edges, and a directed path
LoopStart ~> LoopEnd through the body (the *spine*).

Run:  python pasta_oracle.py            (self-tests + full sweep + table)
      python pasta_oracle.py --quick    (self-tests + small sweep)
"""

import itertools
import random
import sys
import time
from collections import defaultdict


# ---------------------------------------------------------------- model

def regions(nodes, edges, materialized):
    """Union-find over pipelined edges -> node -> region id."""
    parent = {v: v for v in nodes}

    def find(v):
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    for (u, v) in edges:
        if (u, v) not in materialized:
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[ru] = rv
    return {v: find(v) for v in nodes}


def schedulable(nodes, edges, materialized):
    """Region graph acyclic? Kahn's algorithm on the region multigraph."""
    reg = regions(nodes, edges, materialized)
    succ = defaultdict(list)
    indeg = defaultdict(int)
    regs = set(reg.values())
    for (u, v) in materialized:
        ru, rv = reg[u], reg[v]
        if ru == rv:
            return False                       # self-loop
        succ[ru].append(rv)
        indeg[rv] += 1
    queue = [r for r in regs if indeg[r] == 0]
    seen = 0
    while queue:
        r = queue.pop()
        seen += 1
        for s in succ[r]:
            indeg[s] -= 1
            if indeg[s] == 0:
                queue.append(s)
    return seen == len(regs)


def enumerate_plans(nodes, edges, forced):
    """All schedulable plans; a plan is the frozenset of materialized edges.
    `forced` edges are materialized in every plan."""
    free = [e for e in edges if e not in forced]
    plans = set()
    for mask in itertools.product((False, True), repeat=len(free)):
        mat = set(forced)
        mat.update(e for e, m in zip(free, mask) if m)
        if schedulable(nodes, edges, frozenset(mat)):
            plans.add(frozenset(mat))
    return plans


# ------------------------------------------------------------- methods

class Loop:
    """A loop block: LoopStart ls, LoopEnd le, body nodes (strictly between)."""

    def __init__(self, ls, le, body):
        self.ls, self.le, self.body = ls, le, set(body)

    def members(self):
        return {self.ls, self.le} | self.body


def boundary_edges(edges, loop):
    mem = loop.members()
    into = [(u, v) for (u, v) in edges if v == loop.ls and u not in mem]
    outof = [(u, v) for (u, v) in edges if u == loop.le and v not in mem]
    return into + outof


def method_X(nodes, edges, loops, forced=frozenset()):
    forced = set(forced)
    for lp in loops:
        forced.update(boundary_edges(edges, lp))
    return enumerate_plans(nodes, edges, frozenset(forced))


def collapse(nodes, edges, loop, label):
    """Collapse loop members into a single node `label`."""
    mem = loop.members()
    n2 = [v for v in nodes if v not in mem] + [label]
    e2 = []
    for (u, v) in edges:
        if u in mem and v in mem:
            continue
        uu = label if u in mem else u
        vv = label if v in mem else v
        e2.append((uu, vv))
    return n2, e2


def method_Y(nodes, edges, loops, forced=frozenset()):
    """Recursive scheduling, innermost block first. Returns the composed
    set of full-workflow plans."""
    if not loops:
        return enumerate_plans(nodes, edges, frozenset(forced))
    # innermost = a loop with no other loop inside its body
    inner = next(lp for lp in loops
                 if not any(o is not lp and o.members() <= lp.body
                            for o in loops))
    mem = inner.members()
    body_nodes = sorted(mem)
    body_edges = [(u, v) for (u, v) in edges if u in mem and v in mem]
    body_forced = frozenset(e for e in forced if e in body_edges)
    body_plans = enumerate_plans(body_nodes, body_edges, body_forced)

    label = f"L({inner.ls})"
    outer_nodes, outer_edges = collapse(nodes, edges, inner, label)
    bnd = boundary_edges(edges, inner)
    # boundary edges keep their identity through the collapse mapping
    bmap = {}
    for (u, v) in bnd:
        uu = label if u in mem else u
        vv = label if v in mem else v
        bmap[(uu, vv)] = (u, v)
    outer_forced = set(e for e in forced if e in outer_edges)
    outer_forced.update(bmap.keys())
    # remaining loops must see the collapsed node in place of the inner
    # block's members, or the next collapse operates on a stale node set
    outer_loops = []
    for lp in loops:
        if lp is inner:
            continue
        if mem <= lp.body:
            outer_loops.append(Loop(lp.ls, lp.le, (lp.body - mem) | {label}))
        else:
            outer_loops.append(lp)
    outer_plans = method_Y(outer_nodes, outer_edges, outer_loops,
                           frozenset(outer_forced))

    composed = set()
    for op in outer_plans:
        # translate collapsed edges back to original ids
        op_orig = frozenset(bmap.get(e, e) for e in op)
        for bp in body_plans:
            composed.add(op_orig | bp)
    return composed


# ----------------------------------------------------------- generators

def gen_wellformed(rng, n_pre, n_body, n_post, bypass=False, spine=True,
                   p_edge=0.4, p_block=0.15):
    """One loop; guaranteed spine unless spine=False (then the body feeds
    LoopEnd from an internal source and has NO LoopStart path)."""
    pre = [f"P{i}" for i in range(n_pre)]
    body = [f"B{i}" for i in range(n_body)]
    post = [f"Q{i}" for i in range(n_post)]
    ls, le = "LS", "LE"
    nodes = pre + [ls] + body + [le] + post
    edges = set()
    # chains guarantee connectivity
    for chain in (pre, post):
        for a, b in zip(chain, chain[1:]):
            edges.add((a, b))
    edges.add((pre[-1], ls))
    edges.add((le, post[0]))
    sink, src = [], []
    if spine:
        edges.add((ls, body[0]))
        for a, b in zip(body, body[1:]):
            edges.add((a, b))
        edges.add((body[-1], le))
    else:
        # split body: LS feeds a sink half; a source half feeds LE; any
        # extra edge from the LS side to the LE side would restore the
        # spine, so those pairs are excluded below
        half = max(1, len(body) // 2)
        sink, src = body[:half], body[half:] or [body[-1]]
        edges.add((ls, sink[0]))
        for a, b in zip(sink, sink[1:]):
            edges.add((a, b))
        for a, b in zip(src, src[1:]):
            edges.add((a, b))
        edges.add((src[-1], le))
    ls_side = {ls} | set(sink)
    le_side = set(src) | {le}
    # extra random forward edges (keep DAG, keep well-formedness)
    order = {v: i for i, v in enumerate(nodes)}

    def zone(v):
        if v in body or v in (ls, le):
            return "in"
        return "out"

    for u, v in itertools.combinations(nodes, 2):
        if order[u] >= order[v] or (u, v) in edges:
            continue
        if v == ls or u == le:
            continue                            # single entry / single exit
        inz, outz = zone(u), zone(v)
        if {inz, outz} == {"in", "out"}:
            continue                            # no side edges
        if not spine and u in ls_side and v in le_side:
            continue                            # keep the spine broken
        if inz == "out" and outz == "out":
            if bypass and order[u] < order[ls] and order[v] > order[le] \
               and rng.random() < 0.5:
                edges.add((u, v))               # bypass edge
            elif rng.random() < p_edge and not (order[u] < order[ls] < order[v]):
                edges.add((u, v))
        elif rng.random() < p_edge:
            edges.add((u, v))
    if bypass and not any(order[u] < order[ls] and order[v] > order[le]
                          for (u, v) in edges):
        edges.add((pre[0], post[-1]))           # guarantee one bypass
    edges = sorted(edges)
    forced = frozenset(e for e in edges if rng.random() < p_block
                       and e not in boundary_edges(edges, Loop(ls, le, body)))
    return nodes, edges, [Loop(ls, le, set(body))], forced


def gen_nested(rng, p_block=0.1):
    """Outer loop whose body contains an inner loop; both with spines."""
    nodes = ["P0", "LS1", "A0", "LS2", "C0", "C1", "LE2", "A1", "LE1", "Q0"]
    base = [("P0", "LS1"), ("LS1", "A0"), ("A0", "LS2"), ("LS2", "C0"),
            ("C0", "C1"), ("C1", "LE2"), ("LE2", "A1"), ("A1", "LE1"),
            ("LE1", "Q0")]
    edges = set(base)
    if rng.random() < 0.5:
        edges.add(("C0", "LE2") if rng.random() < 0.5 else ("LS2", "C1"))
    if rng.random() < 0.5:
        edges.add(("LS1", "A1") if rng.random() < 0.5 else ("A0", "A1"))
    edges = sorted(edges)
    inner = Loop("LS2", "LE2", {"C0", "C1"})
    outer = Loop("LS1", "LE1", {"A0", "LS2", "C0", "C1", "LE2", "A1"})
    forced = frozenset(e for e in edges if rng.random() < p_block
                       and e not in boundary_edges(edges, inner)
                       and e not in boundary_edges(edges, outer))
    return nodes, edges, [inner, outer], forced


def gen_sequential(rng, p_block=0.1):
    """Two loops one after the other, plus an optional whole-workflow bypass."""
    nodes = ["P0", "LS1", "B0", "LE1", "M0", "LS2", "C0", "LE2", "Q0"]
    edges = {("P0", "LS1"), ("LS1", "B0"), ("B0", "LE1"), ("LE1", "M0"),
             ("M0", "LS2"), ("LS2", "C0"), ("C0", "LE2"), ("LE2", "Q0")}
    if rng.random() < 0.5:
        edges.add(("P0", "Q0"))
    edges = sorted(edges)
    l1 = Loop("LS1", "LE1", {"B0"})
    l2 = Loop("LS2", "LE2", {"C0"})
    forced = frozenset(e for e in edges if rng.random() < p_block
                       and e not in boundary_edges(edges, l1)
                       and e not in boundary_edges(edges, l2))
    return nodes, edges, [l1, l2], forced


# ------------------------------------------------------------ self-test

def selftest():
    # Hand-computed instance: P0->LS->B0, B1->LE->Q0, bypass P0->Q0,
    # NO B0->B1 (spineless).  X = 8 (all labelings schedulable);
    # Y rejects the 4 plans that pipeline the bypass -> Y = 4.
    nodes = ["P0", "LS", "B0", "B1", "LE", "Q0"]
    edges = [("P0", "LS"), ("LS", "B0"), ("B1", "LE"), ("LE", "Q0"),
             ("P0", "Q0")]
    loops = [Loop("LS", "LE", {"B0", "B1"})]
    X = method_X(nodes, edges, loops)
    Y = method_Y(nodes, edges, loops)
    assert len(X) == 8 and len(Y) == 4 and Y < X, (len(X), len(Y))

    # Add the spine B0->B1: sets must coincide.
    edges2 = edges + [("B0", "B1")]
    X2 = method_X(nodes, edges2, loops)
    Y2 = method_Y(nodes, edges2, loops)
    assert X2 == Y2, (len(X2), len(Y2))

    # Drop the bypass instead (still spineless): sets coincide too --
    # the mismatch needs bypass AND a missing spine.
    edges3 = edges[:-1]
    assert method_X(nodes, edges3, loops) == method_Y(nodes, edges3, loops)
    print("self-tests passed "
          f"(counterexample: X={len(X)} plans, Y={len(Y)}; "
          f"with spine: {len(X2)}={len(Y2)})")


# ---------------------------------------------------------------- sweep

def sweep(cases, seed=42):
    rng = random.Random(seed)
    stats = defaultdict(int)
    mism = 0
    for i in range(cases):
        kind = rng.choice(["single", "single", "single",
                           "bypass", "bypass", "nested", "sequential"])
        if kind == "single":
            g = gen_wellformed(rng, rng.randint(1, 3), rng.randint(1, 3),
                               rng.randint(1, 3))
        elif kind == "bypass":
            g = gen_wellformed(rng, rng.randint(2, 3), rng.randint(1, 3),
                               rng.randint(2, 3), bypass=True)
        elif kind == "nested":
            g = gen_nested(rng)
        else:
            g = gen_sequential(rng)
        nodes, edges, loops, forced = g
        X = method_X(nodes, edges, loops, forced)
        Y = method_Y(nodes, edges, loops, forced)
        stats[kind] += 1
        if X != Y:
            mism += 1
            print(f"MISMATCH case {i} ({kind}): |X|={len(X)} |Y|={len(Y)}")
    print(f"sweep: {cases} well-formed workflows "
          f"({dict(stats)}), mismatches: {mism}")
    return mism


def spineless_sweep(cases, seed=7):
    """Same sweep but with the spine deliberately broken and a bypass
    guaranteed: mismatches are EXPECTED (X strictly larger)."""
    rng = random.Random(seed)
    mism = 0
    for _ in range(cases):
        nodes, edges, loops, forced = gen_wellformed(
            rng, rng.randint(2, 3), 2, rng.randint(2, 3),
            bypass=True, spine=False, p_block=0.0)
        X = method_X(nodes, edges, loops, forced)
        Y = method_Y(nodes, edges, loops, forced)
        if X != Y:
            assert Y < X          # Y only ever loses plans, never invents
            mism += 1
    print(f"spineless sweep: {cases} cases, {mism} mismatches "
          f"(expected: all of them)")
    return mism


def scaling_table(max_free=22):
    """Chain workflow with one bypass edge: pre-chain -> loop(chain body)
    -> sink, plus bypass pre[0] -> sink. Free edges split EVENLY between
    the body module (LS -> chain -> LE: half+2 edges) and the collapsed
    rest (pre-chain + bypass: half+2 edges). Search-space size and
    enumeration time, X vs Y."""
    print(f"{'free edges':>10} {'X space':>10} {'Y space':>10} "
          f"{'X time(s)':>10} {'Y time(s)':>10}")
    rows = []
    for half in range(3, (max_free - 4) // 2 + 1):
        pre = [f"P{i}" for i in range(half + 2)]
        body = [f"B{i}" for i in range(half + 1)]
        post = ["Q0"]
        nodes = pre + ["LS"] + body + ["LE"] + post
        edges = ([*zip(pre, pre[1:])] + [(pre[-1], "LS"), ("LS", body[0])]
                 + [*zip(body, body[1:])] + [(body[-1], "LE"), ("LE", "Q0")]
                 + [(pre[0], "Q0")])
        loops = [Loop("LS", "LE", set(body))]
        free = len(edges) - 2                      # 2 boundary edges forced
        t0 = time.perf_counter()
        X = method_X(nodes, edges, loops)
        tx = time.perf_counter() - t0
        t0 = time.perf_counter()
        Y = method_Y(nodes, edges, loops)
        ty = time.perf_counter() - t0
        assert X == Y
        body_free = len(body) + 1                  # LS->b0..b_last->LE chain
        outer_free = free - body_free
        assert body_free == outer_free             # even split
        rows.append((free, 2 ** free, 2 ** body_free + 2 ** outer_free,
                     tx, ty))
        print(f"{free:>10} {2**free:>10} "
              f"{2**body_free + 2**outer_free:>10} {tx:>10.3f} {ty:>10.3f}")
    return rows


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    selftest()
    assert sweep(500 if quick else 5000) == 0
    assert spineless_sweep(100 if quick else 500) > 0
    scaling_table(16 if quick else 22)
    print("ALL CHECKS PASSED")
