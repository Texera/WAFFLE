"""Show the observed first tuple and filter outcome for eight native workers."""
import json
from pathlib import Path

import matplotlib.pyplot as plt
from verify_binding import RESULTS, check


def observations(results=RESULTS):
    check(results)
    records = [json.loads(line) for line in (results / "native.jsonl").read_text().splitlines()]
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
    scoped_results = RESULTS.parent / "binding_scoped_results" / "standard"
    if observations(scoped_results) != observations_by_worker:
        raise ValueError("Figure 24 requires matching eight-worker profiles on both runtimes")
    workers = sorted(range(8), key=lambda w: observations_by_worker[w, 2][0])
    with plt.rc_context({"font.family": "DejaVu Serif", "font.size": 8, "pdf.fonttype": 42}):
        fig, ax = plt.subplots(figsize=(3.39, 1.52))
        fig.subplots_adjust(left=0.15, right=0.98, bottom=0.30, top=0.73)
        ax.bar(range(len(workers)), [observations_by_worker[w, 2][0] for w in workers],
               width=0.60, color="#9abdc9", edgecolor="#2a5364", linewidth=0.6)
        for threshold, style in ((2, "--"), (3, ":")):
            ax.axhline(threshold, linestyle=style, color="#20272b", linewidth=1.1,
                       label=f"K = {threshold}")
        ax.set(ylim=(0, 7.5), yticks=(0, 2, 3, 5, 7), xlabel="Worker", ylabel="First input x")
        ax.set_xticks(range(len(workers)), workers)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(length=2, pad=2)
        fig.legend(*ax.get_legend_handles_labels(), loc="upper center", ncol=2,
                   frameon=False, fontsize=7.5)
        fig.savefig(output, metadata={"CreationDate": None, "ModDate": None})
        plt.close(fig)


if __name__ == "__main__":
    draw(Path(__file__).resolve().parents[2] / "figures" / "first-tuple-outcomes.pdf")
