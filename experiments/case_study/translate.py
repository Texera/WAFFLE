"""Manual translations of the prespecified KNIME examples to native loop operators.

CSV exports are fresh KNIME inputs, never cached outputs. Expected outputs are
used only by the separate checker, not embedded in a translated computation.
"""
import argparse,csv,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'loop_execution'))
from experiment import graph

CASES={9:'chunks',10:'fixed count',11:'groups',12:'row variables',13:'condition',14:'interval',15:'column collection',16:'variable collection'}

def make_graph(root,num):
    source_file=root/f'{num:02}-input.csv'
    if num in (9,10,13,15,16):fields=[('Text','string')]
    elif num==12:fields=[('Number','integer')]
    else:fields=[('X','double'),('Y','double'),('Class','string')]
    g=graph(source_file,5,'loop');source,start,body,end,collector=g['operators']
    source['operatorProperties']['columns']=[dict(attributeName=n,attributeType=t) for n,t in fields]
    dtype={n:'str' if t=='string' else ('int' if t=='integer' else 'float') for n,t in fields}
    source['operatorProperties']['code']='''from pytexera import *
import pandas as pd
class Input(UDFSourceOperator):
    def produce(self):
        yield pd.read_csv(PATH, dtype=DTYPE).drop(columns=['row ID'])
'''.replace('PATH',repr(source_file.as_posix())).replace('DTYPE',repr(dtype))
    init='i = 0';output='D';condition='i < 5'
    if num==9:output='D.iloc[3*i:3*(i+1)]';condition='i < (len(D)+2)//3'
    if num==11:
        init="i = 0\ngroups = sorted(D['Class'].unique().tolist())"
        output="group = groups[i]\nD[D['Class'] == group]";condition='i < len(groups)'
    if num==12:output="Number = int(D.iloc[i]['Number'])\nD.iloc[[i]]";condition='i < len(D)'
    if num==14:output='value = i * 0.25\nD'
    start['operatorProperties']=dict(initialization=init,output=output)
    end['operatorProperties']=dict(update='i += 1',condition=condition)
    common='''from pytexera import *
import pandas as pd
import json
import math
class Body(UDFTableOperator):
    def process_state(self, state, port):
        self.values = dict(state)
        return state
    def process_table(self, table, port):
        i = int(self.values['i'])
'''
    snippets={
        9:"rows = [{'value': str(v), 'count': int(n), 'Iteration': i} for v,n in table['Text'].value_counts(sort=False).items()]",
        10:"rows = [dict(r, **{'Counting Column': i, 'Iteration': i}) for r in table.to_dict('records')]",
        12:"points = pd.read_csv(POINTS).drop(columns=['row ID'])\nrows = [dict(r, **{'Appended Number': int(self.values['Number'])}) for r in points.to_dict('records')]".replace('POINTS',repr((root/'12-points.csv').as_posix())),
        13:"rows = [dict(r, **{'Counting Column': i, 'Iteration': i}) for r in table.to_dict('records')]",
        14:"v = float(self.values['value'])\nrows = []\nfor r in table.to_dict('records'):\n    r['X'] = float(r['X']) * v\n    r['Y'] = -r['X'] * v\n    rows.append(r)",
        15:"rows = [{'iteration': i, 'Counting Column': i}]",
        16:"rows = [{'currentIteration': i}]",
    }
    if num==11:
        snippets[11]='''rows = []
for name in table.columns:
    s = table[name]
    numeric = pd.api.types.is_numeric_dtype(s)
    if not numeric:
        continue
    row = {'Column': name, 'Min': float(s.min()) if numeric else None, 'Max': float(s.max()) if numeric else None,
           'Mean': float(s.mean()) if numeric else None, 'Std. deviation': float(s.std(ddof=1)) if numeric else None,
           'Variance': float(s.var(ddof=1)) if numeric else None, 'Skewness': float(s.skew()) if numeric else None,
           'Kurtosis': float(s.kurt()) if numeric else None, 'Overall sum': float(s.sum()) if numeric else None,
           'No. missings': int(s.isna().sum()), 'No. NaNs': 0, 'No. +\u221es': 0, 'No. -\u221es': 0,
           'Median': None, 'Row count': len(s), 'Class': str(self.values['group'])}
    rows.append(row)'''
    code=common+'\n'.join('        '+s for s in snippets[num].splitlines())+'\n'
    code+="        rows = [{k: ({'__float__': 'NaN'} if isinstance(v, float) and math.isnan(v) else v) for k,v in r.items()} for r in rows]\n"
    code+="        yield pd.DataFrame([{'payload': json.dumps(r, sort_keys=True, allow_nan=False)} for r in rows])\n"
    cols=[dict(attributeName='payload',attributeType='string')]
    body['operatorProperties'].update(code=code,outputColumns=cols)
    if num==15:
        code='''from pytexera import *
import pandas as pd
import json
class Collect(UDFTableOperator):
    def process_table(self, table, port):
        rows = sorted([json.loads(p) for p in table['payload']], key=lambda r:r['iteration'])
        wide = {('Counting Column' if r['iteration']==0 else 'Counting Column (Iter #'+str(r['iteration'])+')'):r['Counting Column'] for r in rows}
        yield pd.DataFrame([{'payload':json.dumps(wide, sort_keys=True)}])
'''
    else:code='from pytexera import *\nclass Collect(UDFOperatorV2):\n    def process_tuple(self, row, port):\n        yield row\n'
    collector['operatorProperties'].update(code=code,outputColumns=cols)
    return g

def prepare(root):
    records=[]
    for n,pattern in CASES.items():
        g=make_graph(root,n);name=f'{n:02}-texera.json'
        path=root/name
        if path.exists():raise ValueError(f'Existing translation: {path}')
        path.write_text(json.dumps(g,indent=2),encoding='utf-8')
        records.append(dict(case=str(n),strategy=pattern,workflow=name,fields=['payload'],pair=0,warmup=False))
    evidence = sorted(root.glob('*-input.csv')) + sorted(root.glob('*-points.csv')) + sorted(root.glob('*-texera.json')) + sorted(root.glob('*-results.csv'))
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence}
    (root/'manifest.json').write_text(json.dumps(dict(runs=records, input_hashes=hashes),indent=2),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package',type=Path);a=p.parse_args();prepare(a.package.resolve())
