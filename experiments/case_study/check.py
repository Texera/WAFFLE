"""Compare full output multisets, with exact strings and a numeric tolerance."""
import argparse,csv,hashlib,json,math
from pathlib import Path

def equal(a,b):
    if a is None or b is None:return a is b
    if isinstance(a,(float,int)) and isinstance(b,(float,int)):
        return math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9)
    return type(a)==type(b) and a==b

def compare(expected,actual):
    assert len(expected)==len(actual),f'row count {len(actual)} != {len(expected)}'
    remaining=list(actual)
    for e in expected:
        for i,a in enumerate(remaining):
            if set(a)==set(e) and all(equal(e[k],a[k]) for k in e):
                remaining.pop(i);break
        else:raise AssertionError(f'No matching row: {e}; first remaining: {remaining[:1]}')

def expected_rows(root,num):
    rows=[]
    with (root/f'{num:02}-results.csv').open(encoding='utf-8-sig',newline='') as f:
        for raw in csv.DictReader(f):
            row={}
            for k,v in raw.items():
                if k=='row ID':continue
                if num==11 and k=='Histogram':continue
                if v=='':row[k]=None
                elif k in ('Text','Column') or (k=='Class' and num in (11,14)):row[k]=v
                elif v=='NaN':row[k]={'__float__':'NaN'}
                else:
                    try:row[k]=float(v)
                    except ValueError:row[k]=v
            if num==9:row['value']=raw['row ID'].rsplit('#',1)[0]
            rows.append(row)
    return rows

def check(root):
    assert (root/'exit-code.txt').read_text().strip()=='0','native suite did not pass'
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    for name,sha in manifest['input_hashes'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha,name
    samples=[json.loads(x) for x in (root/'native.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(samples)==len(manifest['runs'])
    for i,(sample,run) in enumerate(zip(samples,manifest['runs'])):
        assert sample['sample']==i and sample['case']==run['case']
    assert len({x['case'] for x in samples})==len(samples)
    by_case={int(x['case']):x for x in samples};out=[]
    for case in json.loads((root/'selection.json').read_text())['cases']:
        n=case['case'];status='unverified';reason=''
        try:
            knime=json.loads((root/f'{n:02}-knime-run.json').read_text())
            assert knime['exit_code']==0 and knime['exports_present'],'KNIME did not finish'
            assert n in by_case,'Texera produced no completed run'
            expected=expected_rows(root,n);actual=[json.loads(r['payload']) for r in by_case[n]['rows']]
            compare(expected,actual);status='match'
        except (AssertionError,FileNotFoundError) as e:reason=str(e)
        out.append(dict(case=n,status=status,reason=reason,
                        rows=len(by_case[n]['rows']) if n in by_case else None))
    result=dict(cases=out,tolerance=dict(relative=1e-9,absolute=1e-9),row_order='multiset',
                row_ids='ignored except Value Counter category keys in case09',
                presentation='case11 Histogram image cells, color metadata and interactive views excluded; all scalar result columns compared',
                undefined_statistics='NaN is encoded as {"__float__":"NaN"}, distinct from missing/null',
                matched=sum(x['status']=='match' for x in out),total=len(out))
    (root/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2));return int(result['matched']!=result['total'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package',type=Path);a=p.parse_args();raise SystemExit(check(a.package))
