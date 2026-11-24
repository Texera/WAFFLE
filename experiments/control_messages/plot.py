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
    with plt.rc_context({"font.family": "DejaVu Serif", "font.size": 8, "pdf.fonttype": 42}):
        fig, ax = plt.subplots(figsize=(3.35, 1.50))
        fig.subplots_adjust(left=0.32, right=0.98, top=0.79, bottom=0.24)
        for y, mode in enumerate(("delivered", "publication", "per_copy")):
            shown = []
            ax.hlines(y, 0, len(delivered) - 1, color="#aaa", lw=0.7)
            for i, k in enumerate(delivered):
                if mode == "publication" and k in shown:
                    ax.plot(i, y, marker="x", color="#555", ms=5)
                    continue
                shown.append(k)
                ax.plot(i, y, marker="o" if k == "2" else "s", ms=12,
                        color="#175e82" if k == "2" else "#903e19")
                ax.text(i, y, k, ha="center", va="center", color="white", fontsize=7)
            if mode != "delivered" and shown != example[mode]["callback_K"].split():
                raise ValueError("Callback trace differs from the recorded run")
        ax.set(xlim=(-0.45, 4.45), ylim=(2.50, -0.55))
        ax.set_yticks([0, 1, 2], ["Delivered K", "Shared ID", "ID per copy"])
        ax.set_xticks(range(5), range(1, 6))
        ax.xaxis.tick_top()
        ax.xaxis.set_label_position("top")
        ax.set_xlabel("Delivery order", labelpad=2)
        ax.tick_params(length=0, pad=2, labelsize=7.5)
        ax.spines[:].set_visible(False)
        fig.text(0.63, 0.10, "×  callback suppressed", ha="center", fontsize=7.5)
        fig.savefig(output, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--results", type=Path, default=RESULTS)
    args = parser.parse_args()
    plot(args.results, args.output)
