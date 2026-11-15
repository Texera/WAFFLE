"""Rebuild the paper's X/Y planning-time figure from all saved measured runs.

Run: python experiments/xy_planning/plot.py
Requires matplotlib. No benchmark or external service is invoked.
"""
from pathlib import Path
import csv
import json
from statistics import median

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CASES = [(1, 1, 12, 7), (2, 2, 20, 11), (3, 3, 28, 15),
         (4, 4, 36, 19), (1, 4, 24, 13), (4, 1, 24, 13)]


def summarize():
    with (HERE / 'measurements.csv').open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 3600
    seen = set()
    for row in rows:
        key = (row['case'], int(row['fork']), int(row['repetition']), row['strategy'])
        assert key not in seen, key
        seen.add(key)
        assert key[1] in range(3) and key[2] in range(100) and key[3] in ('X', 'Y')
        assert int(row['total_ns']) == sum(int(row[k]) for k in
                                         ('decomposition_ns', 'search_ns', 'composition_ns'))
    output = []
    for inside, outside, operators, optimum in CASES:
        name = f'inside-{inside}-outside-{outside}'
        case = {'case': name, 'inside': inside, 'outside': outside, 'operators': operators,
                'minimum_estimated_cost': optimum}
        for strategy in ('X', 'Y'):
            selected = [r for r in rows if r['case'] == name and r['strategy'] == strategy]
            assert len(selected) == 300
            assert all(float(r['cost']) == optimum for r in selected)
            per_jvm = []
            for fork in range(3):
                times = [int(r['total_ns']) / 1e6 for r in selected if int(r['fork']) == fork]
                assert len(times) == 100
                per_jvm.append(median(times))
            value = median(int(r['total_ns']) / 1e6 for r in selected)
            assert min(per_jvm) <= value <= max(per_jvm)
            states = sorted({int(r['search_states']) for r in selected})
            assert len(states) == 1
            case[strategy] = {'pooled_median_ms': value, 'jvm_medians_ms': per_jvm,
                              'jvm_median_min_ms': min(per_jvm),
                              'jvm_median_max_ms': max(per_jvm), 'search_states': states[0]}
        output.append(case)
    return output


def main():
    summary = summarize()
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    plt.rcParams.update({'font.family': 'DejaVu Serif', 'font.size': 8,
                         'pdf.fonttype': 42, 'ps.fonttype': 42})
    fig, ax = plt.subplots(figsize=(3.35, 2.45), layout='constrained')
    for strategy, offset, color, marker, label in (
            ('X', -0.13, '#1761A0', 'o', 'X: global'),
            ('Y', 0.13, '#B34E00', 's', 'Y: modular')):
        values = [r[strategy]['pooled_median_ms'] for r in summary]
        lower = [v-r[strategy]['jvm_median_min_ms'] for v, r in zip(values, summary)]
        upper = [r[strategy]['jvm_median_max_ms']-v for v, r in zip(values, summary)]
        ax.errorbar([i+offset for i in range(len(summary))], values,
                    yerr=[lower, upper], fmt=marker, linestyle='none', color=color,
                    markersize=4.5, elinewidth=1, capsize=2.5, label=label)
    ax.set_yscale('log')
    ax.set_ylim(2, 1000)
    ax.set_xlim(-0.5, 5.5)
    ax.yaxis.set_major_locator(FixedLocator([3, 10, 30, 100, 300, 1000]))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f'{value:g}'))
    ax.yaxis.set_minor_locator(NullLocator())
    ax.set_ylabel('Planning time (ms, log scale)')
    ax.set_xticks(range(len(summary)),
                  [f"{r['inside']} / {r['outside']}\n{r['operators']} ops" for r in summary])
    ax.tick_params(axis='x', labelsize=7, length=0, pad=5)
    ax.set_xlabel('Groups inside / outside the loop', labelpad=5)
    ax.grid(axis='y', linewidth=0.5, color='#d4d4d4')
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
    ax.legend(loc='upper left', frameon=False, fontsize=7.5)
    destination = ROOT / 'figures/xy-planning-time.pdf'
    destination.parent.mkdir(exist_ok=True)
    fig.savefig(destination, metadata={'CreationDate': None, 'ModDate': None})
    plt.close(fig)
    print(destination)
    print('3600 measured plans; all six cases; no samples excluded')
    for r in summary:
        print(f"{r['case']}: X={r['X']['pooled_median_ms']:.6f} ms, "
              f"Y={r['Y']['pooled_median_ms']:.6f} ms; cost={r['minimum_estimated_cost']}")


if __name__ == '__main__':
    main()
