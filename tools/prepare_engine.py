"""Fetch pinned public Texera sources and verify their complete Git tree."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode', choices=['runtime', 'runtime-scoped', 'planning'])
    p.add_argument('destination', type=Path, help='New directory; existing directories are refused')
    a = p.parse_args()
    lock = json.loads((ROOT / 'implementation.lock.json').read_text(encoding='utf-8'))
    spec = lock[a.mode]
    if a.destination.exists():
        p.error('Destination already exists; choose a new directory')
    layers = [lock['runtime'], spec] if a.mode == 'runtime-scoped' else [spec]
    base = layers[0]
    for layer in layers:
        if 'patch' in layer:
            patch = ROOT / layer['patch']
            if hashlib.sha256(patch.read_bytes()).hexdigest() != layer['patch_sha256']:
                raise SystemExit(f'Checksum mismatch: {patch.name}')
    a.destination.mkdir(parents=True)
    def git(*args, capture=False):
        result = subprocess.run(['git', *args], cwd=a.destination, check=True,
                                text=True, stdout=subprocess.PIPE if capture else None)
        return result.stdout.strip() if capture else None
    git('init')
    git('config', 'core.autocrlf', 'false')
    git('remote', 'add', 'origin', lock['source_repository'])
    git('fetch', '--depth', '1', 'origin', base.get('base', base.get('revision')))
    git('checkout', '--detach', 'FETCH_HEAD')
    for layer in layers:
        if 'patch' in layer:
            git('apply', '--index', '--whitespace=nowarn', str(ROOT / layer['patch']))
        tree = git('write-tree', capture=True)
        if tree != layer['tree']:
            raise SystemExit(f'Source tree mismatch: {tree} != {layer["tree"]}')
    print(f'Verified {a.mode} source tree {tree}: {a.destination.resolve()}')
    if 'patch' in spec:
        print('Runtime patch is staged; HEAD is the public base commit. Do not discard staged changes.')


if __name__ == '__main__':
    main()
