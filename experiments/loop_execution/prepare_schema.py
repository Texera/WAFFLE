"""Generate DAO files from the pinned checkout DDL in embedded PostgreSQL."""
import argparse
import os
from pathlib import Path
import subprocess


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--java-home', type=Path, default=os.environ.get('JAVA_HOME'))
    p.add_argument('--classpath-file', type=Path)
    p.add_argument('--jooq-codegen', type=Path, required=True, help='jooq-codegen 3.19.36 JAR')
    p.add_argument('--jooq-meta', type=Path, required=True, help='jooq-meta 3.19.36 JAR')
    p.add_argument('--jaxb', type=Path, required=True, help='jakarta.xml.bind-api 4.0.0 JAR')
    a = p.parse_args()
    a.repo, a.output = a.repo.resolve(), a.output.resolve()
    if not a.java_home:
        p.error('Set JAVA_HOME or --java-home to a JDK 17 installation')
    cp_file = a.classpath_file or a.repo / 'amber/target/streams/test/fullClasspath/_global/streams/export'
    for path in [cp_file, a.jooq_codegen, a.jooq_meta, a.jaxb]:
        if not path.is_file():
            p.error(f'Missing dependency: {path}')
    cp = os.pathsep.join([cp_file.read_text(encoding='utf-8').strip(),
                         *[str(x.resolve()) for x in (a.jooq_codegen, a.jooq_meta, a.jaxb)]])
    a.output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).with_name('GenerateSchema.java').resolve()
    for tool, args in [('javac', ['-cp', cp, '-d', str(a.output), str(source)]),
                       ('java', ['-cp', str(a.output) + os.pathsep + cp, 'GenerateSchema'])]:
        executable = a.java_home / 'bin' / (tool + ('.exe' if os.name == 'nt' else ''))
        argfile = a.output / (tool + '.args')
        argfile.write_text('\n'.join('"' + str(x).replace('\\', '/') + '"' for x in args), encoding='utf-8')
        with (a.output / (tool + '.log')).open('w', encoding='utf-8') as log:
            subprocess.run([str(executable), '@' + str(argfile)], cwd=a.repo,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
    print('Generated from checkout DDL:', a.output)


if __name__ == '__main__':
    main()
