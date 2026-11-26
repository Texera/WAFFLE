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


def condition_prompt(system, task, condition):
    base = prompt(system, task)
    if condition == "documentation":
        return base
    if condition == "worked_example":
        extra = documentation(system)
    elif condition == "wiring_only":
        extra = (
            "\nWiring-only example (symbolic diagram). Arrows show connections. "
            "Question marks leave the task logic open. Choose every expression for the actual task.\n"
            + WIRING[system]
            + "\nSubmit a complete graph using the documented JSON node forms and indexes."
        )
    else:
        raise ValueError(f"Unknown prompt condition: {condition}")
    return base.replace("\n\nTask:", extra + "\n\nTask:")
