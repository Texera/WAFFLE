"""Regenerate measured figures from saved results without running benchmarks."""
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

subprocess.run([sys.executable, str(ROOT / 'experiments/control_messages/plot.py'),
                str(ROOT / 'figures/control-merge-orders.pdf')], check=True)
subprocess.run([sys.executable, str(ROOT / 'experiments/xy_planning/plot.py')], check=True)
for script in ('generated_loops/plot.py', 'loop_execution/plot_size.py'):
    subprocess.run([sys.executable, str(ROOT / 'experiments' / script)], check=True)
with tempfile.TemporaryDirectory(prefix='waffle-figures-') as temporary:
    subprocess.run([sys.executable, str(ROOT / 'experiments/loop_execution/analyze.py'),
                    str(ROOT / 'experiments/loop_execution/results'), temporary,
                    '--plot', str(ROOT / 'figures/loop-execution-time.pdf')], check=True)
