"""Plot the branching and fixed-branch filter experiments against physical operator count."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullLocator

HERE = Path(__file__).resolve().parent
METHODS = (("X", "global", "#1761a0", "o", 4.0), ("Y", "modular", "#aa4800", "s", 2.9))


def plot_runs(ax, rows, method, metric, color, marker, size, line):
    counts = [row["operators"] for row in rows]
    stats = [row[method] for row in rows]
    values = [s[metric] for s in stats]
    if metric == "pooled_median_ms":
        low = [v - s["jvm_median_min_ms"] for v, s in zip(values, stats)]
        high = [s["jvm_median_max_ms"] - v for v, s in zip(values, stats)]
        ax.errorbar(
            counts,
            values,
            yerr=[low, high],
            fmt="none",
            ecolor=color,
            elinewidth=0.65,
            capsize=1.4,
        )
    (handle,) = ax.plot(
        counts,
        values,
        linestyle=line,
        marker=marker,
        markersize=size,
        color=color,
        linewidth=1.1,
        markeredgewidth=0.75,
    )
    return handle


def draw(metric, output):
    baseline = json.loads((HERE.parent / "summary.json").read_text())
    extended = json.loads((HERE / "summary.json").read_text())
    intermediate = json.loads((HERE / "intermediate.json").read_text())
    trials = intermediate["branch"]
    balanced = [r for r in baseline if r["inside"] == r["outside"]]
    balanced += [r for r in extended if r["filters_per_group"] == 0 and r["inside"] > 4]
    balanced.sort(key=lambda r: r["operators"])
    unequal = [r for r in baseline if r["inside"] != r["outside"]]
    filters = sorted(
        (
            r
            for r in extended + intermediate["filter"]
            if r["inside"] == r["outside"] == 4
        ),
        key=lambda r: r["operators"],
    )
    timing = metric == "pooled_median_ms"
    with plt.rc_context(
        {"font.family": "DejaVu Serif", "font.size": 7.5, "pdf.fonttype": 42}
    ):
        fig, (branch_ax, filter_ax) = plt.subplots(
            1, 2, sharey=True, figsize=(3.35, 2.12)
        )
        fig.subplots_adjust(left=0.17, right=0.98, bottom=0.23, top=0.76, wspace=0.13)
        handles = []
        for method, _, color, marker, size in METHODS:
            handle = plot_runs(
                branch_ax, balanced, method, metric, color, marker, size, "-"
            )
            handles.append(handle)
            plot_runs(branch_ax, unequal, method, metric, color, "x", 4, "none")
            plot_runs(filter_ax, filters, method, metric, color, marker, size, "-")
            # The final repeated point anchors the dotted series. A timeout breaks the line.
            last = balanced[-1]
            trial_metric = "total_ms" if timing else "search_states"
            sizes = [r["operators"] for r in trials]
            values = [r[method].get(trial_metric, float("nan")) for r in trials]
            branch_ax.plot(
                [last["operators"], *sizes],
                [last[method][metric], *values],
                linestyle=":",
                linewidth=1.0,
                color=color,
                zorder=1,
            )
            branch_ax.plot(
                sizes,
                values,
                linestyle="none",
                marker=marker,
                color=color,
                markerfacecolor="white",
                markersize=size,
            )
            if timing:
                for trial in trials:
                    outcome = trial[method]
                    if outcome["status"] != "timeout":
                        continue
                    x = trial["operators"]
                    limit_ms = 1000 * outcome["limit_s"]
                    branch_ax.plot(x, limit_ms, marker="_", markersize=4, color=color)
                    branch_ax.annotate(
                        "",
                        xy=(x, limit_ms),
                        xytext=(0, 7),
                        textcoords="offset points",
                        arrowprops=dict(
                            arrowstyle="<-", color=color, lw=0.8, shrinkA=0, shrinkB=0
                        ),
                    )
        for ax, title in ((branch_ax, "Add branch groups"), (filter_ax, "Add filters")):
            ax.set_title(title, fontsize=7.6, pad=4)
            ax.set_xlim(7, 108)
            ax.set_yscale("log")
            ax.yaxis.set_minor_locator(NullLocator())
            ax.grid(axis="y", color="#dddddd", linewidth=0.5)
            ax.set_axisbelow(True)
            ax.tick_params(labelsize=6.6, length=2.4, pad=2)
            ax.spines[["right", "top"]].set_visible(False)
        branch_ax.set_xticks([12, 36, 60, 84, 100])
        filter_ax.set_xticks([36, 52, 68, 84, 100])
        if timing:
            # Reserve space above the highest observed time or timeout arrow.
            highest_ms = max(
                r[m]["total_ms"]
                if r[m]["status"] == "completed"
                else 1000 * r[m]["limit_s"]
                for r in trials
                for m, *_ in METHODS
            )
            branch_ax.set_ylim(1.7, highest_ms * 6)
            ticks = [10**i for i in range(1, 9) if 10**i <= highest_ms * 2]
            branch_ax.set_yticks(ticks, [f"{ms / 1000:g}" for ms in ticks])
            branch_ax.set_ylabel("Planning time (s, log scale)")
        else:
            highest = max(
                row[method].get("search_states", 0)
                for row in trials
                for method, *_ in METHODS
            )
            branch_ax.set_ylim(2.8, max(1024, highest) * 1.65)
            ticks = [
                n for n in (4, 32, 256, 2048, 16384, 131072) if n <= max(1024, highest)
            ]
            if highest >= 4 * ticks[-1]:
                ticks.append(highest)
            branch_ax.set_yticks(ticks, [f"{n:,}" for n in ticks])
            branch_ax.set_ylabel("Visited states (log scale)")
        fig.legend(
            handles,
            [f"{name} ({label})" for name, label, *_ in METHODS],
            loc="upper center",
            ncol=2,
            frameon=False,
            fontsize=7.3,
            bbox_to_anchor=(0.56, 1.015),
            handlelength=1.6,
            columnspacing=1.25,
        )
        fig.text(0.575, 0.055, "Physical operators", ha="center")
        fig.savefig(output, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


if __name__ == "__main__":
    root = HERE.parents[2]
    draw("search_states", root / "figures/xy-search-states.pdf")
    draw("pooled_median_ms", root / "figures/xy-planning-time.pdf")
