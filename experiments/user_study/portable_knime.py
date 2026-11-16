"""Package the short KNIME task without machine-specific paths.

Tiny fixture rows are embedded in the prepared calculation. Audit CSVs go to
the JVM temporary directory under a unique package ID, reset on each execution.
Loop controls and computation remain identical to the checked native graph.
"""
import json
from pathlib import Path
import uuid
import xml.etree.ElementTree as E
import zipfile
import knime


def package(source, destination, data, evidence):
    token='waffle-study-'+uuid.uuid4().hex
    temp='Paths.get(System.getProperty("java.io.tmpdir"), '+json.dumps(token)+')'
    points='java.util.Arrays.asList('+','.join(json.dumps(s) for s in (data/'points.csv').read_text().splitlines())+')'
    with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
        for file in source.rglob('*'):
            if not file.is_file():continue
            content=file.read_bytes()
            if file.name=='settings.xml':
                tree=E.fromstring(content)
                for e in tree.iter('{'+knime.NS+'}entry'):
                    if e.get('key')!='scriptBody':continue
                    code=e.get('value').replace('%%00010','\n')
                    code=code.replace('Files.readAllLines(Paths.get('+json.dumps((data/'points.csv').as_posix())+'), StandardCharsets.UTF_8)',points)
                    for name in ('visits.csv','results.csv'):
                        code=code.replace('Paths.get('+json.dumps((evidence/name).as_posix())+')',temp+'.resolve('+json.dumps(name)+')')
                    if 'iteration = 0;' in code:
                        code=code.replace('try {\n','try {\nFiles.createDirectories('+temp+');\n',1)
                    e.set('value',code.replace('\n','%%00010'))
                content=E.tostring(tree,encoding='utf-8',xml_declaration=True)
            archive.writestr(destination.stem+'/'+file.relative_to(source).as_posix(),content)
    return token
