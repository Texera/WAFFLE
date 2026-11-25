"""Deliver legal arrival orders to fresh native workers and retain their observed outputs."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

K = {"K": 2}
R = {"ratio": 0.8}
CASES = {
    "equal": [("left", K), ("right", K)],
    "independent": [("left", K), ("right", R)],
    "conflict": [("left", K), ("right", {"K": 3})],
}


def measure(repo):
    sys.path.insert(0, str(repo.resolve() / "amber/src/main/python"))
    from core.models import InternalQueue, State, StateFrame
    from core.models.internal_queue import DataElement
    from core.runnables import MainLoop
    from proto.org.apache.texera.amber.core import ActorVirtualIdentity, ChannelIdentity, PortIdentity
    from pytexera import UDFOperatorV2

    class Receiver(UDFOperatorV2):
        def __init__(self):
            self.calls = []

        def process_state(self, state, port):
            self.calls.append(dict(state))
            return state

        def process_tuple(self, row, port):
            yield row

    def trace(case, frames, paths=None):
        inputs = InternalQueue()
        worker = MainLoop("observer", inputs, InternalQueue())
        receiver = Receiver()
        worker.context.executor_manager.executor = receiver
        channels = {}
        for index, path in enumerate(("left", "right")):
            channel = ChannelIdentity(ActorVirtualIdentity(path), ActorVirtualIdentity("observer"), False)
            port = PortIdentity(index)
            worker.context.input_manager.add_input_port(port, State.SCHEMA, [], [])
            worker.context.input_manager.register_input(channel, port)
            channels[path] = channel
        output = worker.context.output_manager
        sent = []
        # Observe the actual frames handed to output, without a network peer.
        original = output.emit_state
        def record(state, depth, block, message_id):
            sent.append(dict(state))
            return original(state, depth, block, message_id)
        output.emit_state = record
        events = []
        try:
            for i, (message_id, values, block, depth) in enumerate(frames):
                path = paths[i] if paths else ("right" if message_id in ("right", "b", "inner") else "left")
                frame = StateFrame(State(values), loop_start_id=block, loop_counter=depth,
                                   message_id=message_id)
                inputs.put(DataElement(tag=channels[path], payload=frame))
                worker.receive(inputs.get())
                exc = worker.context.exception_manager.exc_info
                events.append(dict(id=message_id, path=path, incoming=values, block=block, depth=depth,
                                   callbacks=deepcopy(receiver.calls), forwarded=deepcopy(sent),
                                   visible=dict(receiver.state or {}), error=str(exc[1]) if exc else None))
                if exc:
                    break
        finally:
            worker.data_processor.stop()
            condition = worker.context.tuple_processing_manager.context_switch_condition
            with condition:
                condition.notify_all()
            worker.stop()
            worker.context.close()
        return dict(case=case, events=events)

    records = []
    for case, pair in CASES.items():
        for order in (pair, list(reversed(pair))):
            records.append(trace(case, [(tag, val, "loop", 0) for tag, val in order]))
    # Figure 13: the upper path sends K before ratio. The lower K can be anywhere.
    for pos in range(3):
        messages = [("start", K), ("filter", R)]
        paths = ["left", "left"]
        paths.insert(pos, "right")
        messages.insert(pos, ("start", K))
        records.append(trace("figure13", [(tag, val, "loop", 0) for tag, val in messages], paths))
    records.append(trace("nested", [("outer1", K, "outer", 1), ("inner", {"K": 3}, "inner", 0),
                                    ("outer2", K, "outer", 1)]))
    records.append(trace("partial", [("a", K, "loop", 0), ("b", {**K, **R}, "loop", 0)]))
    records.append(trace("atomic", [("a", K, "loop", 0), ("b", {**R, "K": 3}, "loop", 0)]))
    return records


def verify(records):
    path_orders = {("right", "left", "left"), ("left", "right", "left"), ("left", "left", "right")}
    expected_orders = {
        **{name: [pair, list(reversed(pair))] for name, pair in CASES.items()},
        "figure13": [[("start", K), ("start", K), ("filter", R)]] * 2
                    + [[("start", K), ("filter", R), ("start", K)]],
        "nested": [[("outer1", K), ("inner", {"K": 3}), ("outer2", K)]],
        "partial": [[("a", K), ("b", {**K, **R})]],
        "atomic": [[("a", K), ("b", {**R, "K": 3})]],
    }
    for record in records:
        name, events = record["case"], record["events"]
        order = [(e["id"], e["incoming"]) for e in events]
        if name == "figure13":
            path_orders.remove(tuple(e["path"] for e in events))
        expected_orders[name].remove(order)
        first, final = events[0], events[-1]
        if name in ("conflict", "atomic"):
            assert final["error"] and "conflict" in final["error"] and "K" in final["error"], record
            assert final["callbacks"] == final["forwarded"] == [first["incoming"]], record
            assert final["visible"] == first["incoming"], record
            assert not first["error"] and first["callbacks"] == first["forwarded"] == [first["incoming"]], record
        else:
            assert all(e["error"] is None for e in events), record
            expected = []
            visible = {}
            scopes = {}
            for e in events:
                values = scopes.setdefault(e["depth"], {})
                fresh = {k:v for k,v in e["incoming"].items() if k not in values}
                values.update(fresh)
                if fresh:
                    expected.append(fresh)
                for depth in sorted(scopes, reverse=True):
                    visible.update(scopes[depth])
                assert e["callbacks"] == e["forwarded"] == expected and e["visible"] == visible, record
    assert not any(expected_orders.values()) and not path_orders, expected_orders


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path)
    parser.add_argument("--original", action="store_true", help="Check the historical message-ID worker")
    parser.add_argument("records", type=Path)
    args = parser.parse_args()
    if args.repo:
        records = measure(args.repo)
        with args.records.open("x", encoding="utf-8") as stream:
            json.dump(records, stream, indent=2)
            stream.write("\n")
    else:
        records = json.loads(args.records.read_text(encoding="utf-8"))
    if args.original:
        from verify_scoped import check_original
        check_original(records)
    else:
        verify(records)
    print(f"Verified {len(records)} native receiver traces.")
