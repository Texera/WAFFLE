"""Frozen paired authoring protocol. Only PUBLIC inputs and traces enter prompts."""

from pathlib import Path
import json

FIELDS = "x y n goal i u v flag".split()
LIMIT = 8
SEEDS = (397, 811)
TRIES = 3
TASKS = {
    "advance": "Emit (x,y) before each change, exactly n times. Between emissions advance x by 2 and keep y fixed.",
    "running_sum": "Repeat n times. Increase x by one, add this NEW x to y, then emit the new pair.",
    "crossing": "Emit the initial (x,y). If x has reached or exceeded goal, finish. Otherwise advance x by y and repeat. Emit at most n rows including the initial row.",
    "recurrence": "Emit the initial (x,y) and thereafter replace the pair simultaneously with (y,x+y) between emissions. Emit exactly n rows.",
    "zigzag": "Emit n rows beginning with the input pair. Between rows, increase x by y after an odd-numbered emission (the first is odd), decrease x by y after an even-numbered emission. Increase y by one after each emission.",
    "cooldown": "Before each emission, increase y by the current x. Emit (x,new y). Stop if the emitted y reaches or exceeds goal or if n rows have been emitted. For the next iteration use x+2 if the just-emitted y is negative and x+1 otherwise.",
}
PUBLIC = (2, 1, 3, 5)
HIDDEN = {
    "advance": [(3, -2, 1, 4), (-1, 3, 4, 2)],
    "running_sum": [(0, 4, 1, 3), (-2, -2, 4, 6)],
    "crossing": [(4, 2, 4, 4), (-1, 2, 4, 3)],
    "recurrence": [(5, 2, 1, 1), (-2, 3, 4, 3)],
    "zigzag": [(-3, 2, 1, 8), (5, -1, 4, 3)],
    "cooldown": [(3, 2, 4, 4), (1, -4, 4, 12)],
}


def oracle(task, data):
    x, y, n, goal = data
    rows = []
    for index in range(n):
        if task == "running_sum":
            x += 1
            y += x
        elif task == "cooldown":
            y += x
        rows.append([x, y])
        if task == "advance":
            x += 2
        elif task == "crossing":
            if x >= goal:
                break
            x += y
        elif task == "recurrence":
            x, y = y, x + y
        elif task == "zigzag":
            x += y if index % 2 == 0 else -y
            y += 1
        elif task == "cooldown":
            if y >= goal:
                break
            x += 2 if y < 0 else 1
    return rows


COMMON = """Return one JSON array. Each element is a native graph node in topological order, encoded as a positional array. References to earlier nodes are their integer indexes starting at zero. All graphs must include an input, loop, and sink. Input has ONE row with numeric columns x,y,n,goal and scratch columns i,u,v,flag initialized to zero. Each input can differ at execution. All arithmetic expressions are JSON strings written in a common restricted Python syntax: column names, integer constants, +, -, *, %, comparisons, and/or/not, and a if test else b. Use numeric 0/1 for flags. No function calls. The output is the complete ordered sequence of (x,y) pairs at the sink. A safety limit stops runaway loops after 8 iterations. Do not hardcode the example. The interface supplies serialization only. Return JSON without commentary."""
DOC = {
    "waffle": """Node forms:
["input"]
["start",source,assignments] opens a WAFFLE loop. All input columns become named loop variables once. Then apply assignments once in order. An assignment list is zero or more [column,"expression"] pairs.
["emit",start,"x expression","y expression"] emits one result row per iteration, using the current loop variables. Both expressions read the same state, and emitting does not modify it.
["end",emit,assignments,"continue expression"] collects the emitted row, then applies assignments sequentially to loop variables and evaluates continue on the updated variables. True runs another iteration. In update and condition, out_x and out_y are also available for the row just emitted.
["sink",end] exports all rows. Exactly one of each node in this catalog is required.""",
    "knime": """Node forms:
["input"]
["start",source] opens a KNIME Recursive Loop Start. First iteration uses the input row. Every later iteration uses the feedback row.
["set",source,"column","expression"] is a Math Formula node. It returns the row with the named column replaced. Other columns stay the same. You may chain nodes or branch by referencing the same source twice.
["keep",source,"column"] is a Row Filter passing rows whose named column equals 1. Set a numeric flag with a formula to implement an arbitrary continuation condition.
["end",collect,feedback] is a Recursive Loop End. It appends (x,y) from collect on EVERY iteration and feeds the row from feedback to the start. Empty feedback ends the loop. Collect and feedback may branch off at any node inside the loop.
["sink",end] exports all collected rows. Use exactly one input, start, end and sink, and as many formula/filter nodes as needed. A set may also be placed before start.""",
}


def prompt(system, task):
    return (
        COMMON
        + "\n\n"
        + DOC[system]
        + "\n\nTask: "
        + TASKS[task]
        + "\nExample input (x,y,n,goal): "
        + str(PUBLIC)
        + "\nRequired output: "
        + json.dumps(oracle(task, PUBLIC))
    )


def dump(path, data):
    Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
