import json
from pathlib import Path
import subprocess


def pinned_runtime(repo):
    # prepare_engine.py reconstructs the expected tree in the index.
    lock = Path(__file__).resolve().parents[2] / "implementation.lock.json"
    expected = json.loads(lock.read_text())["runtime"]["tree"]
    tree = subprocess.check_output(["git", "write-tree"], cwd=repo, text=True).strip()
    if tree != expected or subprocess.run(["git", "diff", "--quiet"], cwd=repo).returncode:
        raise ValueError(f"runtime tracked sources must match tree {expected}")
