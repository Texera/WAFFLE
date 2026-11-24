"""Draw the matched stopping-policy comparison from the checked measurements."""
from pathlib import Path
import csv
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

HERE = Path(__file__).resolve().parent
INPUTS = ("low", "mixed", "high")
FRACTIONS = ("1/3", "1/2", "2/3")


def draw(source, output):
    with source.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    graphs = {row["graph"] for row in rows}
    keys = {(row["graph"], row["input"], row["fraction"]) for row in rows}
    expected = {(graph, fixture, fraction) for graph in graphs for fixture in INPUTS for fraction in FRACTIONS}
    if len(graphs) != 933 or len(rows) != len(keys) or keys != expected:
        raise ValueError("Incomplete or duplicate graph/input/fraction observations")
    cmap = LinearSegmentedColormap.from_list("count", ("#f1f4f6", "#195779"))
    with plt.rc_context({"font.family": "DejaVu Serif", "font.size": 8, "pdf.fonttype": 42}):
        fig, axes = plt.subplots(1, 2, figsize=(3.38, 1.72), sharey=True)
        fig.subplots_adjust(left=0.15, right=0.99, bottom=0.31, top=0.83, wspace=0.12)
        for ax, title, first in zip(axes, ("On first visit", "By final visit"), (True, False)):
            counts = np.zeros((len(INPUTS), len(FRACTIONS)), dtype=int)
            for row in rows:
                if int(row["threshold_met"]) and (not first or int(row["visits"]) == 1):
                    counts[INPUTS.index(row["input"]), FRACTIONS.index(row["fraction"])] += 1
            ax.imshow(counts, vmin=0, vmax=len(graphs), cmap=cmap, aspect="auto")
            for (i, j), count in np.ndenumerate(counts):
                ax.text(j, i, str(count), ha="center", va="center", color="white" if count > 0.6 * len(graphs) else "#182329")
            for split in (0.5, 1.5):
                ax.axvline(split, color="white", lw=1)
                ax.axhline(split, color="white", lw=1)
            ax.set_title(title, fontsize=8)
            ax.set_xticks(range(3), FRACTIONS)
            ax.set_yticks(range(3), [v.title() for v in INPUTS])
            ax.tick_params(length=0, pad=3)
            ax.spines[:].set_visible(False)
        fig.text(0.57, 0.07, "Required fraction of rows", ha="center")
        fig.savefig(output, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


if __name__ == "__main__":
    draw(HERE / "stopping_sensitivity.csv", HERE.parents[1] / "figures" / "stopping-sensitivity.pdf")
