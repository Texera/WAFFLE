"""Native Texera loop versus explicit-body-copy experiment."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import uuid


def check_rows(expected, actual):
    assert len(expected) == len(actual), (len(expected), len(actual))
    def key(row): return json.dumps(row, sort_keys=True)
    expected = sorted(expected, key=lambda r: r['K'])
    actual = sorted(actual, key=lambda r: r['K'])
    for e, a in zip(expected, actual):
        assert a.keys() == e.keys()
        for name in e:
            assert math.isclose(float(e[name]), float(a[name]), rel_tol=1e-9, abs_tol=1e-9), (e, a)


def write_points(path, count):
    if count < 12: raise ValueError('At least twelve points required')
    rng = random.Random(20261114)
    centers = [(0, 0), (8, 8), (0, 8), (8, 0)]
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['x', 'y'])
        for i in range(count):
            x, y = centers[i % len(centers)]
            w.writerow([format(x + rng.gauss(0, .8), '.12g'), format(y + rng.gauss(0, .8), '.12g')])


def graph(path, iterations, strategy):
    if iterations < 1: raise ValueError('positive iteration count required')
    if strategy not in ('loop', 'copies'): raise ValueError(strategy)
    nodes, links = [], []
    def port(kind, multi=False):
        return dict(portID=kind+'-0', displayName='', isDynamicPort=False,
                    allowMultiInputs=multi, disallowMultiInputs=not multi, dependencies=[])
    def node(label, kind, properties, source=False, multi=False):
        ident = kind+'-operator-'+str(uuid.uuid5(uuid.NAMESPACE_URL, 'loop-execution/'+label))
        nodes.append(dict(operatorID=ident, operatorType=kind, operatorVersion='N/A',
                          operatorProperties=properties, inputPorts=[] if source else [port('input',multi)],
                          outputPorts=[port('output')], customDisplayName=label,
                          dynamicInputPorts=False, dynamicOutputPorts=False, isDisabled=False,
                          showAdvanced=False, viewResult=label=='Results'))
        return ident
    def edge(a,b): links.append(dict(linkID='link-'+str(len(links)),
                                     source=dict(operatorID=a,portID='output-0'),
                                     target=dict(operatorID=b,portID='input-0')))
    def props(code,fields,source=False):
        p=dict(code=code,workers=1,defaultEnv=True,envName='')
        p['columns' if source else 'outputColumns']=[dict(attributeName=n,attributeType=t) for n,t in fields]
        if not source: p['retainInputColumns']=False
        return p
    source_code=f'from pytexera import *\nimport pandas as pd\nclass Points(UDFSourceOperator):\n    def produce(self):\n        yield pd.read_csv({path.as_posix()!r})\n'
    source=node('Points','PythonUDFSourceV2',props(source_code,[('x','double'),('y','double')],True),True)
    def body(k):
        return f'''from pytexera import *
import pandas as pd
from sklearn.cluster import KMeans
from threadpoolctl import threadpool_limits
class Cluster(UDFTableOperator):
    k = {k!r}
    def process_state(self, state, port):
        if 'K' in state:
            self.k = int(state['K'])
        return state
    def process_table(self, table, port):
        if self.k is None:
            raise ValueError('K did not arrive before the input table')
        with threadpool_limits(limits=1):
            model = KMeans(n_clusters=self.k, n_init=10, random_state=0, algorithm='lloyd').fit(table[['x','y']].to_numpy())
        yield pd.DataFrame([{{'K': self.k, 'score': -float(model.inertia_)}}])
'''
    outputs=[]
    if strategy=='loop':
        start=node('Loop Start','LoopStart',dict(initialization='K = 2',output='D'))
        cluster=node('Cluster','PythonUDFV2',props(body(None),[('K','integer'),('score','double')]))
        end=node('Loop End','LoopEnd',dict(update='K += 1',condition=f'K <= {iterations+1}'))
        edge(source,start);edge(start,cluster);edge(cluster,end);outputs=[end]
    else:
        for k in range(2,iterations+2):
            cluster=node('Cluster '+str(k),'PythonUDFV2',props(body(k),[('K','integer'),('score','double')]))
            edge(source,cluster);outputs.append(cluster)
    collector=node('Results','PythonUDFV2',props('from pytexera import *\nclass Collect(UDFOperatorV2):\n    def process_tuple(self, row, port):\n        yield row\n',[('K','integer'),('score','double')]),multi=True)
    for x in outputs:edge(x,collector)
    return dict(operators=nodes,links=links,operatorPositions={n['operatorID']:dict(x=i*180,y=100) for i,n in enumerate(nodes)},commentBoxes=[],settings=dict(dataTransferBatchSize=400,executionMode='MATERIALIZED'))


def prepare(root, counts, iterations, pairs):
    import pandas as pd
    from sklearn.cluster import KMeans
    from threadpoolctl import threadpool_limits
    root=root.resolve();root.mkdir(parents=True,exist_ok=False)
    runs=[];files={}
    for count in counts:
        data=root/f'points-{count}.csv';write_points(data,count)
        points=pd.read_csv(data).to_numpy()
        expected={}
        with threadpool_limits(limits=1):
            for k in range(2,max(iterations)+2):
                expected[k]=dict(K=k,score=-float(KMeans(n_clusters=k,n_init=10,random_state=0,algorithm='lloyd').fit(points).inertia_))
        for n in iterations:
            paths={}
            for strategy in ['loop','copies']:
                p=root/f'n{count}-i{n}-{strategy}.json'
                p.write_text(json.dumps(graph(data,n,strategy),indent=2)+'\n',encoding='utf-8');paths[strategy]=p.name
            for pair in range(-1,pairs):
                order=['loop','copies'] if pair%2==0 else ['copies','loop']
                for strategy in order:
                    runs.append(dict(case=f'n{count}-i{n}',strategy=strategy,pair=pair,warmup=pair<0,
                                     workflow=paths[strategy],fields=['K','score'],
                                     expected=[expected[k] for k in range(2,n+2)]))
    for p in root.iterdir():files[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    manifest=dict(runs=runs,input_hashes=files,seed=20261114,counts=counts,iterations=iterations,pairs=pairs,
                  max_concurrent_regions=1,workers_per_operator=1,execution_mode='MATERIALIZED',
                  timing='native coordinator and workers through result retrieval; compilation excluded',
                  baseline='one explicit body copy per K; branches scheduled sequentially; K order may differ')
    (root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(root,len(runs),'native executions planned')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path)
    p.add_argument('--counts',type=int,nargs='+',default=[200,2000])
    p.add_argument('--iterations',type=int,nargs='+',default=[1,4,8])
    p.add_argument('--pairs',type=int,default=5)
    a=p.parse_args();prepare(a.output,a.counts,a.iterations,a.pairs)
