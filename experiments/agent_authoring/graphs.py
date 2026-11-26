"""Validate the graph format and execute the public example for repair feedback."""

import ast
from protocol import FIELDS, LIMIT

OPS = {
    ast.Add: "+",
    ast.Sub: "-",
    ast.Mult: "*",
    ast.Mod: "%",
    ast.Lt: "<",
    ast.LtE: "<=",
    ast.Gt: ">",
    ast.GtE: ">=",
    ast.Eq: "==",
    ast.NotEq: "!=",
}


def expression(source, names, jep=False):
    if not isinstance(source, str) or len(source) > 300:
        raise ValueError("expected an expression string of at most 300 characters")

    def visit(node):
        if isinstance(node, ast.Name) and node.id in names:
            return "$" + node.id + "$" if jep else node.id
        if (
            isinstance(node, ast.Constant)
            and type(node.value) in (int, bool)
            and abs(node.value) <= 1000
        ):
            return str(int(node.value))
        if isinstance(node, ast.UnaryOp) and type(node.op) in (
            ast.Not,
            ast.USub,
            ast.UAdd,
        ):
            op = {ast.Not: "!" if jep else "not ", ast.USub: "-", ast.UAdd: "+"}[
                type(node.op)
            ]
            return "(" + op + visit(node.operand) + ")"
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            a, b = visit(node.left), visit(node.right)
            if jep and isinstance(node.op, ast.Mod):
                return f"mod((mod({a},{b})+{b}),{b})"
            return f"({a} {OPS[type(node.op)]} {b})"
        if isinstance(node, ast.Compare) and all(type(op) in OPS for op in node.ops):
            operands = [visit(it) for it in [node.left, *node.comparators]]
            parts = [
                f"({operands[i]} {OPS[type(op)]} {operands[i + 1]})"
                for i, op in enumerate(node.ops)
            ]
            return "(" + (" && " if jep else " and ").join(parts) + ")"
        if isinstance(node, ast.BoolOp):
            sep = (
                (" && " if jep else " and ")
                if isinstance(node.op, ast.And)
                else (" || " if jep else " or ")
            )
            return "(" + sep.join(visit(v) for v in node.values) + ")"
        if isinstance(node, ast.IfExp):
            t, a, b = visit(node.test), visit(node.body), visit(node.orelse)
            return f"if({t},{a},{b})" if jep else f"({a} if {t} else {b})"
        raise ValueError("unsupported expression element: " + ast.unparse(node))

    return visit(ast.parse(source.strip(), mode="eval").body)


def evaluate(source, values):
    return eval(expression(source, values), {"__builtins__": {}}, values)


def initial(data):
    return dict(zip(FIELDS, [*data, 0, 0, 0, 0]))


def assign(pairs, state):
    if not isinstance(pairs, list):
        raise ValueError("assignments must be an array of pairs")
    for name, expr in pairs:
        if name not in FIELDS:
            raise ValueError(f"unknown writable field {name}")
        state[name] = evaluate(expr, state)


def validate(plan, system):
    if not isinstance(plan, list) or not 4 <= len(plan) <= 64:
        raise ValueError("expected a graph array with 4 to 64 nodes")
    sizes = (
        {"input": 1, "start": 3, "emit": 4, "end": 4, "sink": 2}
        if system == "waffle"
        else {"input": 1, "start": 2, "set": 4, "keep": 3, "end": 3, "sink": 2}
    )
    for i, node in enumerate(plan):
        if (
            not isinstance(node, list)
            or not node
            or node[0] not in sizes
            or len(node) != sizes[node[0]]
        ):
            raise ValueError(f"node {i}: unsupported node form {str(node)[:120]}")
        if node[0] == "input":
            continue
        refs = node[1:3] if system == "knime" and node[0] == "end" else node[1:2]
        if any(type(r) is not int or not 0 <= r < i for r in refs):
            raise ValueError(f"node {i}: use indexes of preceding nodes")
        if node[0] == "set":
            if node[2] not in FIELDS:
                raise ValueError("unknown set column")
            expression(node[3], FIELDS)
        if node[0] == "keep" and node[2] not in FIELDS:
            raise ValueError("unknown filter column")
    kinds = [node[0] for node in plan]
    if not (
        kinds[0] == "input"
        and kinds[-1] == "sink"
        and all(kinds.count(k) == 1 for k in ("input", "start", "end", "sink"))
    ):
        raise ValueError("expected one input, one start, one end and one final sink")
    if kinds[plan[-1][1]] != "end":
        raise ValueError("sink must read the loop end")
    if system == "waffle" and (
        kinds != ["input", "start", "emit", "end", "sink"]
        or any(n[1] != i - 1 for i, n in enumerate(plan) if i)
    ):
        raise ValueError(
            "WAFFLE graph must connect input, start, emit, end, sink in order"
        )
    if system == "knime":
        start, end = kinds.index("start"), kinds.index("end")
        reachable = {start}
        for i in range(start + 1, end):
            if plan[i][1] in reachable:
                reachable.add(i)
        if not all(ref in reachable for ref in plan[end][1:]):
            raise ValueError("both loop end inputs must descend from its start")
    return plan


def preview(plan, system, data):
    validate(plan, system)
    state = initial(data)
    rows = []
    if system == "waffle":
        assign(plan[1][2], state)
        for _ in range(LIMIT):
            x, y = [evaluate(e, state) for e in plan[2][2:]]
            rows.append([x, y])
            state.update(out_x=x, out_y=y)
            assign(plan[3][2], state)
            if not evaluate(plan[3][3], state):
                break
    else:
        feedback = None
        for iteration in range(LIMIT):
            streams = []
            for node in plan:
                kind = node[0]
                if kind == "input":
                    value = state
                elif kind == "start":
                    value = feedback if iteration else streams[node[1]]
                elif kind == "set":
                    value = streams[node[1]]
                    if value is not None:
                        value = dict(value)
                        value[node[2]] = evaluate(node[3], value)
                elif kind == "keep":
                    value = streams[node[1]]
                    if value is not None and value[node[2]] != 1:
                        value = None
                elif kind == "end":
                    value, feedback = streams[node[1]], streams[node[2]]
                    if value is not None:
                        rows.append([value["x"], value["y"]])
                else:
                    value = streams[node[1]]
                streams.append(value)
            if feedback is None:
                break
    return rows
