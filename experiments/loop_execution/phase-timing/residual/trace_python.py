"""Record elapsed spans per input batch or reader. No per-tuple disk writes."""

import os
from functools import wraps
from pathlib import Path
from threading import Lock, local
from time import perf_counter_ns, time_ns

state = local()
lock = Lock()
path = Path(os.environ["WAFFLE_PHASE_DIR"]) / f"residual-{os.getpid()}.tsv"


def record(kind, name, left, right, active=0, rows=0):
    with lock, path.open("a", encoding="utf8") as f:
        f.write(f"{kind}\t{name}\t{left}\t{right}\t{active}\t{rows}\n")


def read_call(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        acc = getattr(state, "reader", None)
        if acc is None:
            return fn(*args, **kwargs)
        t = perf_counter_ns()
        try:
            result = fn(*args, **kwargs)
            if fn.__name__ == "__next__":
                acc[1] += 1
            return result
        finally:
            acc[0] += perf_counter_ns() - t

    return wrapped


def reader(fn, kind, identify):
    @wraps(fn)
    def wrapped(self, *args, **kwargs):
        assert getattr(state, "reader", None) is None
        acc = [0, 0]
        state.reader = acc
        begin = time_ns()
        try:
            return fn(self, *args, **kwargs)
        finally:
            end = time_ns()
            state.reader = None
            record(kind, identify(self), begin, end, *acc)

    return wrapped


def read_port(fn):
    return reader(fn, "port_read", lambda s: s.worker_actor_id.name)


def read_loop(fn):
    return reader(fn, "loop_read", lambda s: str(s.context.worker_id))


def tuple_batch(fn):
    @wraps(fn)
    def wrapped(self, *args, **kwargs):
        lo = time_ns()
        try:
            return fn(self, *args, **kwargs)
        finally:
            hi = time_ns()
            record("tuple_batch", str(self.context.worker_id), lo, hi)

    return wrapped


def finish_rows(main):
    lo = time_ns()
    try:
        main.process_input_tuple()
    finally:
        hi = time_ns()
        record("tuple_finish", str(main.context.worker_id), lo, hi)
