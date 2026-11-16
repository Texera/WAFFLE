"""Execute relocated portable KNIME archives in the installed native engine."""
import argparse
import json
from pathlib import Path
import shutil
import tempfile
import zipfile
from model import expected, check_evidence
from study import read_csv
from portable_knime import package
from run_knime import launch


def run(root,runtime):
    manifest=json.loads((root/'manifest.json').read_text())
    out=root/'facilitator/portable-rehearsal';out.mkdir(exist_ok=False)
    records=[]
    for r in manifest['runs']:
        if r['tool']!='knime' or r['case']!='visible':continue
        name=f"35min-{r['pack']}-{r['task']}"
        archive=out/(name+'.knwf')
        workflow=root/r['workflow'];data=root/r['data']
        token=package(workflow,archive,data,workflow.parent)
        # Extraction into a different location exercises the actual shipped archive.
        moved=out/'relocated'/name
        with zipfile.ZipFile(archive) as z:z.extractall(moved)
        log=out/(name+'.log')
        code=launch(runtime,['-application','org.knime.product.KNIME_BATCH_APPLICATION','-reset','-nosave','-failonloaderror','-workflowDir='+str(moved/name),'-data',str(out/'workspace')],log)
        audit=Path(tempfile.gettempdir())/token
        visits=read_csv(audit/'visits.csv',False);rows=read_csv(audit/'results.csv',False)
        passed=check_evidence(expected(data,r['task'],r['target']),visits,rows,code)
        records.append(dict(id=r['id'],exit_code=code,passed=passed,visits=visits,results=rows))
        print(name,passed,flush=True)
        for file in ('visits.csv','results.csv'):shutil.copyfile(audit/file,out/(name+'-'+file))
        (out/'checks.json').write_text(json.dumps(records,indent=2)+'\n')
        if not passed:return 1
    return 0 if len(records)==6 and all(r['passed'] for r in records) else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',required=True,type=Path);p.add_argument('--runtime',required=True,type=Path);a=p.parse_args()
    raise SystemExit(run(a.package,a.runtime))
