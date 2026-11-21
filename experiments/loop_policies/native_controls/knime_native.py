"""Build KNIME workflows from native nodes and verify the collected iteration rows."""

from pathlib import Path
from xml.etree import ElementTree as E
from concurrent.futures import ThreadPoolExecutor
import csv
import os
import sys
import uuid
from inputs import RUN, cases, curve, model, save
from knime import NS, cfg, entry, array, write
from run_knime import launch

BASE = "org.knime.base.node."


def entries(node, values):
    for key, value in values.items():
        entry(node, key, value)


class Graph:
    def __init__(self, folder):
        self.folder = folder
        self.root = E.Element("{" + NS + "}config", key="workflow.knime")
        entries(
            self.root, dict(created_by="5.5.3", version="4.1.0", state="CONFIGURED")
        )
        cfg(self.root, "workflow_credentials")
        self.nodes = cfg(self.root, "nodes")
        self.edges = cfg(self.root, "connections")
        self.settings = []

    def node(self, label, factory, bundle="org.knime.base"):
        index = len(self.settings) + 1
        rel = f"{label} (#{index})/settings.xml"
        n = cfg(self.nodes, f"node_{index}")
        entries(
            n,
            dict(
                id=index,
                node_settings_file=rel,
                node_is_meta=False,
                node_type="NativeNode",
                ui_classname="org.knime.core.node.workflow.NodeUIInformation",
            ),
        )
        array(
            cfg(n, "ui_settings"), "extrainfo.node.bounds", [index * 150, 120, 85, 85]
        )
        root = E.Element("{" + NS + "}config", key="settings.xml")
        entries(
            root,
            {
                "node_file": "settings.xml",
                "state": "CONFIGURED",
                "factory": factory,
                "node-name": label,
                "name": label,
                "node-bundle-symbolic-name": bundle,
                "node-bundle-name": bundle,
                "node-bundle-version": "5.5.0",
                "node-bundle-vendor": "KNIME AG",
                "hasContent": False,
                "isInactive": False,
            },
        )
        cfg(root, "flow_stack")
        entry(
            cfg(root, "internal_node_subsettings"),
            "memory_policy",
            "CacheSmallInMemory",
        )
        cfg(root, "factory_settings")
        cfg(root, "ports")
        stores = cfg(root, "filestores")
        entry(stores, "file_store_location", "").set("isnull", "true")
        entry(stores, "file_store_id", str(uuid.uuid4()))
        self.settings.append((root, self.folder / rel))
        return index, cfg(root, "model")

    def link(self, src, dest, inport=1, outport=1):
        edge = cfg(self.edges, f"connection_{len(self.edges)}")
        entries(
            edge, dict(sourceID=src, destID=dest, sourcePort=outport, destPort=inport)
        )

    def finish(self):
        for root, path in self.settings:
            path.parent.mkdir(parents=True, exist_ok=True)
            write(path, root)
        write(self.folder / "workflow.knime", self.root)

    def input(self, rows):
        idx, m = self.node("Input", BASE + "io.tablecreator.TableCreator2NodeFactory")
        cols = list(rows[0])
        array(m, "rowIndices", [i for i in range(len(rows)) for _ in cols])
        array(m, "columnIndices", list(range(len(cols))) * len(rows))
        array(m, "values", [str(row[c]) for row in rows for c in cols])
        entries(
            m,
            dict(
                rowIdPrefix="Row",
                rowIdSuffix="",
                rowIdStartValue=0,
                highlightOutputTable=False,
            ),
        )
        props = cfg(m, "columnProperties")
        for j, name in enumerate(cols):
            c = cfg(props, str(j))
            entries(
                c,
                dict(
                    UserSetValues=False,
                    MissValuePattern="",
                    ReadPossValsFromFile=False,
                    SkipThisColumn=False,
                    ColumnName=name,
                ),
            )
            entries(
                cfg(c, "ColumnClass"),
                dict(cell_class="org.knime.core.data.def.DoubleCell", is_null=False),
            )
        return idx

    def formula(self, source, column, expression):
        idx, m = self.node(
            "Set " + column, "org.knime.ext.jep.JEPNodeFactory", "org.knime.ext.jep"
        )
        # The legacy JEP key selects replacement when true.
        entries(
            m,
            dict(
                expression=expression,
                replaced_column=column,
                append_column=True,
                convert_to_int=False,
            ),
        )
        self.link(source, idx)
        return idx

    def export(self, source, path):
        idx, m = self.node("Export", BASE + "io.csvwriter.CSVWriterNodeFactory")
        entries(
            m,
            dict(
                colSeparator=",",
                missing="",
                quoteBegin='"',
                quoteEnd='"',
                quoteMode="STRINGS",
                quoteReplacement="",
                sepReplacePattern="",
                ReplSepInStrings=False,
                writeColHeader=True,
                writeRowHeader=False,
                lineEndingMode="SYST",
                filename=path.as_posix(),
                fileOverwritePolicy="Overwrite",
                skipWriteColHeaderOnAppend=False,
                commentBegin="",
                commentEnd="",
                addTime=False,
                addUser=False,
                addTablename=False,
                userCommentLine="",
                gzip=False,
            ),
        )
        entry(m, "charSet", "").set("isnull", "true")
        entry(m, "decimalSeparator", ".", "xchar")
        self.link(source, idx)


