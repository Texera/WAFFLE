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

def plot(summary,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size':8,'pdf.fonttype':42,'ps.fonttype':42})
    sizes=sorted({r['points'] for r in summary['summary']})
    fig,axes=plt.subplots(1,len(sizes),figsize=(3.35,1.85),sharey=True,squeeze=False)
    for ax,n in zip(axes[0],sizes):
        for strategy,style,marker in [('loop','-','o'),('copies','--','s')]:
            vals=sorted([r for r in summary['summary'] if r['points']==n and r['strategy']==strategy],key=lambda r:r['iterations'])
            med=[r['median_s'] for r in vals]
            ax.errorbar([r['iterations'] for r in vals],med,
                        yerr=[[r['median_s']-r['min_s'] for r in vals],[r['max_s']-r['median_s'] for r in vals]],
                        color='black',linestyle=style,marker=marker,markersize=3,linewidth=1,capsize=2,
                        markerfacecolor='black' if strategy=='loop' else 'white',label='Loop' if strategy=='loop' else 'Explicit copies')
        ax.set_title(f'{n:,} points',fontsize=8);ax.set_xticks([1,4,8]);ax.set_xlabel('Number of K values');ax.grid(axis='y',alpha=.2)
    axes[0,0].set_ylim(0,max(r['max_s'] for r in summary['summary'])*1.1)
    axes[0,0].set_ylabel('Workflow time (s)')
    handles,labels=axes[0,0].get_legend_handles_labels();fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.54,1.04),ncol=2,frameon=False,fontsize=7)
    fig.tight_layout(rect=(0,0,1,.9),pad=.4,w_pad=.5);fig.savefig(output,bbox_inches='tight');plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('output',type=Path);p.add_argument('--plot',type=Path)
    a=p.parse_args();result=analyze(a.package,a.output)
    if a.plot:plot(result,a.plot)
