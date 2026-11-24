"""Plot the cluster counts visited in the recorded native loop-policy runs."""
import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
FIXTURES = ("immediate", "near", "far", "unreachable")
RULES = ("sweep", "target", "adaptive", "history")


def traces():
    by_case = {}
    with (HERE / "observations.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            key = row["rule"], row["fixture"]
            output = json.loads(row["output"])
            sequence = tuple(point["K"] for point in output)
            engines = by_case.setdefault(key, {})
            if row["engine"] in engines:
                raise ValueError(f"Duplicate run for {key}")
            engines[row["engine"]] = sequence
    if set(by_case) != {(rule, fixture) for rule in RULES for fixture in FIXTURES}:
        raise ValueError("Missing or unexpected rule/input pair")
    result = {}
    for key, engines in by_case.items():
        if set(engines) != {"waffle", "knime", "n8n", "rapidminer"} or len(set(engines.values())) != 1:
            raise ValueError(f"Incomplete or inconsistent runs for {key}")
        seq = engines["waffle"]
        if not seq or seq[0] != 2 or sorted(set(seq)) != list(seq) or seq[-1] > 4:
            raise ValueError(f"Unexpected traversal {seq}")
        result[key] = seq
    return result


def draw(output):
    runs = traces()
    with plt.rc_context({"font.family": "DejaVu Serif", "font.size": 8, "pdf.fonttype": 42}):
        fig, axes = plt.subplots(1, 4, sharey=True, figsize=(3.39, 1.52))
        fig.subplots_adjust(left=0.215, right=0.99, bottom=0.27, top=0.70, wspace=0.15)
        for ax, fixture, scale in zip(axes, FIXTURES, ("0.1×", "0.7×", "1×", "10×")):
            for i, rule in enumerate(RULES):
                visits = runs[rule, fixture]
                for start, end in zip(visits, visits[1:]):
                    curvature = 0.20 if end - start > 1 else 0
                    ax.annotate("", xy=(end, i), xytext=(start, i),
                                arrowprops={"arrowstyle": "-", "color": "#436579", "lw": 0.8,
                                            "connectionstyle": f"arc3,rad={curvature}"})
                ax.scatter(visits, [i] * len(visits), s=18, color="#185873", zorder=3)
            ax.set(xlim=(1.65, 4.35), ylim=(3.43, -0.43), xticks=(2, 3, 4))
            ax.set_yticks(range(4), ["Sweep", "Target", "Adaptive", "Gain"])
            ax.set_title(scale, fontsize=8, pad=3)
            ax.spines[:].set_visible(False)
            ax.set_axisbelow(True)
            ax.grid(axis="x", color="#d6dce0", linestyle=":", lw=0.5)
            ax.tick_params(length=0, pad=2, labelsize=7.6)
        fig.text(0.59, 0.95, "Input coordinate scale", ha="center", va="top", fontsize=8)
        fig.text(0.59, 0.055, "Cluster count K", ha="center", fontsize=8)
        fig.savefig(output, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


if __name__ == "__main__":
    draw(HERE.parents[2] / "figures" / "loop-policy-visits.pdf")
