"""Execute instrumented originals with reset, retaining every success or failure."""
import argparse,json,subprocess,time
from pathlib import Path

def run(runtime,package,only=None):
    java=next(runtime.glob('plugins/org.knime.binary.jre.win32.x86_64_*/jre/bin/java.exe'))
    launcher=next(runtime.glob('plugins/org.eclipse.equinox.launcher_*.jar'))
    ini=(runtime/'knime.ini').read_text().splitlines();vmargs=ini[ini.index('-vmargs')+1:]
    for case in json.loads((package/'selection.json').read_text())['cases']:
        n=case['case']
        if only and n!=only:continue
        log=package/f'{n:02}-knime.log'
        if log.exists():raise ValueError(f'Existing evidence: {log}')
        command=[str(java),*vmargs,'-Dfile.encoding=UTF-8','-jar',str(launcher),'-nosplash','-consoleLog','-application','org.knime.product.KNIME_BATCH_APPLICATION',
                 '-reset','-nosave','-failonloaderror','-workflowDir='+str(package/case['workflow']),'-data',str(package/'workspace')]
        start=time.perf_counter()
        with log.open('w',encoding='utf-8') as out:
            try:code=subprocess.run(command,cwd=runtime,stdout=out,stderr=subprocess.STDOUT,timeout=300).returncode
            except subprocess.TimeoutExpired:code=-1
        result=dict(case=n,exit_code=code,seconds=time.perf_counter()-start,exports_present=all((package/f).exists() for f in case['expected_exports']),command=command)
        (package/f'{n:02}-knime-run.json').write_text(json.dumps(result,indent=2))
        print(n,code,result['exports_present'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('package',type=Path);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--only',type=int)
    a=p.parse_args();run(a.runtime,a.package,a.only)
