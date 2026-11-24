"""Run the original hierarchy and two feedback-port observation runs from reset."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from prepare_knime import NS, config, entry, setval, write
from run_knime import run


def add_writer(workflow, folder, writer, settings, source, port, destination, index):
    sink = 200 + index
    sub = folder / f"Export {sink}"
    sub.mkdir()
    node = copy.deepcopy(writer)
    node.set("key", f"node_{sink}")
    setval(node, "id", sink)
    setval(node, "node_settings_file", sub.name + "/settings.xml")
    config(workflow, "nodes").append(node)
    target = copy.deepcopy(settings)
    model = config(target.getroot(), "model")
    setval(model, "filename", destination.as_posix())
    setval(model, "writeColHeader", "true")
    setval(model, "writeRowHeader", "true")
    variables = config(target.getroot(), "variables")
    for child in list(variables):
        variables.remove(child)
    write(target, sub / "settings.xml")
    edge = ET.SubElement(
        config(workflow, "connections"), f"{{{NS}}}config", key=f"observation_{sink}"
    )
    for key, value in [
        ("sourceID", source),
        ("sourcePort", port),
        ("destID", sink),
        ("destPort", 1),
    ]:
        ET.SubElement(edge, f"{{{NS}}}entry", key=key, type="xint", value=str(value))


def execute(output, template, runtime):
    output.mkdir(parents=True, exist_ok=False)
    source = json.loads((HERE / "source.json").read_bytes())
    archive = output / "original.knwf"
    with urllib.request.urlopen(source["download"], timeout=90) as stream:
        archive.write_bytes(stream.read())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != source["sha256"]:
        raise ValueError("Source archive differs from the pinned version")
    template_path = next(template.rglob("workflow.knime"))
    nodes = config(ET.parse(template_path).getroot(), "nodes")
    writer = next(
        n for n in nodes if "CSV Writer" in entry(n, "node_settings_file").get("value")
    )
    settings = ET.parse(
        template_path.parent / entry(writer, "node_settings_file").get("value")
    )
    cases = []
    for case, observer in enumerate((None, 141, 142), 1):
        folder = output / f"case-{case}"
        folder.mkdir()
        with zipfile.ZipFile(archive) as z:
            assert all(
                (folder / name).resolve().is_relative_to(folder)
                for name in z.namelist()
            )
            z.extractall(folder)
        original = next(folder.rglob("workflow.knime"))
        workflow = ET.parse(original)
        root = workflow.getroot()
        if observer is None:
            exports = [
                (138, 1, "input"),
                (131, 3, "initial-frontier"),
                (124, 1, "initial-relation"),
                (130, 1, "collected"),
                (137, 1, "final"),
            ]
        else:
            # Port 1 collects rows. Ports 2 and 3 drive recursion and retain their original links.
            (link,) = [
                e
                for e in config(root, "connections")
                if entry(e, "destID").get("value") == "130"
                and entry(e, "destPort").get("value") == "1"
            ]
            assert entry(link, "sourceID").get("value") == "135"
            setval(link, "sourceID", observer)
            exports = [
                (
                    130,
                    1,
                    "feedback-frontier" if observer == 141 else "feedback-relation",
                )
            ]
        for i, (source_id, port, name) in enumerate(exports):
            add_writer(
                root,
                original.parent,
                writer,
                settings,
                source_id,
                port,
                output / (name + ".csv"),
                i,
            )
        write(workflow, original)
        cases.append(
            dict(
                case=case,
                workflow=str(original.parent.relative_to(output)),
                expected_exports=[name + ".csv" for _, _, name in exports],
            )
        )
    (output / "selection.json").write_text(
        json.dumps(dict(cases=cases)), encoding="utf8"
    )
    run(runtime, output)
    for case in cases:
        result = json.loads((output / f"{case['case']:02}-knime-run.json").read_bytes())
        if result["exit_code"] or not result["exports_present"]:
            raise RuntimeError(f"KNIME case {case['case']} failed; see its batch log")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ("output", "writer_template", "runtime"):
        p.add_argument(key, type=Path)
    a = p.parse_args()
    execute(a.output.resolve(), a.writer_template, a.runtime)
