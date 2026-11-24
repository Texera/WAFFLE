"""Plot the number of labeled boundaries per distinct published plan."""
import csv
from collections import Counter
import json
from pathlib import Path
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent


def bin_counts():
    with (HERE / "plans.csv").open(newline="") as stream:
        seen = {row["fingerprint"] for row in csv.DictReader(stream)}
    counts = Counter({"2": len(seen)})
    with (HERE / "multiple.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            size = int(row["named_starts"]) + int(row["named_ends"])
            if size < 3 or int(row["reachable_start_end_pairs"]) < 1 or row["fingerprint"] in seen:
                raise ValueError("Invalid boundary count or repeated plan")
            seen.add(row["fingerprint"])
            counts["3–4" if size <= 4 else "5–6" if size <= 6 else "7+"] += 1
    total = json.loads((HERE / "summary.json").read_bytes())["distinct_connected_plans"]
    if sum(counts.values()) != total:
        raise ValueError("Histogram does not account for every plan")
    return counts


def draw():
    counts = bin_counts()
    labels = ["2", "3–4", "5–6", "7+"]
    values = [counts[label] for label in labels]
    with plt.rc_context({"font.family": "DejaVu Serif", "font.size": 8, "pdf.fonttype": 42}):
        fig, ax = plt.subplots(figsize=(3.35, 1.49))
        fig.subplots_adjust(left=0.13, right=0.95, top=0.82, bottom=0.29)
        ax.barh(labels, values, height=0.60, color=["#195779", "#72a8b5", "#72a8b5", "#72a8b5"])
        for i, value in enumerate(values):
            ax.annotate(str(value), (value, i), xytext=(3, 0), textcoords="offset points", va="center")
        ax.invert_yaxis()
        ax.set_xlim(0, max(values) * 1.13)
        ax.set_xticks([0, 200, 400, 600, 800])
        ax.set_xlabel("Distinct published plans", labelpad=2)
        ax.set_title("Labeled starts and ends per plan", loc="left", fontsize=8, pad=4)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        fig.savefig(HERE.parents[2] / "figures" / "published-loop-boundaries.pdf",
                    metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


if __name__ == "__main__":
    draw()
