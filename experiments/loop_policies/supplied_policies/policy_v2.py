"""Lab policy with a sequential search and a 100-point minimum gain."""
import json
from pathlib import Path

def record(name, args):
    with Path(__file__).with_suffix(".calls").open("a", encoding="utf-8") as stream:
        print(json.dumps([name, *args]), file=stream)

def next_candidate(k, score, trials):
    record("next_candidate", (k, score, trials))
    return k + 1 if score < -100 and k < 4 else 0

def keep_searching(k, score, previous):
    record("keep_searching", (k, score, previous))
    return k < 4 and (k == 2 or score - previous >= 100)
