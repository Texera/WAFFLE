"""Count graph operators and data links directly from the saved engine workflows."""
import json
from pathlib import Path

import matplotlib.pyplot as plt


@plt.rc_context({"font.family": "DejaVu Serif", "font.size": 8, "pdf.fonttype": 42})
def workflow_size():
    folder = Path(__file__).resolve().parent / "results"
    counts = {}
    settings = (1, 4, 8)
    for values in settings:
        for method in ("loop", "copies"):
            totals = set()
            for tuples in (200, 2000):
                workflow = json.loads((folder / f"n{tuples}-i{values}-{method}.json").read_text())
                totals.add((len(workflow["operators"]), len(workflow["links"])))
            if len(totals) != 1:
                raise ValueError("Workflow size unexpectedly depends on input cardinality")
            counts[values, method] = totals.pop()

    fig, axes = plt.subplots(1, 2, figsize=(3.35, 1.82), sharey=True)
    fig.subplots_adjust(left=0.17, right=0.98, bottom=0.22, top=0.69, wspace=0.30)
    for measure, (ax, title) in enumerate(zip(axes, ("Operators", "Data links"))):
        for method, label, color, offset in (("loop", "Loop", "#1761a0", -0.17),
                                            ("copies", "Explicit copies", "#b34e00", 0.17)):
            bars = ax.barh([i + offset for i in range(3)],
                           [counts[v, method][measure] for v in settings],
                           height=0.29, color=color, label=label)
            ax.bar_label(bars, padding=2, fontsize=7)
        ax.set_title(title, fontsize=8, pad=2)
        ax.set_xlim(0, 20)
        ax.set_xticks((0, 8, 16))
        ax.set_yticks(range(3), settings)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(length=2, labelsize=7)
    axes[0].invert_yaxis()
    axes[0].set_ylabel("Values of K", fontsize=8)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2,
               frameon=False, fontsize=7.5, handlelength=1.2, columnspacing=1.6)
    fig.savefig(Path(__file__).resolve().parents[2] / "figures" / "loop-workflow-size.pdf", metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)


if __name__ == "__main__":
    workflow_size()
