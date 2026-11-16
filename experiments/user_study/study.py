"""Prepare local study materials and independently check native dry-run evidence."""
import argparse
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile
import knime
import waffle
import portable_knime
from model import make_data, expected, check_evidence


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(root, remote=None, short=False):
    root=root.resolve(); root.mkdir(parents=True, exist_ok=False)
    (root/'facilitator').mkdir(); runs=[]; packs=[]
    cases=[('sweep-starter','visible'),('sweep','visible'),('sweep','first'),
           ('adapt','visible'),('adapt','first'),('adapt','cap'),
           ('files-starter','visible'),('files','visible'),('files','extra')]
    if short:cases=[(task,variant) for task,variant in cases if not task.startswith('files')]
    for pack in ('A','B'):
        info=make_data(root/'data'/pack,pack); packs.append(info)
        for tool in ('knime','waffle'):
            for task,variant in cases:
                label=f'{tool}-{pack}-{task}-{variant}'
                directory=root/'facilitator'/'runs'/label; directory.mkdir(parents=True)
                data=root/'data'/pack/variant
                mapped=lambda p: PurePosixPath(remote)/p.relative_to(root).as_posix() if remote and tool=='waffle' else p
                if tool=='knime':
                    path=directory/'workflow';knime.workflow(path,data,directory,task,info['target'],short=short)
                    with zipfile.ZipFile(directory/'workflow.knwf','w',zipfile.ZIP_DEFLATED) as z:
                        for f in path.rglob('*'):
                            if f.is_file():z.write(f,f'{pack}-{task}-{variant}/'+f.relative_to(path).as_posix())
                else:
                    path=directory/'workflow.json';save(path,waffle.graph(mapped(data),mapped(directory),task,info['target'],short=short))
                runs.append(dict(id=label,tool=tool,pack=pack,task=task,case=variant,
                                 workflow=path.relative_to(root).as_posix(),data=data.relative_to(root).as_posix(),
                                 target=info['target'],expected=expected(data,task,info['target'])))
            dest=root/'participants'/pack/tool;dest.mkdir(parents=True)
            for task in (('sweep-starter',) if short else ('sweep-starter','files-starter')):
                source=root/'facilitator'/'runs'/f'{tool}-{pack}-{task}-visible'/('workflow.knwf' if tool=='knime' else 'workflow.json')
                if short and tool=='knime':
                    portable_knime.package(source.parent/'workflow',dest/(task+source.suffix),root/'data'/pack/'visible',source.parent)
                else:shutil.copyfile(source,dest/(task+source.suffix))
            (dest/'START-HERE.txt').write_text(('Run the connected loop once: it returns K=2 and its score. Keep the prepared calculation and Results nodes unchanged. Follow the single form, save a separate copy after each task, and stop each task at four minutes.\n' if short else 'Run the provided single-input starter first. The facilitator supplies each task card separately. Keep the prepared calculation and Results nodes unchanged. Save a copy after each activity.\n'),encoding='utf-8')
            if short:
                fallback=root/'facilitator/fallbacks'/pack/tool
                fallback.mkdir(parents=True)
                source=root/'facilitator/runs'/f'{tool}-{pack}-sweep-visible'
                if tool=='knime':
                    portable_knime.package(source/'workflow',fallback/'sweep-fallback.knwf',root/'data'/pack/'visible',source)
                else:
                    shutil.copyfile(source/'workflow.json',fallback/'sweep-fallback.json')
                (fallback/'READ-BEFORE-OPENING.txt').write_text('Use only if the sweep task was unfinished. Save the unfinished sweep first, then open this copy for the adaptation task. Record fallback use in the form. Do not inspect this file during the sweep task.\n',encoding='utf-8')
        cards=root/'cards'/pack;cards.mkdir(parents=True)
        texts={
            '1-create.txt':'Add a loop to run the supplied K-means workflow for K = 2, 3 and 4. Return every K and score. Which K has the highest score? Write your answer separately. Save the workflow. You have 10 active minutes.',
            '2-adapt.txt':f'Change your saved workflow to stop when the score first reaches {info["target"]:.6f}. Include that result. If the target is not reached, finish K = 2, 3 and 4. Return the scores and identify the best K actually tried. You have 5 active minutes.',
            '3-files.txt':'Add a loop to the file starter to read every CSV in the supplied sales folder. Return each filename and its mean price, in any order. The number of files may change. Save the workflow. You have 10 active minutes.'
        }
        if short:
            texts={
                '1-configure.txt':'The connected loop runs K=2 once. Change it to try K=2,3,4 and return every K and score. Which K has the highest score? Keep the prepared body unchanged and save a separate workflow copy. Stop at four minutes, including execution waits.',
                '2-adapt.txt':f'Change your saved workflow to stop when score first reaches {info["target"]:.6f}, including that row. If it never reaches the target, stop after K=4. Return every K and score actually tried. Save a separate copy. Stop at four minutes, including execution waits.'}
        for name,text in texts.items():(cards/name).write_text(text+'\n',encoding='utf-8')
    save(root/'manifest.json',dict(version=2 if short else 1,protocol='35-minute' if short else 'legacy-three-task',packs=packs,runs=runs,waffle_runtime_root=remote))
    hashes={p.relative_to(root).as_posix():digest(p) for p in root.rglob('*') if p.is_file()}
    save(root/'input-hashes.json',hashes)
    print(f'Prepared {len(runs)} native checks at {root}')


