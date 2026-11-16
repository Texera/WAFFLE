"""Native KNIME nodes; prepared bodies use the bundled Java Snippet node."""
from pathlib import Path
import json
import uuid
import xml.etree.ElementTree as E

NS='http://www.knime.org/2008/09/XMLConfig'; E.register_namespace('',NS)
def cfg(parent,key):return E.SubElement(parent,'{'+NS+'}config',key=key)
def entry(parent,key,value,kind=None):
    kind=kind or ('xboolean' if isinstance(value,bool) else 'xint' if isinstance(value,int) else 'xstring')
    return E.SubElement(parent,'{'+NS+'}entry',key=key,type=kind,value=(str(value).lower() if isinstance(value,bool) else str(value)).replace('\n','%%00010'))
def array(parent,key,values):
    x=cfg(parent,key);entry(x,'array-size',len(values))
    for i,v in enumerate(values):entry(x,str(i),v)
    return x
def write(path,tree):
    E.indent(tree,space='  ');E.ElementTree(tree).write(path,encoding='utf-8',xml_declaration=True)

def snippet(model,code,in_cols=(),out_cols=(),in_vars=(),out_vars=(),replace=()):
    entry(model,'scriptImports','import java.nio.file.*;\nimport java.nio.charset.StandardCharsets;\n')
    entry(model,'scriptFields','')
    entry(model,'scriptBody','try {\n'+code+'\n} catch(java.io.IOException e){throw new RuntimeException(e);}\n')
    for k in ('jarFiles','bundles'):array(model,k,[])
    for key,fields,col,out in [('inCols',in_cols,True,False),('outCols',out_cols,True,True),('inVars',in_vars,False,False),('outVars',out_vars,False,True)]:
        group=cfg(model,key);entry(group,'array-size',len(fields))
        for i,(name,var,typ) in enumerate(fields):
            f=cfg(group,str(i));entry(f,'Name',name);entry(f,'JavaName',var);entry(f,'JavaType','java.lang.'+typ)
            if col:
                cell=cfg(f,'Type');entry(cell,'cell_class','org.knime.core.data.def.'+{'Integer':'Int','Double':'Double','String':'String'}[typ]+'Cell');entry(cell,'is_null',False)
            else:entry(f,'Type',{'Integer':'INTEGER','Double':'DOUBLE','String':'STRING'}[typ])
            if out:entry(f,'replaceExisting',name in replace)
    entry(model,'version','version 1.x');entry(model,'runOnExecute',False)

