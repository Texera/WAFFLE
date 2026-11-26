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
    verify_sessions(RESULTS / "state-and-branch", clarified=True, state_and_branch=True)
    verify_sessions(
        RESULTS / "literal-repeat",
        clarified=True,
        state_and_branch=True,
        literal_repeat=True,
    )
    verify_sessions(RESULTS / "carry-keep", clarified=True, carry_keep=True)
    print(f"All {len(controls)} native reference outputs match NetworkX.")


def verify_sessions(
    folder, clarified, state_and_branch=False, literal_repeat=False, carry_keep=False
):
    expected = task.expected(task.PUBLIC_ROOT)
    outputs = json.loads((folder / "agent-outputs.json").read_text())
    native_path = folder / "agent-native.jsonl"
    native = {}
    if native_path.exists():
        for line in native_path.read_text().splitlines():
            entry = json.loads(line)
            assert entry["case"] not in native
            native[entry["case"]] = [[row["x"], row["y"]] for row in entry["rows"]]
    knime_path = folder / "agent-knime.json"
    if knime_path.exists():
        for entry in json.loads(knime_path.read_text()):
            assert entry["exit"] == 0 and entry["case"] not in native
            native[entry["case"]] = entry["rows"]
    scored = set()
    for system in task.controls():
        executable = 0
        submissions = 0
        successful = 0
        prompt = (folder / f"{system}-prompt.txt").read_text(encoding="utf8")
        assert prompt == task.prompt(
            system, clarified, state_and_branch, literal_repeat, carry_keep
        )
        if carry_keep:
            assert prompt.replace(task.CARRY_KEEP_REMINDER[system] + "\n\n", "") == (
                RESULTS / "literal-repeat" / f"{system}-prompt.txt"
            ).read_text(encoding="utf8")
        elif literal_repeat:
            assert prompt.replace(
                task.LITERAL_REPEAT_REMINDER + "\n\n", ""
            ) == task.prompt(system, state_and_branch=True)
        elif state_and_branch:
            assert prompt.replace(
                task.OUTPUT_REMINDER[system] + "\n\n", ""
            ) == task.prompt(system, True)
        elif clarified:
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
            attempts = record["attempts"]
            assert record["max_tokens"] == 4096 and 1 <= len(attempts) <= TRIES
            assert not any(item["public_pass"] for item in attempts[:-1])
            assert attempts[-1]["public_pass"] or len(attempts) == TRIES
            assert record["prompt_hash"] == hashlib.sha256(prompt.encode()).hexdigest()
            for item in attempts:
                submissions += 1
                assert item["served_model"] == record["model"]
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
                    assert not item["public_pass"]
                    assert item["feedback"] == f"Invalid graph: {str(exc)[:300]}."
                else:
                    assert graph == item["plan"]
                    assert (
                        rows == item["public_rows"]
                        and (rows == expected) == item["public_pass"]
                    )
                    assert (
                        item["feedback"]
                        == "The public example produced " + json.dumps(rows) + "."
                    )
                    executable += 1
            records = [r for r in outputs if (r["system"], r["seed"]) == (system, seed)]
            if not attempts[-1]["public_pass"]:
                assert not records
                continue
            roots = (task.PUBLIC_ROOT, *task.HELD_OUT)
            assert len(records) == len(roots) and {r["root"] for r in records} == set(
                roots
            )
            for r in records:
                key = hashlib.sha256(
                    json.dumps([attempts[-1]["plan"], r["root"]]).encode()
                ).hexdigest()[:16]
                assert r["case"] == f"{system}-{key}" and r["rows"] == native[r["case"]]
                assert r["match"] == (r["rows"] == task.expected(r["root"]))
                scored.add(r["case"])
            successful += all(r["match"] for r in records)
        print(
            f"{folder.name} {system}: {executable}/{submissions} executable, {successful}/{len(SEEDS)} successful sessions."
        )
    assert {r["case"] for r in outputs} == scored == set(native)


if __name__ == "__main__":
    verify()
