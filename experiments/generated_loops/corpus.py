"""Deterministic generator for single-block Texera logical workflows."""
import argparse
import hashlib
from itertools import chain, product
import json
from pathlib import Path

ARMS = ((0, 1), (0, 2), (0, 3), (1, 1), (1, 2), (1, 3), (2, 2))
FAMILIES = ("search", "stopping", "aggregation")
FIXTURES = {
    "mixed": (-4, 0, 7, -2, 1, 1, 5, -1, 3),
    "low": (-20, -19, -20, -17, -21, -16),
    "high": (18, 20, 21, 18, 23, 22),
}


def cases():
    shallow = chain.from_iterable(product(ARMS, repeat=depth) for depth in (1, 2, 3))
    # Keep the established four-stage IDs while enumerating the entire grammar.
    deep = sorted(product(ARMS, repeat=4), key=digest)
    # Append the new shapes so existing graph IDs, families and policies stay fixed.
    extra_pair = (2, 3)
    extended = (shape for depth in (1, 2, 3, 4)
                for shape in product((*ARMS, extra_pair), repeat=depth) if extra_pair in shape)
    for index, arms in enumerate(chain(shallow, deep, extended)):
        yield FAMILIES[index % 3], (index // 3) % 3, arms


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def udf(code, columns, source=False):
    schema = [dict(attributeName=name, attributeType="integer") for name in columns]
    props = dict(code=code, workers=1, defaultEnv=True, envName="")
    if source:
        props["columns"] = schema
    else:
        props.update(outputColumns=schema, retainInputColumns=False)
    return props


def cells(family, policy):
    if family == "search":
        return "-2", "D", "k += 1", "k <= 2"
    if family == "stopping":
        return "0", "D", "k += 1", f"k <= 5 and 6 * score < {2 + policy} * count"
    return "0", "D.loc[D.bucket == k]", "k += 1", "k < 3"


def reducer(family, policy):
    terms = {
        "search": ("abs(x - k)", "(x - k) ** 2", "max(x - k, 0) + 2 * max(k - x, 0)"),
        "stopping": ("int(x <= k)",) * 3,
        "aggregation": ("x", "abs(x)", "x * x"),
    }
    return f"""from pytexera import *
class Body(UDFOperatorV2):
    def open(self):
        self.score = 0
        self.count = 0

    def process_state(self, state, port):
        return None

    def process_tuple(self, row, port):
        k = int(self.state['k'])
        x = int(row['x'])
        self.score += {terms[family][policy]}
        self.count += 1
        yield None

    def produce_state_on_finish(self, port):
        return State(dict(self.state, score=self.score, count=self.count))

    def on_finish(self, port):
        yield dict(step=int(self.state['k']), score=self.score)
"""


def graph(family, policy, arms, values):
    nodes, links = [], []

    def port(name, multi=False):
        return dict(portID=name + "-0", displayName="", isDynamicPort=False,
                    allowMultiInputs=multi, disallowMultiInputs=not multi, dependencies=[])

    def add(kind, props, parents=()):
        ident = f"{kind}-operator-{len(nodes)}"
        nodes.append(dict(operatorID=ident, operatorType=kind, operatorProperties=props,
                          inputPorts=[port("input", kind == "Union")] if parents else [],
                          outputPorts=[port("output")]))
        for parent in parents:
            links.append(dict(linkID=f"link-{len(links)}",
                              source=dict(operatorID=parent, portID="output-0"),
                              target=dict(operatorID=ident, portID="input-0")))
        return ident

    code = f"""from pytexera import *
class Fixture(UDFSourceOperator):
    def produce(self):
        for i, x in enumerate({tuple(values)!r}):
            yield dict(x=x, bucket=i % 3)
"""
    src = add("PythonUDFSourceV2", udf(code, ("x", "bucket"), source=True))
    initial, output, update, condition = cells(family, policy)
    tip = add("LoopStart", dict(initialization="k = " + initial, output=output), [src])
    for stage, lengths in enumerate(arms, 1):
        tails = []
        for side, length in enumerate(lengths):
            tail = tip
            for hop in range(length):
                delta = stage + hop
                expr = f"2 * x + {delta}" if side == 0 else f"x - {delta}"
                code = f"""from pytexera import *
class Feature(UDFOperatorV2):
    def process_tuple(self, row, port):
        x = int(row['x'])
        yield dict(x={expr}, bucket=int(row['bucket']))
"""
                tail = add("PythonUDFV2", udf(code, ("x", "bucket")), [tail])
            tails.append(tail)
        tip = add("Union", {}, tails)
    tip = add("PythonUDFV2", udf(reducer(family, policy), ("step", "score")), [tip])
    tip = add("LoopEnd", dict(update=update, condition=condition), [tip])
    add("Sort", dict(attributes=[dict(attribute="step", sortPreference="ASC")]), [tip])
    return dict(operators=nodes, links=links, settings=dict(executionMode="MATERIALIZED"))


def prepare(root):
    root.mkdir(parents=True, exist_ok=False)
    for i, (family, policy, arms) in enumerate(cases()):
        g = graph(family, policy, arms, FIXTURES["mixed"])
        (root / f"{i:03d}.json").write_bytes(encode(g))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("new_directory", type=Path)
    prepare(parser.parse_args().new_directory)
