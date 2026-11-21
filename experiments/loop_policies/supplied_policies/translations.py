"""Run native translations of the visible policy logic as positive controls."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from xml.etree import ElementTree as E
from prepare_cases import HERE, VISITS, model
from run_knime import launch

sys.path.insert(0, str(HERE.parent / "native_controls"))
from rapidminer_native import numeric
from n8n_native import IMAGE


def execute_n8n(source, folder, rule, version):
    g = json.loads((source / "workflow.json").read_text())
    update = next(n for n in g["nodes"] if n["name"] == "Update")
    fields = {f["name"]: f for f in update["parameters"]["assignments"]["assignments"]}
    if rule == "choose":
        if version == "v1":
            step = "($json.rows.length===0 ? ($json.score < -250 ? 4 : 3) : ($json.rows.length===1 ? ($json.K===4 ? 3 : ($json.score < -100 ? 4 : 0)) : 0))"
        else:
            step = "($json.score < -100 && $json.K < 4 ? $json.K+1 : 0)"
        fields["K"]["value"] = "={{ " + step + " }}"
        fields["again"]["value"] = "={{ " + step + " > 0 }}"
    else:
        fields["again"]["value"] = fields["again"]["value"].replace(
            ">= 150", ">= " + ("250" if version == "v1" else "100")
        )
    path = folder / "workflow.json"
    path.write_text(json.dumps(g, indent=2))
    command = [
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
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    (folder / "engine.log").write_text(result.stderr + result.stdout, encoding="utf-8")
    result.check_returncode()
    record, _ = json.JSONDecoder().raw_decode(
        result.stdout[result.stdout.index("{\n") :]
    )
    assert record["status"] == "success"
    trace = record["data"]["resultData"]["runData"]
    rows = trace["Result"][0]["data"]["main"][0][0]["json"]["rows"]
    assert len(trace["Body"]) == len(rows)
    return rows


def execute_knime(source, folder, rule, version):
    E.register_namespace("", "http://www.knime.org/2008/09/XMLConfig")
    wf = folder / "workflow"
    shutil.copytree(source / "workflow", wf, dirs_exist_ok=True)

    def setting(node, key, value):
        path = next(wf.glob(node + " (#*)/settings.xml"))
        doc = E.parse(path)
        doc.find(".//{*}config[@key='model']/.//{*}entry[@key='" + key + "']").set(
            "value", value
        )
        doc.write(path, encoding="utf-8", xml_declaration=True)

    if rule == "choose":
        if version == "v1":
            step = "if($K$ == 2,if($score$ < -250,4,3),if($previous$ == 2,if($K$ == 4,3,if($score$ < -100,4,0)),0))"
        else:
            step = "if(($score$ < -100) && ($K$ < 4),$K$+1,0)"
        setting("Set again", "expression", step)
        setting("Keep continuing rows", "Pattern", "[1-9]([.]0+)?")
        setting("Set previous", "expression", "$K$")
        setting("Set K", "expression", "$again$")
    else:
        gain = 250 if version == "v1" else 100
        setting(
            "Set again",
            "expression",
            f"if(($K$ < 4) && (($K$ == 2) || ($score$-$previous$ >= {gain})),1,0)",
        )
    setting("Export", "filename", (folder / "result.csv").as_posix())
    code = launch(
        Path(os.environ["KNIME_HOME"]),
        [
            "-application",
            "org.knime.product.KNIME_BATCH_APPLICATION",
            "-reset",
            "-nosave",
            "-failonloaderror",
            "-workflowDir=" + str(wf),
            "-data",
            str(folder / "workspace"),
        ],
        folder / "engine.log",
    )
    if code:
        raise RuntimeError(f"KNIME exit {code} in {folder}")
    with (folder / "result.csv").open(newline="") as f:
        return [
            dict(K=float(row["K"]), score=float(row["score"]))
            for row in csv.DictReader(f)
        ]


def execute_rm(source, folder, rule, version):
    doc = E.parse(source / "workflow.rmp")
    loop = doc.find(".//operator[@name='Repeat']")
    filt = doc.find(".//operator[@name='Stop']/parameter[@key='parameter_expression']")
    if rule == "choose":
        for key, val in dict(
            set_iteration_macro="true", macro_name="trial", macro_start_value="1"
        ).items():
            E.SubElement(loop, "parameter", key=key, value=val)
        if version == "v1":
            step = "if(%{trial} == 1,if(%{score} < -250,4,3),if(%{trial} == 2,if(%{k} == 4,3,if(%{score} < -100,4,0)),0))"
        else:
            step = "if(%{score} < -100 && %{k} < 4,%{k}+1,0)"
        doc.find(".//operator[@name='Advance']/list/parameter[@key='k']").set(
            "value", numeric(step)
        )
        filt.set("value", numeric("%{k} == 0"))
    else:
        filt.set(
            "value",
            filt.attrib["value"].replace(
                "< 150", "< " + ("250" if version == "v1" else "100")
            ),
        )
    doc.write(folder / "workflow.rmp", encoding="utf-8", xml_declaration=True)
    with (folder / "engine.log").open("w", encoding="utf-8") as f:
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
            stdout=f,
            stderr=f,
            timeout=90,
            check=True,
        )
    observed = json.loads((folder / "output.json").read_text())
    assert observed["iterations"] == len(observed["rows"])
    return observed["rows"]


def run_case(root, baseline, engine, case):
    rule, version, fixture = case
    folder = root / "translations" / engine / "-".join(case)
    folder.mkdir(parents=True, exist_ok=True)
    template = "history" if rule == "stop" or engine == "knime" else "adaptive"
    source = baseline / engine / f"{template}-{fixture}"
    runners = {"knime": execute_knime, "n8n": execute_n8n, "rapidminer": execute_rm}
    rows = runners[engine](source, folder, rule, version)
    scores = model.scores(HERE.parent / "results" / "inputs" / fixture / "points.csv")
    assert model.compare([scores[k - 2] for k in VISITS[case]], rows), (case, rows)
    (folder / "observation.json").write_text(json.dumps(rows))
    print(engine, case, [r["K"] for r in rows], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument(
        "baseline", type=Path, help="Output of the native_controls experiment"
    )
    parser.add_argument("engine", choices=("knime", "n8n", "rapidminer"))
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(
            pool.map(
                lambda case: run_case(
                    args.run.resolve(), args.baseline.resolve(), args.engine, case
                ),
                VISITS,
            )
        )
