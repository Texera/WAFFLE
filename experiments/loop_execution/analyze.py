"""Validate all runs before summarizing or plotting the execution comparison."""
import argparse,csv,hashlib,json,statistics
from pathlib import Path
from experiment import check_rows

def analyze(root,out):
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    assert (root/'exit-code.txt').read_text().strip()=='0','native suite did not pass'
    for name,sha in manifest['input_hashes'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
    samples=[json.loads(line) for line in (root/'native.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(samples)==len(manifest['runs'])
    records=[]
    for i,(s,r) in enumerate(zip(samples,manifest['runs'])):
        assert s['sample']==i
        for k in ('case','strategy','pair','warmup'):assert s[k]==r[k],(i,k)
        check_rows(r['expected'],s['rows'])
        records.append({k:s[k] for k in ('sample','case','strategy','pair','warmup','execution_ns','compilation_ns')})
    groups={}
    for s in samples:
        if not s['warmup']:groups.setdefault((s['case'],s['strategy']),[]).append(s['execution_ns']/1e9)
    summary=[]
    for (case,strategy),values in groups.items():
        assert len(values)==manifest['pairs']
        n,i=map(int,case[1:].split('-i'))
        summary.append(dict(case=case,points=n,iterations=i,strategy=strategy,runs=len(values),
                            median_s=statistics.median(values),min_s=min(values),max_s=max(values)))
    out.mkdir(parents=True,exist_ok=True)
    with (out/'measurements.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    result=dict(raw_sha256=hashlib.sha256((root/'native.jsonl').read_bytes()).hexdigest(),
                completed_runs=len(samples),measured_runs=sum(not s['warmup'] for s in samples),all_outputs_match=True,
                timing=manifest['timing'],summary=summary)
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2));return result

def plot(summary, measurements, output, additional=None):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    with measurements.open(encoding='utf-8') as source:
        runs = [r for r in csv.DictReader(source) if r['warmup'] == 'False']
    assert len(runs) == summary['measured_runs']
    if additional is not None:
        extra = json.loads((additional / 'summary.json').read_text())
        with (additional / 'measurements.csv').open() as source:
            extra_runs = [r for r in csv.DictReader(source) if r['warmup'] == 'False']
        assert len(extra_runs) == extra['measured_runs']
        assert not {r['case'] for r in runs} & {r['case'] for r in extra_runs}
        runs.extend(extra_runs)
        summary = dict(summary, summary=summary['summary'] + extra['summary'])
    sizes = sorted({r['points'] for r in summary['summary']})
    strategies = [('loop', -0.20, '#86aebf', 'Loop'),
                  ('copies', 0.20, 'white', 'Explicit copies')]
    plt.rcParams.update({'font.size': 8, 'pdf.fonttype': 42})
    widths = [len({r['iterations'] for r in summary['summary'] if r['points'] == n}) + 0.5 for n in sizes]
    fig, axes = plt.subplots(1, len(sizes), figsize=(3.4, 1.95), sharey=True, squeeze=False,
                             gridspec_kw={'width_ratios': widths})
    for ax, size in zip(axes[0], sizes):
        settings = sorted({r['iterations'] for r in summary['summary'] if r['points'] == size})
        for x, k_count in enumerate(settings):
            for strategy, offset, face, _ in strategies:
                group = sorted((r for r in runs if r['case'] == f'n{size}-i{k_count}'
                                and r['strategy'] == strategy), key=lambda r: int(r['pair']))
                times = [int(r['execution_ns']) / 1e9 for r in group]
                if len(times) != 5:
                    raise ValueError(f"Expected five execution times for {size}, {k_count}, {strategy}")
                ax.boxplot(times, positions=[x + offset], widths=0.31, whis=(0, 100),
                           manage_ticks=False, patch_artist=True, showfliers=False,
                           boxprops=dict(facecolor=face, edgecolor='black', linewidth=0.8),
                           medianprops=dict(color='black', linewidth=1.1),
                           whiskerprops=dict(color='black', linewidth=0.7),
                           capprops=dict(color='black', linewidth=0.7))
        ax.set(xlim=(-0.5, len(settings) - 0.5), xticks=range(len(settings)),
               xticklabels=settings)
        ax.set_title(f'{size:,} points', fontsize=8)
        ax.grid(axis='y', alpha=0.2)
    axes[0, 0].set_ylim(0, max(r['max_s'] for r in summary['summary']) * 1.08)
    axes[0, 0].set_ylabel('Workflow time (s)')
    handles = [Patch(facecolor=face, edgecolor='black', label=label)
               for _, _, face, label in strategies]
    fig.legend(handles=handles, loc='upper center', ncol=2, frameon=False, fontsize=7)
    fig.text(0.56, 0.015, 'Number of K values', ha='center')
    fig.tight_layout(rect=(0, 0.075, 1, 0.87), pad=0.45, w_pad=0.6)
    fig.savefig(output, bbox_inches='tight', metadata={'CreationDate': None})
    plt.close(fig)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('output',type=Path);p.add_argument('--plot',type=Path)
    p.add_argument('--additional-summary',type=Path,help='Directory containing the verified supplemental summary and measurements')
    a=p.parse_args();result=analyze(a.package,a.output)
    if a.plot:plot(result,a.output/'measurements.csv',a.plot,a.additional_summary)
