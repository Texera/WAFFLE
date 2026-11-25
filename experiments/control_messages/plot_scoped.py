"""Figure 23. Each bar is the callback count observed in both arrival orders."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from verify_scoped import RESULTS, check_original
from scoped_orders import CASES, verify


def counts(records):
    output = []
    for case in CASES:
        observed = {len(r["events"][-1]["callbacks"]) for r in records if r["case"] == case}
        if len(observed) != 1:
            raise ValueError(f"Counts differ across orders for {case}: {observed}")
        output.append(observed.pop())
    return output


def plot(results, path):
    original = json.loads((results / "receiver-original.json").read_text())
    scoped = json.loads((results / "receiver.json").read_text())
    check_original(original)
    verify(scoped)
    with plt.rc_context({"font.size": 8, "pdf.fonttype": 42}):
        fig, ax = plt.subplots(figsize=(3.32, 1.50))
        fig.subplots_adjust(left=.33, right=.95, top=.79, bottom=.29)
        y = [2, 1, 0]
        ax.barh([i + .17 for i in y], counts(original), .30, color="#bec9cf",
                edgecolor="#475b65", linewidth=.6, label="Message ID")
        ax.barh([i - .17 for i in y], counts(scoped), .30, color="#264e64",
                label="Write-once")
        ax.set_yticks(y, ["Equal K", "Separate names", "Conflicting K"])
        ax.set(xticks=[0, 1, 2], xlim=(0, 2.05), xlabel="Handler calls after two deliveries")
        ax.tick_params(axis="y", length=0)
        ax.tick_params(axis="x", length=2)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.legend(loc="lower center", bbox_to_anchor=(.47, 1.01), ncol=2, frameon=False,
                  columnspacing=1, handlelength=1.3)
        fig.savefig(path, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--results", type=Path, default=RESULTS)
    args = parser.parse_args()
    plot(args.results, args.output)
