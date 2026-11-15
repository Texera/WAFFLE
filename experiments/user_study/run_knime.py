"""Launch KNIME through Java directly, with no Windows error-dialog launcher."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


def launch(runtime, options, log, timeout=300):
    java = next(runtime.glob('plugins/org.knime.binary.jre.win32.x86_64_*/jre/bin/java.exe'))
    launcher = next(runtime.glob('plugins/org.eclipse.equinox.launcher_*.jar'))
    ini = (runtime / 'knime.ini').read_text(encoding='utf-8').splitlines()
    vmargs = ini[ini.index('-vmargs') + 1:]
    command = [str(java), *vmargs, '-Dfile.encoding=UTF-8', '-jar', str(launcher), '-nosplash', '-consoleLog', *options]
    with log.open('w', encoding='utf-8') as out:
        return subprocess.run(command, cwd=runtime, stdout=out, stderr=subprocess.STDOUT,
                              timeout=timeout).returncode


def run(runtime, package, only=None):
    manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
    selected = [s for s in manifest['runs'] if s['tool'] == 'knime'
                and (not only or only in s['id'])]
    if not selected:
        raise ValueError(f'No KNIME runs match {only!r}')
    for name in ('check-all.json', 'check-knime.json'):
        (package / name).unlink(missing_ok=True)
    failed = False
    for spec in selected:
        label = spec['id']
        folder = package / spec['workflow']
        run_dir = folder.parent
        # Only this explicitly named run's two disposable CSVs are reset.
        for name in ('visits.csv', 'results.csv', 'exit-code.txt'):
            (run_dir / name).unlink(missing_ok=True)
        print(f'KNIME {label} starting', flush=True)
        try:
            code = launch(runtime, ['-application', 'org.knime.product.KNIME_BATCH_APPLICATION',
                                   '-reset', '-nosave', '-failonloaderror', '-workflowDir=' + str(folder),
                                   '-data', str(package / 'facilitator' / 'knime-workspace')],
                          run_dir / 'engine.log')
        except subprocess.TimeoutExpired:
            code = -1
        (run_dir / 'exit-code.txt').write_text(str(code) + '\n', encoding='utf-8')
        print(f'KNIME {label} exited {code}', flush=True)
        completed = code == 0 and all((run_dir / name).is_file() for name in ('visits.csv', 'results.csv'))
        failed |= not completed
        if not completed:
            print((run_dir / 'engine.log').read_text(encoding='utf-8', errors='replace')[-6000:])
            break
    return int(failed)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime', type=Path, required=True)
    p.add_argument('--package', type=Path, required=True)
    p.add_argument('--only')
    a = p.parse_args()
    raise SystemExit(run(a.runtime, a.package, a.only))
