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


def condition_prompt(system, task, condition):
    base = prompt(system, task)
    if condition == "documentation":
        return base
    if condition == "worked_example":
        extra = documentation(system)
    elif condition in ("wiring_only", "wiring_timing"):
        extra = (
            "\nWiring-only example (symbolic diagram). Arrows show connections. "
            "Question marks leave the task logic open. Choose every expression for the actual task.\n"
            + WIRING[system]
            + "\nSubmit a complete graph using the documented JSON node forms and indexes."
        )
        if condition == "wiring_timing":
            extra += "\nIteration semantics: " + TIMING[system]
    else:
        raise ValueError(f"Unknown prompt condition: {condition}")
    return base.replace("\n\nTask:", extra + "\n\nTask:")
