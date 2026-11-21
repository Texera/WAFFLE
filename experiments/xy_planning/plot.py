"""Rebuild the paper's X/Y planning-time figure from all saved measured runs.

Run: python experiments/xy_planning/plot.py
Requires matplotlib. No benchmark or external service is invoked.
"""
from pathlib import Path
import csv
import json
from statistics import median


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
    from scale.charts import draw
    draw("pooled_median_ms", ROOT / "figures/xy-planning-time.pdf")
    draw("search_states", ROOT / "figures/xy-search-states.pdf")
    for r in summary:
        print(f"{r['case']}: X={r['X']['pooled_median_ms']:.6f} ms, "
              f"Y={r['Y']['pooled_median_ms']:.6f} ms; cost={r['minimum_estimated_cost']}")


if __name__ == '__main__':
    main()
