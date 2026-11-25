"""Plot selected measured workflow sizes from the validated construction sweep."""
import csv
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent


@plt.rc_context({"font.family": "DejaVu Serif", "font.size": 8, "pdf.fonttype": 42})
def workflow_size():
    settings = (1, 8, 64, 1024, 16384, 131072)
    with (HERE / "size_sweep.csv").open(newline="") as stream:
        counts = {(int(r["candidates"]), r["workflow"]): r for r in csv.DictReader(stream)}
    fig, axes = plt.subplots(1, 2, figsize=(3.35, 1.86), sharey=True)
    fig.subplots_adjust(left=0.14, right=0.95, bottom=0.30, top=0.72, wspace=0.18)
    for ax, key, title in zip(axes, ("operators", "links"), ("Operators", "Data links")):
        for method, label, marker, style in (("loop", "Loop", "o", "--"),
                                              ("copies", "Explicit copies", "s", "-")):
            ax.plot(settings, [int(counts[k, method][key]) for k in settings], marker=marker,
                    linestyle=style, color="#264b61", markersize=3.5, linewidth=1, label=label)
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set(xlim=(0.65, 220000), ylim=(2, 650000), yticks=(10, 1000, 100000))
        ax.set_xticks((1, 64, 1024, 131072), ["1", "64", r"$2^{10}$", r"$2^{17}$"])
        ax.minorticks_off()
        ax.set_title(title, fontsize=8, pad=3)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(length=2, pad=2, labelsize=6.7)
    axes[0].set_ylabel("Count", labelpad=1)
    fig.text(0.53, 0.055, "Number of candidate K values", ha="center")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2,
               frameon=False, fontsize=7.5, handlelength=1.8)
    fig.savefig(HERE.parents[1] / "figures" / "loop-workflow-size.pdf",
                metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)


if __name__ == "__main__":
    workflow_size()