def workflow(folder,data,evidence,task,target,short=False):
    folder=Path(folder);folder.mkdir(parents=True)
    root=E.Element('{'+NS+'}config',key='workflow.knime')
    for k,v in [('created_by','5.5.3'),('created_by_nightly',False),('version','4.1.0'),('name','Files' if task.startswith('files') else 'K-means'),('state','CONFIGURED')]:entry(root,k,v)
    cfg(root,'workflow_credentials');nodes=cfg(root,'nodes');links=cfg(root,'connections')
    def node(label,factory,base='org.knime.base'):
        i=len(nodes)+1;d=folder/f'{label} (#{i})';d.mkdir()
        n=cfg(nodes,f'node_{i}')
        for k,v in [('id',i),('node_settings_file',d.name+'/settings.xml'),('node_is_meta',False),('node_type','NativeNode'),('ui_classname','org.knime.core.node.workflow.NodeUIInformation')]:entry(n,k,v)
        array(cfg(n,'ui_settings'),'extrainfo.node.bounds',[60+(i-1)*170,150,100,90])
        s=E.Element('{'+NS+'}config',key='settings.xml');entry(s,'node_file','settings.xml');cfg(s,'flow_stack');entry(cfg(s,'internal_node_subsettings'),'memory_policy','CacheSmallInMemory')
        m=cfg(s,'model')
        for k,v in [('state','CONFIGURED'),('factory',factory),('node-name',label),('node-bundle-name',base),('node-bundle-symbolic-name',base),('node-bundle-version','5.5.0'),('node-bundle-vendor','KNIME AG'),('name',label),('hasContent',False),('isInactive',False)]:entry(s,k,v)
        cfg(s,'factory_settings');cfg(s,'ports')
        annotation=cfg(s,'nodeAnnotation')
        for k,v in [('text',label),('bgcolor',16777215),('x-coordinate',50+(i-1)*170),('y-coordinate',220),('width',130),('height',45),('alignment','CENTER'),('borderSize',0),('borderColor',16777215),('defFontSize',9),('annotation-version',20151123)]:entry(annotation,k,v)
        cfg(annotation,'styles')
        stores=cfg(s,'filestores');entry(stores,'file_store_location','').set('isnull','true');entry(stores,'file_store_id',str(uuid.uuid4()))
        if i>1:
            c=cfg(links,f'connection_{i-2}')
            for k,v in [('sourceID',i-1),('destID',i),('sourcePort',1),('destPort',1)]:entry(c,k,v)
        return s,m,d/'settings.xml'
    files=task.startswith('files');starter=task.endswith('starter')
    s,m,p=node('Input','org.knime.base.node.io.tablecreator.TableCreator2NodeFactory')
    array(m,'rowIndices',[0]);array(m,'columnIndices',[0]);array(m,'values',['' if files else '2'])
    for k,v in [('rowIdPrefix','Row'),('rowIdSuffix',''),('rowIdStartValue',0),('highlightOutputTable',False)]:entry(m,k,v)
    col=cfg(cfg(m,'columnProperties'),'0')
    for k,v in [('UserSetValues',False),('MissValuePattern',''),('ReadPossValsFromFile',False),('SkipThisColumn',False),('ColumnName','filename' if files else 'K')]:entry(col,k,v)
    c=cfg(col,'ColumnClass');entry(c,'cell_class','org.knime.core.data.def.'+('StringCell' if files else 'IntCell'));entry(c,'is_null',False);write(p,s)
    s,m,p=node('Inputs - prepared','org.knime.base.node.jsnippet.JavaSnippetNodeFactory','org.knime.jsnippets')
    reset='\n'.join('Files.writeString(Paths.get('+json.dumps((evidence/n).as_posix())+'), "", StandardCharsets.UTF_8);' for n in ['visits.csv','results.csv'])
    code=reset+'\niteration = 0;\n'
    if files:
        code+='try(java.util.stream.Stream<Path> paths=Files.list(Paths.get('+json.dumps((data/'sales').as_posix())+'))){count=(int)paths.filter(x->x.toString().endsWith(".csv")).count();}\n'
    else:code+='count=3;\n'
    snippet(m,code,out_vars=[('currentIteration','iteration','Integer'),('input_count','count','Integer')]);write(p,s)
    if not starter or (short and not files):
        s,m,p=node('Counting Loop Start','org.knime.base.node.meta.looper.LoopStartCountDynamicNodeFactory')
        entry(m,'loops',1 if short and starter else 3)
        if files:
            v=cfg(cfg(s,'variables'),'loops');entry(v,'used_variable','input_count');entry(v,'exposed_variable','').set('isnull','true')
        entry(cfg(cfg(cfg(s,'node_creation_config'),'Pass through'),'port_0'),'object_class','org.knime.core.node.BufferedDataTable')
        write(p,s)
    label='Read file and mean - prepared' if files else 'K-means and score - prepared'
    s,m,p=node(label,'org.knime.base.node.jsnippet.JavaSnippetNodeFactory','org.knime.jsnippets')
    if files:
        code='''java.util.List<Path> names;
try(java.util.stream.Stream<Path> paths=Files.list(Paths.get(FOLDER_PATH))){names=paths.filter(x->x.toString().endsWith(".csv")).sorted().collect(java.util.stream.Collectors.toList());}
Path file=names.get(iteration);out_file=file.getFileName().toString();
java.util.List<String> rows=Files.readAllLines(file,StandardCharsets.UTF_8);double sum=0;
for(String row:rows.subList(1,rows.size()))sum+=Double.parseDouble(row);
out_mean=sum/(rows.size()-1);
'''.replace('FOLDER_PATH',json.dumps((data/'sales').as_posix()))
        out=[('filename','out_file','String'),('mean','out_mean','Double')];outvars=[]
        text='out_file + "," + out_mean'
    else:
        code=Path(__file__).with_name('KMeansBody.java.txt').read_text().replace('POINTS_PATH',json.dumps((data/'points.csv').as_posix()))
        out=[('K','out_k','Integer'),('score','out_score','Double')];outvars=[('score','score','Double')];text='out_k + "," + out_score'
    code+='\nFiles.writeString(Paths.get('+json.dumps((evidence/'visits.csv').as_posix())+'), '+text+' + "\\n", StandardCharsets.UTF_8, StandardOpenOption.CREATE, StandardOpenOption.APPEND);'
    snippet(m,code,in_vars=[('currentIteration','iteration','Integer')],out_cols=out,out_vars=outvars,replace=['filename' if files else 'K']);write(p,s)
    if not starter or (short and not files):
        if task=='adapt' or (short and not files):
            s,m,p=node('Variable Condition Loop End','org.knime.base.node.meta.looper.condition.LoopEndConditionDynamicNodeFactory')
            for k,v in [('variableName','score'),('variableType','DOUBLE'),('value',str(target if task=='adapt' else 0.0)),('operator','GE'),('propagateLoopVariables',False)]:entry(m,k,v)
            for k,v in [('addLastRows',True),('addLastRowsOnly',False),('addIterationColumn',False)]:array(m,k,[v])
        else:
            s,m,p=node('Loop End','org.knime.base.node.meta.looper.LoopEndDynamicNodeFactory')
            entry(m,'addIterationColumn',False);entry(m,'rowKeyPolicy','APPEND_SUFFIX');entry(m,'propagateLoopVariables',False)
            for k,v in [('ignoreEmptyTables',True),('tolerateColumnTypes',False),('tolerateChangingSpecs',False)]:array(m,k,[v])
        cfg(cfg(s,'node_creation_config'),'Collector');write(p,s)
    s,m,p=node('Results','org.knime.base.node.jsnippet.JavaSnippetNodeFactory','org.knime.jsnippets')
    names=[('filename','name','String'),('mean','value','Double')] if files else [('K','name','Integer'),('score','value','Double')]
    code='Files.writeString(Paths.get('+json.dumps((evidence/'results.csv').as_posix())+'),name + "," + value + "\\n",StandardCharsets.UTF_8,StandardOpenOption.CREATE,StandardOpenOption.APPEND);'
    snippet(m,code,in_cols=names);write(p,s)
    ed=cfg(root,'workflow_editor_settings');entry(ed,'workflow.editor.zoomLevel','1.0','xdouble');entry(ed,'workflow.editor.snapToGrid',False);entry(ed,'workflow.editor.ShowGrid',False);entry(ed,'workflow.editor.gridX',20);entry(ed,'workflow.editor.gridY',20)
    write(folder/'workflow.knime',root)
