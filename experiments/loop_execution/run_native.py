"""Run the native harness against an already configured Texera checkout."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('package', type=Path)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--python', type=Path, default=Path(sys.executable))
    default_java = str(Path(os.environ['JAVA_HOME']) / 'bin' / ('java.exe' if os.name == 'nt' else 'java')) if os.environ.get('JAVA_HOME') else shutil.which('java')
    p.add_argument('--java', default=default_java)
    p.add_argument('--sbt-launch', type=Path, default=os.environ.get('SBT_LAUNCH'))
    p.add_argument('--only')
    p.add_argument('--case-study', action='store_true')
    p.add_argument('--binding', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    a.package, a.repo, a.python = a.package.resolve(), a.repo.resolve(), a.python.resolve()
    if not a.sbt_launch or not a.sbt_launch.is_file():
        p.error('Supply --sbt-launch /path/to/sbt-launch.jar or SBT_LAUNCH')
    if not a.java or not Path(a.java).is_file() or not a.python.is_file():
        p.error('--java and --python must identify installed executables')
    if not (a.package / 'manifest.json').is_file():
        p.error('Generate a fresh experiment package first')
    if (a.package / 'native.jsonl').exists() and not a.dry_run:
        p.error('Use a fresh package; native evidence already exists')
    env = os.environ.copy()
    env.update(UDF_PYTHON_PATH=str(a.python), STORAGE_ICEBERG_CATALOG_TYPE='postgres',
               TEXERA_HOME=str(a.repo), WAFFLE_EXPERIMENT_PACKAGE=str(a.package),
               SCHEDULE_GENERATOR_MAX_CONCURRENT_REGIONS='1', OMP_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    env['PATH'] = str(a.python.parent) + os.pathsep + env.get('PATH', '')
    env.pop('AMBER_TEST_FILTER', None)
    flags = [x.strip() for x in (a.repo / '.jvmopts').read_text().splitlines()
             if x.strip() and not x.strip().startswith('#')]
    source = Path(__file__).with_name('NativeExecutionSpec.scala').resolve()
    test_name = 'NativeExecutionSpec'
    if a.case_study:
        source = Path(__file__).resolve().parents[1] / 'case_study/CaseExecutionSpec.scala'
        test_name = 'CaseExecutionSpec'
    if a.binding:
        source = Path(__file__).resolve().parents[1] / 'control_messages/MultiworkerBindingSpec.scala'
        test_name = 'MultiworkerBindingSpec'
    test = f'WorkflowExecutionService/testOnly *{test_name} -- -oD'
    if a.only:
        test += ' -z ' + a.only
    cmd = [str(a.java), *flags, '-Dsbt.supershell=false', '-jar', str(a.sbt_launch.resolve()),
           'set DAO / jooqGenerate := Seq.empty',
           f'set WorkflowExecutionService / Test / unmanagedSources += file("{source.as_posix()}")', test]
    git = lambda *args: subprocess.check_output(['git', *args], cwd=a.repo, text=True).strip()
    provenance = dict(revision=git('rev-parse', 'HEAD'), source_tree=git('write-tree'),
                      tracked_worktree_diff=git('diff', '--stat'), command=cmd)
    if a.dry_run:
        print(json.dumps(provenance, indent=2))
        return 0
    (a.package / 'engine-provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    with (a.package / 'engine.log').open('w', encoding='utf-8') as stream:
        code = subprocess.run(cmd, cwd=a.repo, env=env, stdout=stream, stderr=subprocess.STDOUT).returncode
    (a.package / 'exit-code.txt').write_text(str(code), encoding='utf-8')
    print('Engine exit', code, 'log', a.package / 'engine.log')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
