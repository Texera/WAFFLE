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
    fig, axes = plt.subplots(1, 2, figsize=(3.35, 1.85), sharey=True)
    fig.subplots_adjust(left=0.21, right=0.98, bottom=0.21, top=0.73, wspace=0.22)
    for ax, key, title in zip(axes, ("operators", "links"), ("Operators", "Data links")):
        for i, k in enumerate(settings):
            values = [int(counts[k, method][key]) for method in ("loop", "copies")]
            ax.plot(values, [i, i], color="#bbb", linewidth=0.8, zorder=1)
        for method, label, marker, color in (("loop", "Loop", "o", "#1761a0"),
                                               ("copies", "Explicit copies", "s", "#aa4800")):
            ax.scatter([int(counts[k, method][key]) for k in settings], range(len(settings)),
                       s=13, color=color, marker=marker, label=label, zorder=2)
        ax.set_xscale("log")
        ax.set(xlim=(1.4, 600000), xticks=[2, 1000, 100000], xticklabels=["2", r"$10^3$", r"$10^5$"],
               yticks=range(len(settings)), yticklabels=[f"{k:,}" for k in settings])
        ax.minorticks_off()
        ax.set_title(title, fontsize=8, pad=3)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(length=2, labelsize=7)
    axes[0].invert_yaxis()
    axes[0].set_ylabel("Values of K")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", ncol=2,
               frameon=False, fontsize=7.5, handlelength=0.9)
    fig.savefig(HERE.parents[1] / "figures" / "loop-workflow-size.pdf",
                metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)


if __name__ == "__main__":
    workflow_size()
