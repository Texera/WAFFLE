"""WAFFLE source, prepared bodies and ordinary loop boundary operators."""
from pathlib import Path
import uuid

def graph(data,evidence,task,target):
    nodes=[];links=[];files=task.startswith('files');starter=task.endswith('starter')
    def port(kind):return dict(portID=kind+'-0',displayName='',isDynamicPort=False,allowMultiInputs=False,disallowMultiInputs=True,dependencies=[])
    def node(label,kind,props,source=False):
        ident=kind+'-operator-'+str(uuid.uuid5(uuid.NAMESPACE_URL,'study/'+label))
        nodes.append(dict(operatorID=ident,operatorType=kind,operatorVersion='N/A',operatorProperties=props,inputPorts=[] if source else [port('input')],outputPorts=[port('output')],customDisplayName=label,dynamicInputPorts=False,dynamicOutputPorts=False,isDisabled=False,showAdvanced=False,viewResult=label=='Results'))
        if len(nodes)>1:links.append(dict(linkID='link-'+str(len(links)),source=dict(operatorID=nodes[-2]['operatorID'],portID='output-0'),target=dict(operatorID=ident,portID='input-0')))
    def props(code,fields,source=False):
        p=dict(code=code,workers=1,defaultEnv=True,envName='')
        p['columns' if source else 'outputColumns']=[dict(attributeName=n,attributeType=t) for n,t in fields]
        if not source:p['retainInputColumns']=False
        return p
    fields=[('filename','string'),('mean','double')] if files else [('K','integer'),('score','double')]
    source_fields=[('index','integer'),('count','integer')] if files else [('K','integer')]
    source='from pytexera import *\nfrom pathlib import Path\nclass Inputs(UDFSourceOperator):\n    def produce(self):\n'
    for n in ['visits.csv','results.csv']:source+='        Path('+repr((evidence/n).as_posix())+').write_text("",encoding="utf-8")\n'
    if files:source+='        yield [{"index":0,"count":len(list(Path('+repr((data/'sales').as_posix())+').glob("*.csv")))}]\n'
    else:source+='        yield [{"K":2}]\n'
    node('Inputs - prepared','PythonUDFSourceV2',props(source,source_fields,True),True)
    if not starter:
        node('Loop Start','LoopStart',dict(initialization='i = 0\nn = 0' if files else 'K = 2',output='n = int(D["count"].iloc[0])\nD.assign(index=i)' if files else 'D.assign(K=K)'))
    code='from pytexera import *\nfrom pathlib import Path\nimport csv\n'
    if not files:code+=Path(__file__).with_name('kmeans_body.py').read_text()+'\n'
    code+='DATA = Path('+repr(data.as_posix())+')\nAUDIT = Path('+repr((evidence/'visits.csv').as_posix())+')\n'
    code+='''class Prepared(UDFOperatorV2):
    def compute(self, key):
        if getattr(self, '_key', None) == key:
            return self._row
'''
    if files:
        code+='''        path = sorted((DATA / 'sales').glob('*.csv'))[key]
        with path.open(newline='', encoding='utf-8') as f:
            values = [float(r['price']) for r in csv.DictReader(f)]
        row = {'filename': path.name, 'mean': sum(values)/len(values)}
'''
    else:
        code+='''        with (DATA / 'points.csv').open(newline='',encoding='utf-8') as f:
            points = [(float(r['x']),float(r['y'])) for r in csv.DictReader(f)]
        row = {'K': key, 'score': cluster_score(points,key)}
'''
    code+='''        self._key, self._row = key, row
        with AUDIT.open('a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(list(row.values()))
        return row
    def process_state(self, state, port):
        state = State(state)
'''
    if files:code+='        return state\n'
    else:code+='        state["score"] = self.compute(int(state["K"]))["score"]\n        return state\n'
    code+='    def process_tuple(self, row, port):\n        yield self.compute(int(row['+repr('index' if files else 'K')+']))\n'
    node('Read file and mean - prepared' if files else 'K-means and score - prepared','PythonUDFV2',props(code,fields))
    if not starter:
        condition='i < n' if files else ('K <= 4 and score < '+repr(target) if task=='adapt' else 'K <= 4')
        node('Loop End','LoopEnd',dict(update='i += 1' if files else 'K += 1',condition=condition))
    recorder='from pytexera import *\nimport csv\nclass Results(UDFOperatorV2):\n    def process_tuple(self,row,port):\n        with open('+repr((evidence/'results.csv').as_posix())+',"a",newline="",encoding="utf-8") as f:\n            csv.writer(f).writerow(['+','.join('row['+repr(n)+']' for n,_ in fields)+'])\n        yield row\n'
    node('Results','PythonUDFV2',props(recorder,fields))
    return dict(operators=nodes,links=links,operatorPositions={n['operatorID']:dict(x=60+i*220,y=100) for i,n in enumerate(nodes)},commentBoxes=[],settings=dict(dataTransferBatchSize=400,executionMode='MATERIALIZED'))
