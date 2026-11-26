"""One-hop graph operations and an independent shortest-path oracle."""

import ast
import hashlib
import json
from pathlib import Path
import sys

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from graphs import expression, preview
from protocol import COMMON, DOC

GRAPH = nx.karate_club_graph()
VERTICES = sorted(GRAPH)
NEIGHBORS = [sum(1 << u for u in GRAPH[v]) for v in VERTICES]
PUBLIC_ROOT = 0
HELD_OUT = (16, 33)
TASK = "karate_bfs"
ARITY = {"neighbors": 1, "union": 2, "difference": 2}


def fixture(root):
    return (0, 1 << root, 0, 0)


def expected(root):
    levels = {}
    for vertex, distance in nx.single_source_shortest_path_length(GRAPH, root).items():
        levels[distance] = levels.get(distance, 0) | (1 << vertex)
    return [[d, levels[d]] for d in sorted(levels)]


def set_expression(op, fields, jep):
    a = fields[0]
    if not jep:
        if op == "neighbors":
            return (
                "("
                + "+".join(
                    f"({1 << v} if ({a} & {mask}) else 0)"
                    for v, mask in enumerate(NEIGHBORS)
                )
                + ")"
            )
        b = fields[1]
        return f"({a} | {b})" if op == "union" else f"({a} & ~{b})"

    # The KNIME Math Formula node uses doubles. All subset integers are < 2^34.
    def bit(name, vertex):
        return f"mod(floor(${name}$/{1 << vertex}),2)"

    terms = []
    for v in VERTICES:
        if op == "neighbors":
            hits = "+".join(bit(a, u) for u in sorted(GRAPH[v]))
            flag = f"if(({hits})>0,1,0)"
        elif op == "union":
            flag = f"if(({bit(a, v)}+{bit(fields[1], v)})>0,1,0)"
        else:
            flag = f"({bit(a, v)}*(1-{bit(fields[1], v)}))"
        terms.append(f"({1 << v}*{flag})")
    return "(" + "+".join(terms) + ")"


def render(source, names, jep=False):
    if not isinstance(source, str) or len(source) > 300:
        raise ValueError("expected an expression string of at most 300 characters")
    fields = set(names)
    calls = {}

    class SetCalls(ast.NodeTransformer):
        def visit_Name(self, node):
            if node.id not in fields:
                raise ValueError(f"unknown column {node.id}")
            return node

        def visit_Call(self, node):
            op = node.func.id if isinstance(node.func, ast.Name) else None
            if op not in ARITY or len(node.args) != ARITY[op] or node.keywords:
                raise ValueError(
                    "use neighbors(column), union(col,col), or difference(col,col)"
                )
            if any(
                not isinstance(arg, ast.Name) or arg.id not in fields
                for arg in node.args
            ):
                raise ValueError(
                    "set operations take column names; store an intermediate first"
                )
            key = f"setcall{len(calls)}z"
            calls[key] = set_expression(op, [a.id for a in node.args], jep)
            return ast.copy_location(ast.Name(id=key, ctx=ast.Load()), node)

    tree = SetCalls().visit(ast.parse(source.strip(), mode="eval"))
    out = expression(ast.unparse(tree), fields | calls.keys(), jep)
    for key, value in calls.items():
        out = out.replace(f"${key}$" if jep else key, value)
    return out


def public_preview(plan, system, data):
    return preview(plan, system, data, render)


FORMAT_REMINDER = (
    "Scratch fields: the four names are i, u, v, and flag. Use those exact names "
    "for temporary storage. An assignment can overwrite an existing column but "
    "cannot create a column or an alias. "
    "Set operations: each argument must be a bare column name inside the expression "
    "string. To use the result of another call or expression as an argument, first "
    "store that result in an existing column, then pass its name. "
    "Submission format: return one valid JSON array of node arrays. Double-quote "
    "strings, separate consecutive elements with commas, and close every array. "
    "Omit trailing commas, comments, Markdown fences, and text outside the array."
)


