"""Run native Edit Fields and If nodes with an explicit feedback connection."""

from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
import sys
from inputs import ART, RUN, cases, curve, model, save

sys.path.insert(0, str(ART / "experiments/case_study"))
from n8n_cases import IMAGE


def run(spec):
    folder = RUN / "n8n" / spec["id"]
    folder.mkdir(parents=True, exist_ok=True)
    rule = spec["task"]
    step = (
        "($json.score < -250 ? 2*$json.K : $json.K+1)"
        if rule == "adaptive"
        else "($json.K+1)"
    )
    predicate = step + " <= 4"
    if rule in ("target", "adaptive"):
        predicate += " && $json.score < -100"
    if rule == "history":
        predicate += " && ($json.K === 2 || $json.score-$json.previous >= 150)"

    def assignment(name, kind, expression):
        return dict(id=name, name=name, type=kind, value="={{ " + expression + " }}")

    def fields(items):
        return dict(
            mode="manual",
            assignments={"assignments": items},
            includeOtherFields=True,
            options={},
        )

    update = [
        assignment("K", "number", step),
        assignment("again", "boolean", predicate),
        assignment(
            "rows", "array", "$json.rows.concat([{ K: $json.K, score: $json.score }])"
        ),
    ]
    if rule == "history":
        update.append(assignment("previous", "number", "$json.score"))
    initial = dict(K=2, scores=list(curve(spec["fixture"]).values()), rows=[])
    if rule == "history":
        initial["previous"] = 0
    settings = [
        ("Start", "manualTrigger", 1, {}),
        (
            "Init",
            "set",
            3.4,
            dict(mode="raw", jsonOutput=json.dumps(initial), options={}),
        ),
        (
            "Body",
            "set",
            3.4,
            fields([assignment("score", "number", "$json.scores[$json.K-2]")]),
        ),
        ("Update", "set", 3.4, fields(update)),
        (
            "Continue",
            "if",
            1,
            {
                "conditions": {
                    "boolean": [
                        dict(
                            value1="={{ $json.again }}", operation="equal", value2=True
                        )
                    ]
                }
            },
        ),
        ("Result", "noOp", 1, {}),
    ]
    links = [
        ("Start", ["Init"]),
        ("Init", ["Body"]),
        ("Body", ["Update"]),
        ("Update", ["Continue"]),
        ("Continue", ["Body", "Result"]),
    ]
    if rule == "sweep":
        score_rows = [dict(K=k, score=v) for k, v in curve(spec["fixture"]).items()]
        settings = [
            ("Start", "manualTrigger", 1, {}),
            (
                "Init",
                "set",
                3.4,
                dict(
                    mode="raw", jsonOutput=json.dumps({"rows": score_rows}), options={}
                ),
            ),
            ("Input rows", "splitOut", 1, dict(fieldToSplitOut="rows", options={})),
            ("Loop", "splitInBatches", 3, dict(batchSize=1, options={})),
            ("Body", "noOp", 1, {}),
            ("Result", "noOp", 1, {}),
        ]
        links = [
            ("Start", ["Init"]),
            ("Init", ["Input rows"]),
            ("Input rows", ["Loop"]),
            ("Loop", ["Result", "Body"]),
            ("Body", ["Loop"]),
        ]
    nodes = [
        dict(
            id=n,
            name=n,
            type="n8n-nodes-base." + t,
            typeVersion=v,
            parameters=p,
            position=[i * 180, 0],
        )
        for i, (n, t, v, p) in enumerate(settings)
    ]
    edges = {
        s: {"main": [[dict(node=t, type="main", index=0)] for t in dest]}
        for s, dest in links
    }
    path = folder / "workflow.json"
    save(
        path,
        dict(
            id="nativeControl",
            name=spec["id"],
            nodes=nodes,
            connections=edges,
            active=False,
            settings={"executionOrder": "v1"},
        ),
    )
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "-e",
        "N8N_DIAGNOSTICS_ENABLED=false",
        "-v",
        str(path) + ":/case.json:ro",
        "--entrypoint",
        "sh",
        IMAGE,
        "-ec",
        "n8n import:workflow --input=/case.json >&2; exec n8n execute --id nativeControl --rawOutput",
    ]
    result = subprocess.run(
        cmd, timeout=120, capture_output=True, encoding="utf-8", errors="replace"
    )
    (folder / "engine.log").write_text(result.stderr + result.stdout, encoding="utf-8")
    result.check_returncode()
    native, _ = json.JSONDecoder().raw_decode(
        result.stdout[result.stdout.index("{\n") :]
    )
    assert native["status"] == "success"
    trace = native["data"]["resultData"]["runData"]
    visits = [
        {k: r["data"]["main"][0][0]["json"][k] for k in ("K", "score")}
        for r in trace["Body"]
    ]
    result_items = trace["Result"][0]["data"]["main"][0]
    rows = (
        [item["json"] for item in result_items]
        if rule == "sweep"
        else result_items[0]["json"]["rows"]
    )
    assert model.compare(spec["expected"], visits) and model.compare(
        spec["expected"], rows
    )
    save(folder / "observation.json", dict(rows=rows, iterations=len(visits)))
    print(spec["id"], [r["K"] for r in rows], flush=True)


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as pool:
        list(
            pool.map(
                run,
                [s for s in cases() if len(sys.argv) == 1 or s["id"] in sys.argv[1:]],
            )
        )
