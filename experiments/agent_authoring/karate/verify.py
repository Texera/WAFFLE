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

    attempts = 0
    for system in task.controls():
        prompt = (RESULTS / f"{system}-prompt.txt").read_text(encoding="utf8")
        assert prompt == task.prompt(system)
        for seed in SEEDS:
            record = read(f"sessions/{task.TASK}-{seed}-{system}.json")
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
                    task.public_preview(
                        json.loads(content), system, task.fixture(task.PUBLIC_ROOT)
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
                    raise AssertionError(
                        "recorded invalid submission now passes validation"
                    )
                attempts += 1
    assert read("agent-outputs.json") == []
    print(
        f"{attempts} invalid submissions reproduced. All {len(controls)} native control outputs match NetworkX."
    )


if __name__ == "__main__":
    verify()
