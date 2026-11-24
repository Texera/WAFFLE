"""Show the observed first tuple and filter outcome for eight native workers."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
from verify_binding import RESULTS, check


def observations():
    check(RESULTS)
    records = [json.loads(line) for line in (RESULTS / "native.jsonl").read_text().splitlines()]
    profiles = []
    for run in records:
        if run["workers"] != 8:
            continue
        outputs = {tuple(row) for row in run["rows"]}
        workers = {}
        for item in run["first_tuples"]:
            worker, x, k = item["worker"], item["first_x"], item["bound_K"]
            kept = (k, x) in outputs
            if kept != (x >= k):
                raise ValueError(f"First tuple disagrees with the bound filter for worker {worker}")
            workers[worker, k] = (x, kept)
        profiles.append(workers)
    if len(profiles) != 3 or any(profile != profiles[0] for profile in profiles):
        raise ValueError("Eight-worker repetitions have different first-tuple profiles")
    if any(profiles[0][w, 2][0] != profiles[0][w, 3][0] for w in range(8)):
        raise ValueError("First tuples changed between iterations")
    return profiles[0]


def draw(output):
    observations_by_worker = observations()
    workers = sorted(range(8), key=lambda w: observations_by_worker[w, 2][0])
    with plt.rc_context({"font.family": "DejaVu Serif", "font.size": 8, "pdf.fonttype": 42}):
        fig, ax = plt.subplots(figsize=(3.39, 1.42))
        fig.subplots_adjust(left=0.21, right=0.98, bottom=0.36, top=0.78)
        for i, worker in enumerate(workers):
            ax.vlines(i, 0, 1, color="#e0e3e5", lw=0.7, zorder=0)
            for y, k in enumerate((2, 3)):
                _, kept = observations_by_worker[worker, k]
                ax.plot(i, y, marker="o" if kept else "x", color="#195e7b" if kept else "#873f22",
                        markersize=5.3, markeredgewidth=1.2, linestyle="none")
        ax.set(xlim=(-0.45, 7.45), ylim=(1.4, -0.4))
        ax.set_yticks([0, 1], ["K = 2", "K = 3"])
        ax.set_xticks(range(8), [observations_by_worker[w, 2][0] for w in workers])
        ax.spines[:].set_visible(False)
        ax.tick_params(length=0, pad=2)
        upper = ax.secondary_xaxis("top")
        upper.set_xticks(range(8), workers)
        upper.spines[:].set_visible(False)
        upper.tick_params(length=0, pad=2)
        ax.text(-0.06, 1.12, "Worker", ha="right", va="center", transform=ax.transAxes)
        ax.text(-0.06, -0.14, "First x", ha="right", va="center", transform=ax.transAxes)
        for marker, color, label in (("o", "#195e7b", "Passed"), ("x", "#873f22", "Filtered out")):
            ax.plot([], [], marker=marker, color=color, markersize=5, linestyle="none", label=label)
        fig.legend(loc="lower center", ncol=2, frameon=False, fontsize=7.6, handlelength=1, columnspacing=1.6)
        fig.savefig(output, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


if __name__ == "__main__":
    draw(Path(__file__).resolve().parents[2] / "figures" / "first-tuple-outcomes.pdf")
