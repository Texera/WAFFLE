"""Launch the pinned native-large planning benchmark on Windows."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--java-home', type=Path, default=os.environ.get('JAVA_HOME'))
    p.add_argument('--python', type=Path, default=Path(sys.executable))
    p.add_argument('--shell', default=shutil.which('powershell') or shutil.which('pwsh'))
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    if not a.shell or not a.java_home:
        p.error('Provide PowerShell and --java-home (JDK 17)')
    script = a.repo.resolve() / 'experiment/xy-planning/run-compiled.ps1'
    if not script.is_file():
        p.error('Prepare the planning checkout first')
    cmd = [a.shell, '-NoProfile', '-File', str(script), '-Suite', 'native-large',
           '-Forks', '3', '-Warmups', '20', '-Repetitions', '100',
           '-JavaHome', str(a.java_home.resolve()), '-Python', str(a.python.resolve())]
    if a.dry_run:
        print(subprocess.list2cmdline(cmd))
    else:
        subprocess.run(cmd, cwd=a.repo, check=True)


if __name__ == '__main__':
    main()
