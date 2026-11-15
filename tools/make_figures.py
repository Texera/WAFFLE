"""Regenerate both measured figures from saved results; no benchmarks run."""
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

subprocess.run([sys.executable, str(ROOT / 'experiments/xy_planning/plot.py')], check=True)
with tempfile.TemporaryDirectory(prefix='waffle-figures-') as temporary:
    subprocess.run([sys.executable, str(ROOT / 'experiments/loop_execution/analyze.py'),
                    str(ROOT / 'experiments/loop_execution/results'), temporary,
                    '--plot', str(ROOT / 'figures/loop-execution-time.pdf')], check=True)
