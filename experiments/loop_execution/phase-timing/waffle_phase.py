"""Batch-level phase intervals, one append per writer setup or nonempty flush."""

import os
import time
from functools import wraps
from pathlib import Path

path = Path(os.environ["WAFFLE_PHASE_DIR"]) / f"python-{os.getpid()}.tsv"


def measure(function, phase, identity):
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        if phase == "py_flush" and not self.buffer:
            return function(self, *args, **kwargs)
        start = time.time_ns()
        try:
            return function(self, *args, **kwargs)
        finally:
            end = time.time_ns()
            with path.open("a", encoding="utf8") as f:
                f.write(f"{phase}\t{identity(self, args)}\t{start}\t{end}\n")

    return wrapped


def timed_setup(fn):
    return measure(fn, "writer_setup", lambda obj, args: str(obj.worker_id))


def timed_flush(fn):
    return measure(
        fn, "py_flush", lambda obj, args: obj.table_namespace + "." + obj.table_name
    )
