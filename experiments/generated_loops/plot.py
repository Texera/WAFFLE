"""Draw the matched stopping-policy comparison from the checked measurements."""
from pathlib import Path
import csv
import matplotlib.pyplot as plt
import numpy as np
from corpus import cases

HERE = Path(__file__).resolve().parent
INPUTS = ("low", "mixed", "high")
FRACTIONS = ("1/3", "1/2", "2/3")


def draw(source, output):
    with source.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    graphs = {row["graph"] for row in rows}
    keys = {(row["graph"], row["input"], row["fraction"]) for row in rows}
    expected = {(graph, fixture, fraction) for graph in graphs for fixture in INPUTS for fraction in FRACTIONS}
    expected_ids = {str(i) for i, (family, _, _) in enumerate(cases()) if family == "stopping"}
    if graphs != expected_ids or len(rows) != len(keys) or keys != expected:
        raise ValueError("Incomplete or duplicate graph/input/fraction observations")
    observed = np.zeros((len(INPUTS), len(FRACTIONS), 2), dtype=int)
    for row in rows:
        if int(row["threshold_met"]):
            counts = observed[INPUTS.index(row["input"]), FRACTIONS.index(row["fraction"])]
            counts[0] += int(row["visits"]) == 1
            counts[1] += 1
    with plt.rc_context({"font.family": "DejaVu Serif", "font.size": 8, "pdf.fonttype": 42}):
        fig, axes = plt.subplots(1, 3, figsize=(3.39, 1.83), sharey=True)
        fig.subplots_adjust(left=0.11, right=0.98, bottom=0.27, top=0.69, wspace=0.20)
        for i, (ax, fixture) in enumerate(zip(axes, INPUTS)):
            for stage, (label, fill) in enumerate((("On first visit", "#2a6177"), ("By final visit", "#dae8ed"))):
                y = np.arange(len(FRACTIONS)) + (stage - 0.5) * 0.36
                values = observed[i, :, stage]
                ax.barh(y, values, height=0.34, color=fill, linewidth=0.5,
                        edgecolor="#284550", label=label)
                for pos, value in zip(y, values):
                    inside = value > 3000
                    ax.text(value + (-100 if inside else 100), pos, f"{value:,}",
                            ha="right" if inside else "left", va="center", fontsize=6,
                            color="white" if inside and stage == 0 else "black")
            ax.set(xlim=(0, 5650), xticks=(0, 5000), xticklabels=("0", "5k"))
            ax.set_yticks(range(3), FRACTIONS)
            ax.set_title(fixture.title(), fontsize=8, pad=4)
            ax.tick_params(length=2, pad=2, labelsize=7)
            ax.spines[["top", "right"]].set_visible(False)
        axes[0].invert_yaxis()
        fig.text(0.55, 0.05, "Graphs meeting the threshold", ha="center")
        fig.legend(*axes[0].get_legend_handles_labels(), loc="upper center", frameon=False,
                   ncol=2, fontsize=7.5, handlelength=1.3)
        fig.savefig(output, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


if __name__ == "__main__":
    draw(HERE / "stopping_sensitivity.csv", HERE.parents[1] / "figures" / "stopping-sensitivity.pdf")
