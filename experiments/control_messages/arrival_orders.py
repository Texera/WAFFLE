"""Replay each distinct placement of a fresh update at the Python merge worker."""
import argparse
import csv
from pathlib import Path
import sys

ARRIVAL_WIDTHS = (1, 2, 4, 8, 16, 32, 64, 128, 256, 512)


def run(repo, output):
    sys.path.insert(0, str(repo.resolve() / "amber" / "src" / "main" / "python"))
    from core.models import InternalQueue, State, StateFrame
    from core.models.internal_queue import DataElement
    from core.runnables import MainLoop
    from proto.org.apache.texera.amber.core import ChannelIdentity
    from pytexera import UDFOperatorV2

    class Receiver(UDFOperatorV2):
        def __init__(self):
            self.received = []

        def process_state(self, state, port):
            self.received.append(state["K"])
            return state

        def process_tuple(self, row, port):
            yield row

    inputs = InternalQueue()
    worker = MainLoop("merge-observer", inputs, InternalQueue())
    channel = ChannelIdentity(is_control=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["branches", "copies_before_update", "identity", "delivered_K",
                             "callback_K", "callbacks", "final_K"])
            for width in ARRIVAL_WIDTHS:
                for before in range(1, width + 1):
                    for identity in ("publication", "per_copy"):
                        receiver = Receiver()
                        worker.context.executor_manager.executor = receiver
                        # Use disjoint message IDs for independent traces in the same worker.
                        prefix = f"{width}:{before}:{identity}:"
                        originals = [(2, prefix + ("A" if identity == "publication" else f"A{i}"))
                                     for i in range(width)]
                        frames = originals[:before] + [(3, prefix + "B")] + originals[before:]
                        for value, name in frames:
                            frame = StateFrame(State({"K": value}), loop_start_id="loop",
                                               message_id=name)
                            inputs.put(DataElement(tag=channel, payload=frame))
                            worker._process_state_frame(inputs.get().payload)
                        delivered = [value for value, _ in frames]
                        expected = [2, 3] if identity == "publication" else delivered
                        assert receiver.received == expected
                        assert receiver.state["K"] == expected[-1]
                        writer.writerow([width, before, identity, " ".join(map(str, delivered)),
                                         " ".join(map(str, receiver.received)),
                                         len(receiver.received), receiver.state["K"]])
    finally:
        worker.data_processor.stop()
        condition = worker.context.tuple_processing_manager.context_switch_condition
        with condition:
            condition.notify_all()
        worker.stop()
        worker.context.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    run(args.repo, args.output)
