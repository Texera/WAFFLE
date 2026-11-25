"""Show how message identity changes which deliveries invoke the merge callback."""
import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
from verify import check, RESULTS


def plot(results, output):
    check(results)
    with (results / "arrival_orders.csv").open(newline="") as stream:
        example = {r["identity"]: r for r in csv.DictReader(stream)
                   if (r["branches"], r["copies_before_update"]) == ("4", "2")}
    delivered = example["publication"]["delivered_K"].split()
    if delivered != example["per_copy"]["delivered_K"].split() or delivered != ["2", "2", "3", "2", "2"]:
        raise ValueError("Expected the same four copies and one update under both policies")
    update_index = int(example["publication"]["copies_before_update"])
    positions = range(1, len(delivered) + 1)
    with plt.rc_context({"font.family": "DejaVu Serif", "font.size": 8, "pdf.fonttype": 42}):
        fig, ax = plt.subplots(figsize=(3.35, 1.63))
        fig.subplots_adjust(left=0.15, right=0.96, top=0.73, bottom=0.29)
        for mode, label, marker, style in (("per_copy", "ID per copy", "s", "--"),
                                            ("publication", "Shared ID", "o", "-")):
            callbacks, totals = [], []
            for i, value in enumerate(delivered):
                if mode == "per_copy" or i in (0, update_index):
                    callbacks.append(value)
                totals.append(len(callbacks))
            if callbacks != example[mode]["callback_K"].split():
                raise ValueError("Callback trace differs from the recorded run")
            ax.plot(positions, totals, linestyle=style, marker=marker, color="#25495e",
                    markersize=4, markerfacecolor="white" if mode == "per_copy" else "#25495e",
                    linewidth=1.2, label=label)
        ax.set(yticks=range(6), ylim=(0, 5.4), ylabel="Total callbacks")
        ax.set_xticks(positions, [f"{i} ({v})" for i, v in zip(positions, delivered)])
        ax.set_xlabel("Delivery number (arriving K)", labelpad=2)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(length=2, pad=2)
        fig.legend(*ax.get_legend_handles_labels(), loc="upper center",
                   frameon=False, ncol=2, fontsize=7.5)
        fig.savefig(output, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--results", type=Path, default=RESULTS)
    args = parser.parse_args()
    plot(args.results, args.output)
