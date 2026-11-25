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
        fig, axes = plt.subplots(2, 2, figsize=(3.39, 2.27), sharex=True, sharey=True)
        fig.subplots_adjust(left=0.14, right=0.98, bottom=0.16, top=0.78, hspace=0.46, wspace=0.14)
        styles = (("#c1d9e2", ""), ("#397994", ""), ("white", "///"))
        for ax, fixture, scale in zip(axes.flat, FIXTURES, ("0.1×", "0.7×", "1×", "10×")):
            for visit, (color, hatch) in enumerate(styles):
                positions, values = [], []
                for i, rule in enumerate(RULES):
                    sequence = runs[rule, fixture]
                    if visit < len(sequence):
                        positions.append(i + (visit - 1) * 0.24)
                        values.append(sequence[visit])
                ax.bar(positions, values, width=0.23, color=color, hatch=hatch,
                       edgecolor="#284550", linewidth=0.5, label=f"Visit {visit + 1}")
            ax.set(xlim=(-0.52, 3.52), ylim=(0, 4.35), yticks=(0, 2, 4))
            ax.set_xticks(range(4), ["Sweep", "Target", "Adaptive", "Gain"], rotation=26, ha="right")
            ax.set_title(f"Input scale {scale}", fontsize=7.4, pad=2)
            ax.tick_params(length=2, pad=2, labelsize=6.8)
            ax.spines[["right", "top"]].set_visible(False)
        fig.supylabel("Cluster count K", x=0.01, fontsize=8)
        fig.legend(*axes.flat[0].get_legend_handles_labels(), loc="upper center",
                   frameon=False, ncol=3, fontsize=7.5, handlelength=1.1, columnspacing=1.2)
        fig.savefig(output, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


if __name__ == "__main__":
    draw(HERE.parents[2] / "figures" / "loop-policy-visits.pdf")
