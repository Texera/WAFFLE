"""Run saved Studio Core processes using native operators and expressions."""

from concurrent.futures import ThreadPoolExecutor
from xml.etree import ElementTree as E
import json
import subprocess
import sys
from inputs import ART, RUN, cases, curve, model, save

sys.path.insert(0, str(ART / "experiments/case_study/rapidminer"))
from build import operator, param, connect


def numeric(expr):
    import re

    return re.sub(r"%\{(\w+)\}", lambda m: "parse(" + m[0] + ")", expr)


def parameters(node, key, entries):
    group = E.SubElement(node, "list", key=key)
    for name, value in entries.items():
        param(
            group,
            name,
            numeric(value)
            if key in ("attribute_values", "function_descriptions")
            else value,
        )


def graph(spec, path):
    rule = spec["task"]
    scores = curve(spec["fixture"])
    root = E.Element("process", version="10.1.000")
    outer = E.SubElement(operator(root, "process", "Process", 0, 0), "process")
    init = operator(outer, "set_macros", "Initialize", 40, 30)
    simple = rule in ("sweep", "target")
    state = {f"s{k}": s for k, s in scores.items()}
    if not simple:
        state["k"] = 2
    if rule == "history":
        state["prev"] = 0
    parameters(init, "macros", state)
    loop = operator(
        outer, "loop" if rule == "sweep" else "loop_until", "Repeat", 250, 30
    )
    options = dict(
        condition_on_data="true",
        condition_on_performance="false",
        condition_before="false",
        min_examples=1,
        max_examples=1,
        min_attributes=1,
        max_attributes=20,
        max_iterations=3 if simple else 8,
    )
    if rule == "sweep":
        options = dict(iterations=3)
    if simple:
        options.update(set_iteration_macro="true", macro_name="k", macro_start_value=2)
    for name, value in options.items():
        param(loop, name, value)
    inside = E.SubElement(loop, "process")
    body = operator(inside, "generate_data_user_specification", "Body", 40, 30)
    values = {"K": "%{k}", "score": "if(%{k} == 2, %{s2}, if(%{k} == 3, %{s3}, %{s4}))"}
    if rule == "history":
        values["previous"] = "%{prev}"
    parameters(body, "attribute_values", values)
    if simple:
        if rule == "sweep":
            connect(inside, "Body", "output", None, "output 1")
        else:
            filt = operator(inside, "filter_examples", "Stop", 200, 30)
            param(filt, "condition_class", "expression")
            param(filt, "parameter_expression", "score >= -100")
            connect(inside, "Body", "output", "Stop", "example set input")
            connect(inside, "Stop", "original", None, "output 1")
            connect(inside, "Stop", "example set output", None, "example set")
    else:
        adaptive_control(inside, rule)
    connect(outer, "Initialize", "through 1", "Repeat", "input 1")
    connect(outer, "Repeat", "output 1", None, "result 1")
    E.indent(root)
    E.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)


def adaptive_control(inside, rule):
    read = operator(inside, "extract_macro", "Read score", 200, 30)
    for key, value in dict(
        macro="score", macro_type="data_value", attribute_name="score", example_index=1
    ).items():
        param(read, key, value)
    update = operator(inside, "generate_macro", "Advance", 380, 30)
    step = "if(%{score} < -250, 2*%{k}, %{k}+1)" if rule == "adaptive" else "%{k}+1"
    updates = {"k": step}
    if rule == "history":
        updates["prev"] = "%{score}"
    parameters(update, "function_descriptions", updates)
    filt = operator(inside, "filter_examples", "Stop", 540, 30)
    stop = "%{k} > 4"
    if rule in ("adaptive", "target"):
        stop += " || score >= -100"
    if rule == "history":
        stop += " || (K > 2 && score - previous < 150)"
    param(filt, "condition_class", "expression")
    param(filt, "parameter_expression", numeric(stop))
    connect(inside, "Body", "output", "Read score", "example set")
    connect(inside, "Read score", "example set", "Advance", "through 1")
    connect(inside, "Advance", "through 1", "Stop", "example set input")
    connect(inside, "Stop", "original", None, "output 1")
    connect(inside, "Stop", "example set output", None, "example set")


def run(spec):
    folder = RUN / "rapidminer" / spec["id"]
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "workflow.rmp"
    graph(spec, path)
    with (folder / "engine.log").open("w", encoding="utf-8") as log:
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "-v",
                str(folder) + ":/case",
                "waffle-native-controls-rapidminer:10.1",
                "/case/workflow.rmp",
                "/case/output.json",
            ],
            stdout=log,
            stderr=log,
            timeout=90,
            check=True,
        )
    actual = json.loads((folder / "output.json").read_text())
    assert model.compare(spec["expected"], actual["rows"]) and actual[
        "iterations"
    ] == len(actual["rows"]), actual
    save(folder / "observation.json", actual)
    print(spec["id"], [v["K"] for v in actual["rows"]], flush=True)


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(
            pool.map(
                run,
                [s for s in cases() if len(sys.argv) == 1 or s["id"] == sys.argv[1]],
            )
        )
