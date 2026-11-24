"""Attach CSV writers to both original seeds and loop results, preserving both recursive bodies."""
import argparse
import copy
import hashlib
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_knime import NS, config, entry, setval, write
from run_knime import run


def prepare(folder, writer_template, runtime):
    folder.mkdir(parents=True, exist_ok=False)
    spec = json.loads(Path(__file__).with_name("source.json").read_text())
    archive = folder / "example.knwf"
    with urllib.request.urlopen(spec["download"], timeout=60) as stream:
        archive.write_bytes(stream.read())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != spec["sha256"]:
        raise ValueError("Upstream example has changed")
    with zipfile.ZipFile(archive) as z:
        if any(not (folder / name).resolve().is_relative_to(folder) for name in z.namelist()):
            raise ValueError("Unexpected archive path")
        z.extractall(folder)
    original = next(folder.rglob("workflow.knime"))
    workflow = ET.parse(original)
    template = next(writer_template.rglob("workflow.knime"))
    writer = next(n for n in config(ET.parse(template).getroot(),"nodes")
                  if "CSV Writer" in entry(n,"node_settings_file").get("value"))
    settings = ET.parse(template.parent / entry(writer,"node_settings_file").get("value"))
    exports = {1: "sum-input", 8: "fib-input", 7: "sum-output", 3: "fib-output"}
    for node_id, name in exports.items():
        sink_id = 100 + node_id
        sub = original.parent / f"Evidence {sink_id}"
        sub.mkdir()
        node = copy.deepcopy(writer)
        node.set("key", f"node_{sink_id}")
        setval(node, "id", sink_id)
        setval(node, "node_settings_file", f"{sub.name}/settings.xml")
        config(workflow.getroot(), "nodes").append(node)
        target = copy.deepcopy(settings)
        model = config(target.getroot(), "model")
        setval(model, "filename", (folder / f"{name}.csv").as_posix())
        setval(model, "writeColHeader", "true")
        setval(model, "writeRowHeader", "true")
        variables = config(target.getroot(), "variables")
        for child in list(variables):
            variables.remove(child)
        write(target, sub / "settings.xml")
        link = ET.SubElement(config(workflow.getroot(), "connections"), f"{{{NS}}}config", key=f"connection_evidence_{sink_id}")
        for k, v in [("sourceID",node_id),("destID",sink_id),("sourcePort",1),("destPort",1)]:
            ET.SubElement(link, f"{{{NS}}}entry", key=k, type="xint", value=str(v))
    write(workflow, original)
    record = {"case":7, "workflow":original.parent.name, "expected_exports":[n + ".csv" for n in exports.values()]}
    (folder / "selection.json").write_text(json.dumps({"cases":[record]}))
    run(runtime, folder)
    status = json.loads((folder / "07-knime-run.json").read_text())
    if status["exit_code"] or not status["exports_present"]:
        raise RuntimeError("Original execution failed. See 07-knime.log.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for key in ["folder","writer_template","runtime"]:
        p.add_argument(key,type=Path)
    args = p.parse_args()
    prepare(args.folder.resolve(), args.writer_template, args.runtime)
