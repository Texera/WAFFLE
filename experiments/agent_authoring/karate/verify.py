"""Replay the published submissions and compare native control outputs with NetworkX."""

import hashlib
import json
from pathlib import Path

import task
from protocol import SEEDS, TRIES

RESULTS = Path(__file__).parent / "results"


def read(path):
    return json.loads((RESULTS / path).read_text(encoding="utf8"))


def verify():
    assert read("fixtures.json") == json.loads(json.dumps(task.metadata()))
    assert read("controls.json") == task.controls()
    roots = (task.PUBLIC_ROOT, *task.HELD_OUT)
    controls = read("controls-outputs.json")
    assert len(controls) == 2 * len(roots)
    assert {(r["system"], r["root"]) for r in controls} == {
        (system, root) for system in task.controls() for root in roots
    }
    waffle = [
        json.loads(line)
        for line in (RESULTS / "waffle-native.jsonl").read_text().splitlines()
    ]
    knime = read("knime-native.json")
    assert len(waffle) == len(knime) == len(roots)
    native = {r["case"]: [[v["x"], v["y"]] for v in r["rows"]] for r in waffle}
    for r in knime:
        assert r["exit"] == 0
        native[r["case"]] = r["rows"]
    for r in controls:
        assert r["match"] and native[r["case"]] == r["rows"] == task.expected(r["root"])

    verify_sessions(RESULTS, clarified=False)
    verify_sessions(RESULTS / "clarified", clarified=True)
    print(f"All {len(controls)} native reference outputs match NetworkX.")


def verify_sessions(folder, clarified):
    expected = task.expected(task.PUBLIC_ROOT)
    for system in task.controls():
        executable = 0
        prompt = (folder / f"{system}-prompt.txt").read_text(encoding="utf8")
        assert prompt == task.prompt(system, clarified)
        if clarified:
            assert prompt.replace(task.FORMAT_REMINDER + "\n\n", "") == task.prompt(
                system
            )
        for seed in SEEDS:
            path = folder / f"sessions/{task.TASK}-{seed}-{system}.json"
            record = json.loads(path.read_text(encoding="utf8"))
            assert (record["system"], record["task"], record["seed"]) == (
                system,
                task.TASK,
                seed,
            )
            assert record["model"] == "flash-next" and record["temperature"] == 0.6
            assert record["max_tokens"] == 4096 and len(record["attempts"]) == TRIES
            assert record["prompt_hash"] == hashlib.sha256(prompt.encode()).hexdigest()
            for item in record["attempts"]:
                assert (
                    item["served_model"] == record["model"] and not item["public_pass"]
                )
                content = item["text"].strip()
                if content.startswith("```") and content.endswith("```"):
                    content = content.partition("\n")[2][:-3].strip()
                try:
                    graph = json.loads(content)
                    rows = task.public_preview(
                        graph, system, task.fixture(task.PUBLIC_ROOT)
                    )
                except (
                    ValueError,
                    SyntaxError,
                    IndexError,
                    TypeError,
                    KeyError,
                    ArithmeticError,
                ) as exc:
                    assert item["feedback"] == f"Invalid graph: {str(exc)[:300]}."
                else:
                    assert graph == item["plan"]
                    assert rows == item["public_rows"] and rows != expected
                    assert (
                        item["feedback"]
                        == "The public example produced " + json.dumps(rows) + "."
                    )
                    executable += 1
        assert executable == (2 if clarified else 0)
        print(
            f"{folder.name} {system}: {executable}/{len(SEEDS) * TRIES} executable, 0/{len(SEEDS)} successful sessions."
        )
    assert json.loads((folder / "agent-outputs.json").read_text()) == []


if __name__ == "__main__":
    verify()
