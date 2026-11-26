"""Run isolated paired sessions against a configured OpenAI-compatible model."""

from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import os
import time
from pathlib import Path
import requests
from worked_example import condition_prompt
from protocol import PUBLIC, TASKS, SEEDS, TRIES, dump, oracle
from graphs import preview


def session(spec):
    system, task, seed = spec
    path = args.out / f"{task}-{seed}-{system}.json"
    if path.exists():
        return
    instructions = condition_prompt(system, task, args.condition)
    chat = [
        {
            "role": "system",
            "content": "You author executable workflow graphs. Use the provided graph interface.",
        },
        {"role": "user", "content": instructions},
    ]
    record = dict(
        system=system,
        task=task,
        seed=seed,
        model=args.model,
        temperature=0.6,
        max_tokens=4096,
        prompt_hash=hashlib.sha256(chat[1]["content"].encode()).hexdigest(),
        attempts=[],
    )
    for attempt in range(1, TRIES + 1):
        payload = dict(
            model=args.model,
            messages=chat,
            seed=seed + attempt - 1,
            temperature=0.6,
            max_tokens=4096,
            chat_template_kwargs={"enable_thinking": False},
        )
        for retry in range(3):
            try:
                res = requests.post(
                    args.endpoint.rstrip("/") + "/chat/completions",
                    headers={"Authorization": "Bearer " + token},
                    json=payload,
                    timeout=300,
                )
                res.raise_for_status()
                response = res.json()
                break
            except requests.RequestException:
                if retry == 2:
                    raise
                time.sleep(5)
        choice = response["choices"][0]
        content = choice["message"].get("content") or ""
        item = dict(
            text=content,
            finish_reason=choice["finish_reason"],
            usage=response.get("usage"),
            served_model=response.get("model"),
        )
        try:
            raw = content.strip()
            if raw.startswith("\x60\x60\x60") and raw.endswith("\x60\x60\x60"):
                raw = raw.partition("\n")[2][:-3].strip()
            plan = json.loads(raw)
            observed = preview(plan, system, PUBLIC)
            item.update(plan=plan, public_rows=observed)
            ok = observed == oracle(task, PUBLIC)
            feedback = "The public example produced " + json.dumps(observed) + "."
        except (
            ValueError,
            SyntaxError,
            IndexError,
            TypeError,
            KeyError,
            ArithmeticError,
        ) as err:
            ok = False
            feedback = f"Invalid graph: {str(err)[:300]}."
        item.update(public_pass=ok, feedback=feedback)
        record["attempts"].append(item)
        if ok:
            break
        chat.extend(
            [
                dict(role="assistant", content=content),
                dict(role="user", content=feedback + " Submit a corrected full graph."),
            ]
        )
    temp = path.with_suffix(".tmp")
    dump(temp, record)
    temp.replace(path)
    print(path.stem, len(record["attempts"]), ok, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--model", default="flash-next")
    condition = parser.add_mutually_exclusive_group()
    condition.add_argument(
        "--worked-example",
        dest="condition",
        action="store_const",
        const="worked_example",
    )
    condition.add_argument(
        "--wiring-only", dest="condition", action="store_const", const="wiring_only"
    )
    parser.set_defaults(condition="documentation")
    condition.add_argument(
        "--wiring-timing", dest="condition", action="store_const", const="wiring_timing"
    )
    parser.add_argument("--key-file", type=Path)
    condition.add_argument(
        "--wiring-rules", dest="condition", action="store_const", const="wiring_rules"
    )
    condition.add_argument(
        "--end-ports", dest="condition", action="store_const", const="end_ports"
    )
    condition.add_argument(
        "--assignment-format", dest="condition", action="store_const", const="assignment_format"
    )
    condition.add_argument(
        "--row-numbering", dest="condition", action="store_const", const="row_numbering"
    )
    condition.add_argument(
        "--expression-strings", dest="condition", action="store_const", const="expression_strings"
    )
    condition.add_argument(
        "--feedback-filter", dest="condition", action="store_const", const="feedback_filter"
    )
    condition.add_argument(
        "--flag-source", dest="condition", action="store_const", const="flag_source"
    )
    condition.add_argument(
        "--required-connections", dest="condition", action="store_const", const="required_connections"
    )
    condition.add_argument(
        "--filtered-updates", dest="condition", action="store_const", const="filtered_updates"
    )
    args = parser.parse_args()
    token = (
        args.key_file.read_text().strip()
        if args.key_file
        else os.environ["INFERENCE_TOKEN"]
    )
    args.out.mkdir(parents=True, exist_ok=True)
    specs = []
    for task in TASKS:
        for seed in SEEDS:
            systems = ["waffle", "knime"]
            if len(specs) // 2 % 2:
                systems.reverse()
            specs.extend((s, task, seed) for s in systems)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(session, specs))
