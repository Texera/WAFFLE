"""Execute the two comparison-engine workflows and retain their native output."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from recursive.containers import run


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("system", choices=("n8n", "rapidminer"))
    p.add_argument("directory", type=Path)
    a = p.parse_args()
    run(a.directory.resolve(), a.system, kinds=("hierarchy",))