def read_csv(path,files):
    with path.open(newline='',encoding='utf-8') as f:
        return [dict(filename=r[0],mean=float(r[1])) if files else dict(K=int(r[0]),score=float(r[1])) for r in csv.reader(f) if r]


def check(root,tool=None):
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    hashes=json.loads((root/'input-hashes.json').read_text(encoding='utf-8'))
    altered=[name for name,h in hashes.items() if not (root/name).is_file() or digest(root/name)!=h]
    records=[]
    for r in manifest['runs']:
        if tool and r['tool']!=tool:continue
        p=root/r['workflow'];d=p if p.is_dir() else p.parent
        if r['tool']=='knime':d=p.parent
        code=None
        try:
            code=int((d/'exit-code.txt').read_text())
            want=expected(root/r['data'],r['task'],r['target'])
            visits=read_csv(d/'visits.csv',r['task'].startswith('files'))
            results=read_csv(d/'results.csv',r['task'].startswith('files'))
            if r['task'].startswith('files'):
                visits.sort(key=lambda x:x['filename']);results.sort(key=lambda x:x['filename'])
            passed=check_evidence(want,visits,results,code) and not altered
            error='' if passed else 'Trace, output, exit code, or input fingerprint differs'
        except (OSError,ValueError,IndexError) as e:
            passed=False;error=str(e);visits=[];results=[]
        records.append(dict(id=r['id'],tool=r['tool'],pack=r['pack'],task=r['task'],case=r['case'],target=r['target'],exit_code=code,passed=passed,visits=visits,results=results,error=error))
    report=dict(passed=bool(records) and all(r['passed'] for r in records),changed_inputs=altered,runs=records)
    save(root/f'check-{tool or "all"}.json',report)
    print(f'{sum(r["passed"] for r in records)}/{len(records)} pass; changed inputs: {len(altered)}')
    for r in records:
        if not r['passed']:print(r['id'],r['error'])
    return 0 if report['passed'] else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    gen=sub.add_parser('prepare');gen.add_argument('root',type=Path);gen.add_argument('--waffle-runtime-root')
    gen.add_argument('--short',action='store_true',help='Connected-loop, two-task 35-minute protocol')
    chk=sub.add_parser('check');chk.add_argument('root',type=Path);chk.add_argument('--tool',choices=['knime','waffle'])
    a=p.parse_args()
    if a.command=='prepare':prepare(a.root,a.waffle_runtime_root,short=a.short)
    else:raise SystemExit(check(a.root,a.tool))
