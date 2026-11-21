"""Lab policy with a coarse first step and a 250-point minimum gain."""
import json
from pathlib import Path

def record(name, args):
    with Path(__file__).with_suffix(".calls").open("a", encoding="utf-8") as stream:
        print(json.dumps([name, *args]), file=stream)

def next_candidate(k, score, trials):
    record("next_candidate", (k, score, trials))
    if trials == 1:
        return 4 if score < -250 else 3
    if trials == 2:
        if k == 4:
            return 3
        return 4 if score < -100 else 0
    return 0

def keep_searching(k, score, previous):
    record("keep_searching", (k, score, previous))
    return k < 4 and (k == 2 or score - previous >= 250)
