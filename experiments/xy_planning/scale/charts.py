"""Draw the two planning figures from the baseline and scale-extension summaries."""

from pathlib import Path
import json
import csv

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator

HERE = Path(__file__).resolve().parent


def draw(metric, output):
    baseline = json.loads((HERE.parent / "summary.json").read_text())
    extended = json.loads((HERE / "summary.json").read_text())
    branch = sorted(
        [*baseline, extended[1]], key=lambda r: (r["operators"], r["inside"])
    )
    serial = [extended[i] for i in (0, 2, 3)]
    data = [*branch, *serial]
    labels = [f"{r['operators']}   ({r['inside']}/{r['outside']})" for r in branch]
    labels.append("100   (12/12)*")
    labels += [f"{r['operators']}   (+{8 * r['filters_per_group']})" for r in serial]
    y = [*range(7), 9.5, 10.5, 11.5]
    with plt.rc_context(
        {"font.family": "DejaVu Serif", "font.size": 7.5, "pdf.fonttype": 42}
    ):
        fig, ax = plt.subplots(figsize=(3.35, 2.75))
        fig.subplots_adjust(left=0.27, right=0.97, top=0.90, bottom=0.19)
        ax.set_xscale("log")
        ax.set_axisbelow(True)
        ax.grid(axis="x", color="#dedede", lw=0.5)
        for name, color, marker, shift in (
            ("X", "#1761a0", "o", -0.14),
            ("Y", "#aa4800", "s", 0.14),
        ):
            values = [r[name][metric] for r in data]
            positions = [v + shift for v in y]
            if metric == "pooled_median_ms":
                lower = [v - r[name]["jvm_median_min_ms"] for v, r in zip(values, data)]
                upper = [r[name]["jvm_median_max_ms"] - v for v, r in zip(values, data)]
                ax.errorbar(
                    values,
                    positions,
                    xerr=[lower, upper],
                    fmt="none",
                    ecolor=color,
                    lw=0.85,
                    capsize=2,
                )
            ax.plot(
                values,
                positions,
                ls="none",
                marker=marker,
                markersize=4,
                color=color,
                label="X (global)" if name == "X" else "Y (modular)",
            )
            with (HERE / "dense" / name / "outcome.csv").open(newline="") as stream:
                (trial,) = csv.DictReader(stream)
            if trial["status"] == "completed":
                value = (
                    int(trial["states"])
                    if metric == "search_states"
                    else int(trial["total_ns"]) / 1e6
                )
                ax.plot(
                    value,
                    7 + shift,
                    marker=marker,
                    markerfacecolor="white",
                    markeredgecolor=color,
                    markersize=4,
                    linestyle="none",
                )
            elif metric == "pooled_median_ms":
                limit = int(trial["limit_s"]) * 1000
                ax.annotate(
                    "",
                    xy=(limit * 1.42, 7 + shift),
                    xytext=(limit, 7 + shift),
                    arrowprops=dict(
                        arrowstyle="->", color=color, lw=1.1, shrinkA=0, shrinkB=0
                    ),
                )
        ax.set_ylim(12.15, -0.7)
        ax.set_yticks([*range(8), *y[-3:]], labels)
        ax.tick_params(axis="y", length=0, pad=4)
        ax.axhline(8.25, color="#aaa", lw=0.6)
        ax.text(
            -0.035,
            8.76,
            "Ops (+filters)",
            ha="right",
            va="center",
            transform=ax.get_yaxis_transform(),
            fontsize=6.7,
            fontstyle="italic",
        )
        ax.text(
            -0.035,
            1.045,
            "Ops (in/out)",
            ha="right",
            va="center",
            transform=ax.transAxes,
            fontsize=6.7,
            fontstyle="italic",
        )
        ax.legend(
            loc="lower left",
            bbox_to_anchor=(0, 1.005),
            frameon=False,
            ncol=2,
            fontsize=7,
            handlelength=1,
            handletextpad=0.3,
            columnspacing=1.4,
            borderaxespad=0,
        )
        if metric == "search_states":
            ticks = [4, 16, 64, 256, 1024, 8192]
            ax.set_xlim(2.4, 13500)
            ax.set_xlabel("Visited states (log scale)")
            ax.set_xticks(ticks, [str(i) for i in ticks], fontsize=6.8)
        else:
            ticks = [3, 30, 300, 3000, 30000, 120000]
            ax.set_xlim(1.8, 205000)
            ax.set_xlabel("Planning time (s, log scale)")
            ax.set_xticks(ticks, [f"{i / 1000:g}" for i in ticks], fontsize=6.8)
        ax.xaxis.set_minor_locator(NullLocator())
        ax.spines[["top", "right", "left"]].set_visible(False)
        fig.savefig(output, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


if __name__ == "__main__":
    root = HERE.parents[2]
    draw("search_states", root / "figures/xy-search-states.pdf")
    draw("pooled_median_ms", root / "figures/xy-planning-time.pdf")