OUTPUT_REMINDER = {
    "waffle": (
        "Output and state: emit evaluates its two expressions using the current "
        "fields. The values written to the output row can differ from the values "
        "kept in those fields. Emitting a row leaves the stored fields unchanged. "
        "The end node's assignments determine the state carried into the next iteration."
    ),
    "knime": (
        "Output and state: the collected row and the row carried into the next "
        "iteration can contain different values. Each node input reads only the "
        "row on its connected branch. A field assignment or filter affects its "
        "downstream nodes; sibling branches do not inherit it. The loop end reads "
        "its collection and feedback inputs independently."
    ),
}


LITERAL_REPEAT_REMINDER = (
    "Integer literals written in an expression must be between -1000 and 1000 "
    "inclusive. Input fields and computed results may hold larger values. "
    "Define the loop body once in the graph. On each iteration the engine runs "
    "those same nodes again using the state carried forward. Repetition across "
    "iterations requires no additional copies of the body nodes."
)


def prompt(system, clarified=False, state_and_branch=False, literal_repeat=False):
    common = COMMON.replace(
        "No function calls.",
        "Three additional functions are available identically in both systems. "
        "A vertex set is a nonnegative integer mask, with bit v for vertex v; 0 is empty. "
        "neighbors(a) is the union of all immediate neighbors of members of a in the "
        "fixed undirected graph; union(a,b) and difference(a,b) are set union and a minus b. "
        "Each function argument must be an existing column name. Store intermediate results "
        "in declared columns. These functions perform no traversal and hold no state.",
    )
    task = (
        "On Zachary's karate club friendship graph (NetworkX vertices 0 through 33), "
        "traverse all reachable vertices in increasing unweighted shortest-path distance "
        "from the given start vertex. Emit one (distance, vertex-set mask) pair per nonempty "
        "layer, including the starting vertex at distance zero. Each vertex belongs in "
        "exactly one layer. The input x is zero, y holds the singleton mask of the chosen "
        "start vertex, n and goal are unused zeros. Other starts will be tested."
    )
    documentation = DOC[system]
    if clarified or state_and_branch or literal_repeat:
        documentation += "\n\n" + FORMAT_REMINDER
    if state_and_branch or literal_repeat:
        documentation += "\n\n" + OUTPUT_REMINDER[system]
    if literal_repeat:
        documentation += "\n\n" + LITERAL_REPEAT_REMINDER
    return "\n\n".join(
        (
            common,
            documentation,
            "Task: " + task,
            f"Example input (x,y,n,goal): {fixture(PUBLIC_ROOT)}\n"
            f"Required output: {json.dumps(expected(PUBLIC_ROOT))}",
        )
    )


def controls():
    return {
        "waffle": [
            ["input"],
            ["start", 0, [["u", "y"]]],
            ["emit", 1, "x", "y"],
            [
                "end",
                2,
                [
                    ["v", "neighbors(y)"],
                    ["y", "difference(v,u)"],
                    ["u", "union(u,y)"],
                    ["x", "x+1"],
                ],
                "y != 0",
            ],
            ["sink", 3],
        ],
        "knime": [
            ["input"],
            ["set", 0, "u", "y"],
            ["start", 1],
            ["set", 2, "v", "neighbors(y)"],
            ["set", 3, "y", "difference(v,u)"],
            ["set", 4, "u", "union(u,y)"],
            ["set", 5, "x", "x+1"],
            ["set", 6, "flag", "1 if y != 0 else 0"],
            ["keep", 7, "flag"],
            ["end", 2, 8],
            ["sink", 9],
        ],
    }


def metadata():
    edges = sorted([min(u, v), max(u, v)] for u, v in GRAPH.edges)
    return dict(
        networkx=nx.__version__,
        graph="karate_club_graph",
        edges=edges,
        edge_sha256=hashlib.sha256(json.dumps(edges).encode()).hexdigest(),
        public_root=PUBLIC_ROOT,
        held_out_roots=HELD_OUT,
        expected={v: expected(v) for v in (PUBLIC_ROOT, *HELD_OUT)},
    )
