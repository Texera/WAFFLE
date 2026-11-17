"""Plot the checked arrival orders from the Section 5 experiment."""
import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from verify import check, RESULTS, WIDTHS


def plot(results, output):
    counts = check(results)
    fig, ax = plt.subplots(figsize=(3.30, 1.70))
    fig.subplots_adjust(left=0.18, right=0.97, top=0.94, bottom=0.28)
    for mode, label, color, style, marker in (
        ("publication", "One ID per message", "#186386", "-", "o"),
        ("per_copy", "One ID per copy", "#843b24", "--", "s"),
    ):
        ax.plot(WIDTHS, [counts[mode][w] for w in WIDTHS], label=label,
                color=color, linestyle=style, marker=marker, markersize=4.5,
                markerfacecolor="none" if mode == "per_copy" else color)
    ax.set(xlabel="Branches", ylabel="Orders keeping K = 3", xticks=WIDTHS,
           yticks=[0, 2, 4, 6, 8], ylim=(-0.15, 8.6))
    ax.tick_params(labelsize=8)
    ax.yaxis.label.set_fontsize(8)
    ax.grid(axis="y", alpha=0.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", frameon=False, fontsize=7, handlelength=2)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--results", type=Path, default=RESULTS)
    args = parser.parse_args()
    plot(args.results, args.output)
