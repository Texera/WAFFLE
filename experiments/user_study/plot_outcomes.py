"""Plot the ten-participant loop study from aggregate counts."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
RESULTS = Path(__file__).with_name("results")
BLUE = "#28536b"
GRAY = "#c4ced4"


def load_counts():
    with (RESULTS / "group-results.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    with (RESULTS / "separate-feedback.csv").open(newline="", encoding="utf-8") as stream:
        feedback, = csv.DictReader(stream)
    cohort, = [int(r["value"]) for r in rows if r["measure"] == "Cohort"]
    completion = {"WAFFLE": [], "System A": []}
    for task in ("Configure the loop", "Change the stopping rule", "Both tasks"):
        pairs = {r["statistic"]: int(r["value"]) for r in rows
                 if r["measure"] == "Independent completion" and r["task_or_step"] == task
                 and r["tool_or_comparison"] == "Across tools" and int(r["denominator"]) == cohort}
        assert set(pairs) == {"Both tools", "WAFFLE only", "System A only", "Neither tool"}
        assert sum(pairs.values()) == cohort
        for system in completion:
            completion[system].append(pairs["Both tools"] + pairs[system + " only"])
    easier, = [int(r["value"]) for r in rows if r["measure"] == "Paired ease comparison"
               and r["task_or_step"] == "Change the stopping rule" and r["statistic"] == "WAFFLE easier"
               and int(r["denominator"]) == cohort]
    assert int(feedback["participants_asked"]) == cohort
    joint = int(feedback["participants_mentioning_both"])
    assert 0 <= joint <= cohort
    return cohort, completion, [easier, joint]


def plot():
    cohort, completion, feedback = load_counts()
    with plt.rc_context({"font.size": 7.3, "pdf.fonttype": 42, "axes.linewidth": .5}):
        fig, (left, right) = plt.subplots(1, 2, sharey=True, figsize=(3.45, 1.58),
                                         gridspec_kw={"width_ratios": [1.28, 1]})
        fig.subplots_adjust(left=.107, right=.976, bottom=.212, top=.70, wspace=.22)
        for ax in (left, right):
            ax.set_ylim(0, cohort + .5)
            ax.set_yticks(range(0, cohort + 1, 2))
            ax.set_axisbelow(True)
            ax.yaxis.grid(True, color="#d7dce0", linewidth=.4)
            ax.spines[["top", "right", "left"]].set_visible(False)
            ax.tick_params(length=0, pad=2)
        left.set_ylabel(f"Participants (out of {cohort})", fontsize=7.1, labelpad=1.5)
        for name, offset, color in [("WAFFLE", -.18, BLUE), ("System A", .18, GRAY)]:
            bars = left.bar([i + offset for i in range(3)], completion[name], .32,
                            color=color, edgecolor="#43525b", linewidth=.35, label=name)
            left.bar_label(bars, padding=1, fontsize=7.1)
        left.set_xticks(range(3), ["Set K\nrange", "Change\nstop rule", "Both\ntasks"])
        left.set_xlim(-.52, 2.52)
        left.legend(loc="lower center", bbox_to_anchor=(.50, 1.025), ncol=2,
                    frameon=False, handlelength=1.0, handletextpad=.30,
                    columnspacing=.8, borderpad=0, fontsize=7.1)
        bars = right.bar([0, 1], feedback, .44, color="#697b86")
        right.bar_label(bars, padding=1, fontsize=7.1)
        right.set_xticks([0, 1], ["Easier\nrule edit", "Learning &\nflexibility"])
        right.set_xlim(-.52, 1.52)
        for ax, title in [(left, "(a) Task completion"), (right, "(b) WAFFLE feedback")]:
            ax.set_title(title, y=1.32, fontsize=7.3, fontweight="bold", pad=0)
        fig.savefig(ROOT / "figures/user-study-outcomes.pdf",
                    metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


if __name__ == "__main__":
    plot()
