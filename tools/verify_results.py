"""Verify recorded outputs and planning minima without starting either system."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(script, *args, cwd=ROOT):
    result = subprocess.run([sys.executable, str(script), *map(str, args)], cwd=cwd,
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    return result.stdout


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    with tempfile.TemporaryDirectory(prefix='waffle-verify-') as folder:
        temp = Path(folder)
        case = ROOT / 'experiments/case_study'
        shutil.copytree(case / 'results', temp / 'cases')
        run(case / 'check.py', temp / 'cases')
        summary = read(temp / 'cases/comparison.json')
        assert summary['matched'] == summary['total'] == 8
        assert sum(r['rows'] for r in summary['cases']) == 241
        assert summary == read(case / 'results/comparison.json')
        print('Case study: 8/8 matches; 241 output rows verified')
        print(run(ROOT / 'experiments/control_messages/verify.py').strip())
        print(run(ROOT / 'experiments/control_messages/verify_binding.py').strip())
        execution = ROOT / 'experiments/loop_execution'
        run(execution / 'analyze.py', execution / 'results', temp / 'execution')
        assert read(temp / 'execution/summary.json') == read(execution / 'results/summary.json')
        assert (temp / 'execution/measurements.csv').read_bytes() == (execution / 'results/measurements.csv').read_bytes()
        print('Execution: all 72 runs verified; 60 measurements reproduce the summary')
        planning = ROOT / 'experiments/xy_planning'
        shutil.copytree(planning / 'raw', temp / 'planning')
        output = run(planning / 'runner/analyze-compiled.py', temp / 'planning')
        print(output.strip().splitlines()[-1])
        assert read(temp / 'planning/verification.json') == read(planning / 'raw/verification.json')
        spec = importlib.util.spec_from_file_location('xy_plot', planning / 'plot.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assert module.summarize() == read(planning / 'summary.json')
        print('Planning: all 3,600 measured plans reproduce equal X/Y minima and timing summaries')
        for folder, test in [(case, 'test_check.py'),
                             (ROOT / 'experiments/control_messages', 'test_verify_binding.py'),
                             (execution, 'test_experiment.py'),
                             (planning / 'runner', 'test_module_oracle.py')]:
            run(folder / test, cwd=folder)
            print('PASS', test)
    print('All saved-result checks passed; no engine or KNIME execution was started.')


if __name__ == '__main__':
    main()
