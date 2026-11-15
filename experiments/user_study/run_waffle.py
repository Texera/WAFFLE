"""Run the exported workflow JSONs using Texera's real coordinator and workers."""
import argparse
import os
import json
from pathlib import Path
import subprocess


def invalidate_runs(package, only=None):
    manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
    selected = [s for s in manifest['runs'] if s['tool'] == 'waffle'
                and (not only or only in s['id'])]
    if not selected:
        raise ValueError(f'No WAFFLE runs match {only!r}')
    for name in ('check-all.json', 'check-waffle.json'):
        (package / name).unlink(missing_ok=True)
    for spec in selected:
        folder = (package / spec['workflow']).parent
        for name in ('visits.csv', 'results.csv', 'engine-result.txt', 'exit-code.txt'):
            (folder / name).unlink(missing_ok=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--python', type=Path, required=True)
    p.add_argument('--java', type=Path, required=True)
    p.add_argument('--sbt-launch', type=Path, required=True)
    p.add_argument('--only', help='Optional ScalaTest substring, e.g. starter-visible')
    args = p.parse_args()
    # Clear prior evidence even if compilation or JVM startup fails next.
    invalidate_runs(args.package, args.only)
    env = os.environ.copy()
    env['PATH'] = 'C:/Program Files/Git/bin;' + str(args.python.parent) + ';' + env.get('PATH', '')
    env.update(UDF_PYTHON_PATH=str(args.python), STORAGE_ICEBERG_CATALOG_TYPE='postgres',
               TEXERA_HOME=str(args.repo), WAFFLE_STUDY_PACKAGE=str(args.package))
    env.pop('AMBER_TEST_FILTER', None)
    # Build-only configuration. No repository source/build-file edits.
    source = Path(__file__).with_name('StudyWorkflowSpec.scala').resolve().as_posix()
    jvm = [line.strip() for line in (args.repo / '.jvmopts').read_text(encoding='utf-8').splitlines()
           if line.strip() and not line.startswith('#')]
    test = 'WorkflowExecutionService/testOnly *StudyWorkflowSpec -- -oD'
    if args.only:
        test += ' -z ' + args.only
    cmd = [str(args.java), *jvm, '-Dsbt.supershell=false', '-jar', str(args.sbt_launch),
           'set DAO / jooqGenerate := Seq.empty',
           f'set WorkflowExecutionService / Test / unmanagedSources += file("{source}")', test]
    log = args.package / 'facilitator' / 'waffle-engine.log'
    with log.open('w', encoding='utf-8') as f:
        code = subprocess.run(cmd, cwd=args.repo, env=env, stdout=f, stderr=subprocess.STDOUT).returncode
    print(log.read_text(encoding='utf-8', errors='replace')[-9000:])
    raise SystemExit(code)
