"""Instrument eight prespecified official workflows, with bounded iteration counts."""
import argparse, copy, hashlib, json, shutil
from pathlib import Path
import xml.etree.ElementTree as E

NS='http://www.knime.org/2008/09/XMLConfig'
E.register_namespace('',NS)
def config(e,key):return e.find(f'{{{NS}}}config[@key="{key}"]')
def entry(e,key):return e.find(f'{{{NS}}}entry[@key="{key}"]')
def setval(e,key,value):
    x=entry(e,key);assert x is not None,key
    x.set('value',str(value));x.attrib.pop('isnull',None)
def write(tree,path):tree.write(path,encoding='utf-8',xml_declaration=True)

def prepare(source,out):
    out=out.resolve();out.mkdir(parents=True,exist_ok=False)
    selection=json.loads((source/'selection.json').read_text())
    template=next((source/'originals/05_Write_each_row_in_one_file').rglob('workflow.knime'))
    tw=E.parse(template);tn=config(tw.getroot(),'nodes')
    writer=next(n for n in tn if 'CSV Writer' in entry(n,'node_settings_file').get('value'))
    writer_settings=E.parse(template.parent/entry(writer,'node_settings_file').get('value'))
    ends={9:4,10:10,11:16,12:16,13:10,14:16,15:8,16:8}
    adjustments={10:'loops: 1000 to 5',12:'loop table: first 5 of 38 rows',13:'stop iteration: 2000 to 4',14:'interval step: 0.01 to 0.25',15:'loops: 40 to 5',16:'loops: 1000 to 5'}
    records=[]
    for item in selection['items']:
        name=item['path'].split('/')[-1];num=int(name[:2]);original=next((source/'originals'/name).rglob('workflow.knime'))
        folder=out/f'knime-{num:02}'
        shutil.copytree(original.parent,folder)
        wf=E.parse(folder/'workflow.knime');root=wf.getroot();nodes=config(root,'nodes');links=config(root,'connections')
        for node in nodes:
            filename=folder/entry(node,'node_settings_file').get('value');t=E.parse(filename);model=config(t.getroot(),'model')
            factory=entry(t.getroot(),'factory').get('value')
            if num in (10,15,16) and factory.endswith('LoopStartCountNodeFactory'):setval(model,'loops',5)
            if num==13 and factory.endswith('LoopEndConditionNodeFactory'):setval(model,'value',4)
            if num==14 and factory.endswith('LoopStartIntervalNodeFactory'):setval(model,'step',.25)
            if num==12 and factory.endswith('TableCreator2NodeFactory'):
                for key in ('rowIndices','columnIndices','values'):
                    c=config(model,key);setval(c,'array-size',5)
                    for x in list(c):
                        if x.get('key').isdigit() and int(x.get('key'))>=5:c.remove(x)
            write(t,filename)
        exports=[(ends[num],1,'results.csv')]
        # Capture actual fresh source outputs as the shared inputs to the translation.
        exports += [(1,1,'input.csv')] if num in (9,10,12,13,15,16) else [(12,1,'input.csv')]
        if num==12:exports.append((12,1,'points.csv'))
        for offset,(source_id,source_port,filename) in enumerate(exports):
            nid=100+offset;sub=f'Evidence {nid}';(folder/sub).mkdir()
            n=copy.deepcopy(writer);n.set('key',f'node_{nid}');setval(n,'id',nid);setval(n,'node_settings_file',sub+'/settings.xml');nodes.append(n)
            s=copy.deepcopy(writer_settings);sr=s.getroot();m=config(sr,'model')
            setval(m,'filename',(out/f'{num:02}-{filename}').as_posix());setval(m,'writeColHeader','true');setval(m,'writeRowHeader','true')
            variables=config(sr,'variables')
            for child in list(variables):variables.remove(child)
            write(s,folder/sub/'settings.xml')
            c=E.SubElement(links,f'{{{NS}}}config',key=f'connection_evidence_{nid}')
            for k,v in [('sourceID',source_id),('destID',nid),('sourcePort',source_port),('destPort',1)]:E.SubElement(c,f'{{{NS}}}entry',key=k,type='xint',value=str(v))
        write(wf,folder/'workflow.knime')
        archive=source/(name+'.knwf')
        records.append(dict(case=num,name=name,hub_id=item['id'],version=item['itemVersionId'],source_url='https://kni.me/w/'+item['id'][1:],
                            archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),adjustment=adjustments.get(num,'none'),workflow=folder.name,
                            expected_exports=[f'{num:02}-{f}' for _,_,f in exports]))
    (out/'selection.json').write_text(json.dumps(dict(criterion=selection['criterion'],bounded_setting='shortened examples run five iterations; chunk and group examples retain original settings; same changes in both systems',cases=records),indent=2))
    print(out)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();prepare(a.source,a.output)
