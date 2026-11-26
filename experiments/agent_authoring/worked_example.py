"""Sensitivity condition with one equivalent, solved wiring example per system."""

import json
from protocol import prompt

EXAMPLES = {
    "waffle": [
        ["input"],
        ["start", 0, []],
        ["emit", 1, "x", "y"],
        ["end", 2, [["i", "i+1"]], "i < 2"],
        ["sink", 3],
    ],
    "knime": [
        ["input"],
        ["start", 0],
        ["set", 1, "i", "i+1"],
        ["set", 2, "flag", "1 if i < 2 else 0"],
        ["keep", 3, "flag"],
        ["end", 1, 4],
        ["sink", 5],
    ],
}


def documentation(system):
    return (
        "\nWorked example on a DIFFERENT task: emit the unmodified input pair exactly twice. One valid complete graph is "
        + json.dumps(EXAMPLES[system])
        + ". Your task follows. Construct your own graph."
    )


WIRING = {
    "waffle": """IN -> START (initial assignments: ?)
START -> EMIT (first output expression: ?, second output expression: ?)
EMIT -> END (update assignments: ?, continue expression: ?)
END -> SINK""",
    "knime": """IN -> START
START -> [task-defined nodes, if needed] -> COLLECT_ROW (output expressions: ?)
START -> [task-defined nodes, if needed] -> FEEDBACK_ROW (update and continue expressions: ?)
COLLECT_ROW -> END input 1; FEEDBACK_ROW -> END input 2
END -> SINK
The two paths may share nodes. COLLECT_ROW and FEEDBACK_ROW label the producers of the two end inputs.""",
}


TIMING = {
    "waffle": (
        "EMIT evaluates both output expressions using the state at the start of that "
        "body execution and emits one row. END collects this row, making its two fields "
        "available as out_x and out_y. END applies its assignments in the listed order. "
        "Each assignment sees the effects of earlier assignments. END then tests the "
        "resulting state to decide whether to start another iteration with that state. "
        "Stopping the loop retains the row collected in this iteration."
    ),
    "knime": (
        "Each formula node reads its input row and passes the updated row to its consumers. "
        "A later formula on the same path sees that update. Branches reading the same "
        "predecessor each start with that predecessor's row. END collects any row on "
        "its collection input for this iteration. The row on its separate feedback input "
        "starts the next iteration. Empty feedback ends the loop and retains any row "
        "collected in this iteration."
    ),
}


GRAPH_RULE = {
    "waffle": (
        "The available scratch fields are i, u, v, and flag. All four start at zero. "
        "An assignment may write an input field (x, y, n, goal) or one of those four "
        "scratch fields. The graph cannot declare additional fields."
    ),
    "knime": (
        "Number nodes by their positions in the submitted array, starting at zero. "
        "Every input reference must be smaller than the position of the node that "
        "uses it. This rule applies to both input references on the end node."
    ),
}


KNIME_END_PORTS = (
    "END has two independent inputs. Its first input (collection) determines which rows "
    "appear in the output. An empty collection input adds no row for that iteration. "
    "Its second input (feedback) supplies the next iteration. Empty feedback stops "
    "the loop, including when the collection input has a row. The sink must read "
    "directly from END to receive the collected rows."
)


WAFFLE_ASSIGNMENTS = (
    "In every START assignment, write the initializer as a JSON string containing "
    "an expression. This applies to numeric constants too. Store any temporary "
    "value in a declared scratch field (i, u, v, or flag)."
)


ROW_NUMBERING = "The first row emitted is output row 1, even when the workflow counter starts at 0."


EXPRESSION_STRINGS = (
    "Supply the two EMIT output expressions as separate arguments, each a plain JSON string. "
    "Supply the END continuation test as one plain JSON string. "
    "Write these three strings directly in their argument positions, without enclosing them in arrays."
)


FEEDBACK_FILTER = (
    "On the feedback path, compute the continuation flag from the row after its state updates. "
    "Pass that row through a filter that keeps it when the flag is true and drops it when "
    "the flag is false. Connect the filtered output to END's feedback input."
)


def condition_prompt(system, task, condition):
    if condition == "feedback_filter":
        previous = condition_prompt(system, task, "expression_strings")
        if system == "knime":
            return previous.replace("\n\nTask:", "\n" + FEEDBACK_FILTER + "\n\nTask:")
        return previous
    if condition == "expression_strings":
        previous = condition_prompt(system, task, "row_numbering")
        if system == "waffle":
            return previous.replace("\n\nTask:", "\n" + EXPRESSION_STRINGS + "\n\nTask:")
        return previous
    if condition == "row_numbering":
        previous = condition_prompt(system, task, "assignment_format")
        return previous.replace("\n\nTask:", "\n" + ROW_NUMBERING + "\n\nTask:")
    if condition == "assignment_format":
        previous = condition_prompt(system, task, "end_ports")
        if system == "waffle":
            return previous.replace("\n\nTask:", "\n" + WAFFLE_ASSIGNMENTS + "\n\nTask:")
        return previous
    base = prompt(system, task)
    if condition == "documentation":
        return base
    if condition == "worked_example":
        extra = documentation(system)
    elif condition in ("wiring_only", "wiring_timing", "wiring_rules", "end_ports"):
        extra = (
            "\nWiring-only example (symbolic diagram). Arrows show connections. "
            "Question marks leave the task logic open. Choose every expression for the actual task.\n"
            + WIRING[system]
            + "\nSubmit a complete graph using the documented JSON node forms and indexes."
        )
        if condition in ("wiring_timing", "wiring_rules", "end_ports"):
            extra += "\nIteration semantics: " + TIMING[system]
        if condition in ("wiring_rules", "end_ports"):
            extra += "\nGraph rule: " + GRAPH_RULE[system]
        if condition == "end_ports" and system == "knime":
            extra += "\nLoop end and sink: " + KNIME_END_PORTS
    else:
        raise ValueError(f"Unknown prompt condition: {condition}")
    return base.replace("\n\nTask:", extra + "\n\nTask:")
