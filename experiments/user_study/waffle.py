"""Study graphs using Texera readers, aggregation and sorting where available."""
from pathlib import Path
import uuid


def graph(data, evidence, task, target, short=False):
    nodes, links = [], []
    files, starter = task.startswith('files'), task.endswith('starter')

    def port(kind):
        return dict(portID=kind+'-0', displayName='', isDynamicPort=False,
                    allowMultiInputs=False, disallowMultiInputs=True, dependencies=[])

    def node(label, kind, props, source=False, control=False, connect=True):
        ident=kind+'-operator-'+str(uuid.uuid5(uuid.NAMESPACE_URL,'native-study/'+label))
        previous=nodes[-1]['operatorID'] if nodes else None
        nodes.append(dict(operatorID=ident, operatorType=kind, operatorVersion='N/A',
            operatorProperties=props, inputPorts=[] if source else [port('input')],
            outputPorts=[port('output')], customDisplayName=label, dynamicInputPorts=False,
            dynamicOutputPorts=False, isDisabled=False, showAdvanced=False, viewResult=label=='Results'))
        if previous and connect:
            links.append(dict(linkID='link-'+str(len(links)),
                source=dict(operatorID=previous,portID='output-0'),
                target=dict(operatorID=ident,portID='control-variables' if control else 'input-0')))

    def udf(code, fields, source=False):
        props=dict(code=code,workers=1,defaultEnv=True,envName='')
        props['columns' if source else 'outputColumns']=[dict(attributeName=n,attributeType=t) for n,t in fields]
        if not source:props['retainInputColumns']=False
        return props

    fields=[('filename','string'),('mean','double')] if files else [('K','integer'),('score','double')]
    audit=repr((evidence/'visits.csv').as_posix())
    if files:
        # The native dataset lister requires a deployed dataset service. This
        # prepared adapter only enumerates local paths; it never reads prices.
        code='''from pytexera import *
from pathlib import Path
class ListFiles(UDFSourceOperator):
    def produce(self):
'''+f'        for p in sorted(Path({(data/"sales").as_posix()!r}).glob("*.csv")):\n            yield {{"file":p.as_posix()}}\n'
        node('List files - prepared','PythonUDFSourceV2',udf(code,[('file','string')],True),True)
        if not starter:
            node('Loop Start','LoopStart',dict(initialization='i = 0',output='file = D.file[i]'))
        node('Read price file','FileScan',dict(fileName=(data/'sales/01-jan.csv').as_posix() if starter else '$file',
            attributeName='price',attributeType='double',encoding='UTF_8',extract=False,
            outputFileName=False,fileScanOffset=1),True,control=not starter,connect=not starter)
        node('Average price','Aggregate',dict(groupByKeys=[],aggregations=[{
            'aggFunction':'average','attribute':'price','result attribute':'mean'}]))
        code='''from pytexera import *
from pathlib import PurePosixPath
from urllib.parse import unquote, urlparse
import csv
class LabelAndAudit(UDFOperatorV2):
    def process_tuple(self,row,port):
'''+f'        filename=self.state["file"] if self.state is not None and "file" in self.state else {(data/"sales/01-jan.csv").as_posix()!r}\n'
        code+='''        result={'filename':PurePosixPath(unquote(urlparse(filename).path)).name,'mean':row['mean']}
'''+f'        with open({audit},"a",newline="",encoding="utf-8") as f:\n            csv.writer(f).writerow([result["filename"],result["mean"]])\n        yield result\n'
        node('Filename and audit - prepared','PythonUDFV2',udf(code,fields))
    else:
        node('Read points','CSVFileScan',dict(fileName=data.joinpath('points.csv').as_posix(),hasHeader=True,customDelimiter=',',fileEncoding='UTF_8'),True)
        if not starter or short:
            node('Loop Start','LoopStart',dict(initialization='K = 2',output='D'))
        # There is no built-in K-means descriptor in the tested Texera revision.
        # The prepared UDF accepts native-reader rows and only does clustering.
        code='from pytexera import *\nimport csv\n'+Path(__file__).with_name('kmeans_body.py').read_text()+'\n'
        code+='''class Cluster(UDFOperatorV2):
    def open(self):
        self.points=[]
        self.result=None
    def process_tuple(self,row,port):
        self.points.append((float(row['x']),float(row['y'])))
        yield None
    def result_row(self):
        if self.result is None:
            k=int(self.state['K']) if self.state is not None and 'K' in self.state else 2
            self.result={'K':k,'score':cluster_score(self.points,k)}
'''+f'            with open({audit},"a",newline="",encoding="utf-8") as f:\n                csv.writer(f).writerow([k,self.result["score"]])\n'
        code+='''        return self.result
    def produce_state_on_finish(self,port):
        row=self.result_row()
        if self.state is not None:
            state=State(self.state)
            state['score']=row['score']
            return state
    def on_finish(self,port):
        yield self.result_row()
'''
        node('K-means and score - prepared','PythonUDFV2',udf(code,fields))
    if not starter or (short and not files):
        condition='i < len(D)' if files else ('K <= 4 and score < '+repr(target) if task=='adapt' else 'K <= 4')
        if short and starter and not files:condition='False'
        node('Loop End','LoopEnd',dict(update='i += 1' if files else 'K += 1',condition=condition))
    node('Results','Sort',dict(attributes=[dict(attribute='filename' if files else 'K',sortPreference='ASC')]))
    return dict(operators=nodes,links=links,
        operatorPositions={n['operatorID']:dict(x=60+i*220,y=100) for i,n in enumerate(nodes)},
        commentBoxes=[],settings=dict(dataTransferBatchSize=400,executionMode='MATERIALIZED'))