def simple(graph, rule, scores):
    source = graph.input([dict(K=k, score=s) for k, s in scores.items()])
    start, m = graph.node(
        "Iterate over score rows",
        BASE + "meta.looper.variable.start.LoopStartVariable3NodeFactory",
    )
    selection = cfg(m, "column_selection")
    entries(
        selection, {"filter-type": "STANDARD", "enforce_option": "EnforceExclusion"}
    )
    for key in ("included_names", "excluded_names"):
        array(selection, key, [])
    entries(
        cfg(selection, "name_pattern"),
        dict(pattern="", type="Wildcard", caseSensitive=True, excludeMatching=False),
    )
    cfg(cfg(selection, "datatype"), "typelist")
    entries(
        m,
        dict(
            missing_value_policy="FAIL",
            default_value_string="missing",
            default_value_boolean="false",
            default_value_integer=0,
        ),
    )
    entry(m, "default_value_long", 0, "xlong")
    entry(m, "default_value_double", 0, "xdouble")
    graph.link(source, start)
    body, m = graph.node(
        "Return current row",
        BASE + "flowvariable.variabletotablerow.VariableToTableNodeFactory",
    )
    entry(m, "all", False)
    group = cfg(m, "variables")
    for name in ("K", "score"):
        entries(cfg(group, name), dict(name=name, type="DOUBLE"))
    graph.link(start, body)
    if rule == "target":
        end, m = graph.node(
            "Variable Condition Loop End",
            BASE + "meta.looper.condition.LoopEndConditionDynamicNodeFactory",
        )
        entries(
            m,
            dict(
                variableName="score",
                variableType="DOUBLE",
                value="-100",
                operator="GE",
                propagateLoopVariables=False,
            ),
        )
        for key, val in dict(
            addLastRows=True, addLastRowsOnly=False, addIterationColumn=False
        ).items():
            array(m, key, [val])
    else:
        end, m = graph.node("Loop End", BASE + "meta.looper.LoopEndDynamicNodeFactory")
        entries(
            m,
            dict(
                addIterationColumn=False,
                rowKeyPolicy="APPEND_SUFFIX",
                propagateLoopVariables=False,
            ),
        )
        for key, val in dict(
            ignoreEmptyTables=True,
            tolerateColumnTypes=False,
            tolerateChangingSpecs=False,
        ).items():
            array(m, key, [val])
    cfg(cfg(graph.settings[end - 1][0], "node_creation_config"), "Collector")
    graph.link(body, end)
    return end


def recursive(graph, rule, scores):
    initial = dict(K=2, score=0, again=0)
    if rule == "history":
        initial["previous"] = 0
    initial.update({f"s{k}": s for k, s in scores.items()})
    source = graph.input([initial])
    start, _ = graph.node(
        "Recursive Loop Start",
        BASE + "meta.looper.recursive.RecursiveLoopStartNodeFactory",
    )
    graph.link(source, start)
    body = graph.formula(start, "score", "if($K$ == 2,$s2$,if($K$ == 3,$s3$,$s4$))")
    if rule == "adaptive":
        step = "if($score$ < -250,2*$K$,$K$+1)"
        test = f"({step} <= 4) && ($score$ < -100)"
    else:
        step = "$K$+1"
        test = "($K$ < 4) && (($K$ == 2) || ($score$-$previous$ >= 150))"
    again = graph.formula(body, "again", f"if({test},1,0)")
    feedback, m = graph.node(
        "Keep continuing rows", BASE + "preproc.filter.row.RowFilterNodeFactory"
    )
    filt = cfg(m, "rowFilter")
    entries(
        filt,
        dict(
            RowFilter_TypeID="StringComp_RowFilter",
            ColumnName="again",
            include=True,
            deepFiltering=False,
            CaseSensitive=True,
            hasWildCards=False,
            isRegExpr=True,
            Pattern="1([.]0+)?",
        ),
    )
    graph.link(again, feedback)
    if rule == "history":
        feedback = graph.formula(feedback, "previous", "$score$")
    feedback = graph.formula(feedback, "K", step)
    end, m = graph.node(
        "Recursive Loop End", BASE + "meta.looper.recursive.RecursiveLoopEndNodeFactory"
    )
    entries(
        m,
        {
            "Use Flow Variable": False,
            "End Loop Variable Name": "",
            "CFG_AddIterationColumn": False,
            "CFG_End_Loop": "false",
            "CFG_MaxNrIterations": 8,
            "CFG_MinNrOfRows": 1,
            "CFG_OnlyLastData": False,
            "CFG_PropagateVariables": False,
        },
    )
    graph.link(body, end)
    graph.link(feedback, end, inport=2)
    return end


def run(spec):
    folder = RUN / "knime" / spec["id"]
    graph = Graph(folder / "workflow")
    scores = curve(spec["fixture"])
    rule = spec["task"]
    end = (simple if rule in ("sweep", "target") else recursive)(graph, rule, scores)
    graph.export(end, folder / "result.csv")
    graph.finish()
    code = launch(
        Path(os.environ["KNIME_HOME"]),
        [
            "-application",
            "org.knime.product.KNIME_BATCH_APPLICATION",
            "-reset",
            "-nosave",
            "-failonloaderror",
            "-workflowDir=" + str(graph.folder),
            "-data",
            str(folder / "workspace"),
        ],
        folder / "engine.log",
    )
    if code:
        raise RuntimeError(f"{spec['id']}: KNIME exit {code}")
    with (folder / "result.csv").open(newline="") as f:
        rows = [
            dict(K=int(float(r["K"])), score=float(r["score"]))
            for r in csv.DictReader(f)
        ]
    assert model.compare(spec["expected"], rows), rows
    save(folder / "observation.json", dict(rows=rows, iterations=len(rows)))
    print(spec["id"], [v["K"] for v in rows], flush=True)


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(
            pool.map(
                run,
                [s for s in cases() if len(sys.argv) == 1 or s["id"] in sys.argv[1:]],
            )
        )
