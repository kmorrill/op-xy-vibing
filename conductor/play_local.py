from __future__ import annotations

import argparse
import json
import signal
import sys
import threading
from typing import Optional

from conductor.midi_engine import Engine
from conductor.midi_out import MidoSink, open_mido_output, open_mido_input
from conductor.clock import InternalClock


def load_loop(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_internal(loop_path: str, port_filter: Optional[str], bpm: float):
    import mido

    loop = load_loop(loop_path)
    out = open_mido_output(port_filter)
    sink = MidoSink(out, also_send_clock=True)
    eng = Engine(sink)
    eng.load(loop)

    # Prepare clock adapter: convert 24 PPQN pulses into eng.meta.ppq ticks
    meta = loop.get("meta", {})
    ppq = int(meta.get("ppq", 96))
    ratio = max(1, ppq // 24)

    # Send Start and begin
    out.send(mido.Message("start"))
    eng.start()

    def on_clock_pulse(_pulses: int):
        # For each incoming 24-PPQN clock pulse, advance engine by `ratio` ticks
        for _ in range(ratio):
            eng.on_tick(eng.tick + 1)

    def send_midi_clock():
        out.send(mido.Message("clock"))

    clk = InternalClock(bpm=bpm, tick_handler=on_clock_pulse, send_midi_clock=send_midi_clock)

    def shutdown(*_):
        clk.stop()
        eng.stop()
        out.send(mido.Message("stop"))
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    clk.start()
    threading.Event().wait()  # sleep forever


def run_external(loop_path: str, port_filter: Optional[str]):
    import mido

    loop = load_loop(loop_path)
    out = open_mido_output(port_filter)
    sink = MidoSink(out)
    eng = Engine(sink)
    eng.load(loop)
    meta = loop.get("meta", {})
    ppq = int(meta.get("ppq", 96))
    ratio = max(1, ppq // 24)

    def on_input(msg):
        try:
            if msg.type == "start":
                eng.start()
            elif msg.type == "continue":
                eng.start()  # same as start for MVP
            elif msg.type == "stop":
                eng.stop()
            elif msg.type == "songpos":
                # Optional SPP reposition: pos is in 1/16 notes; 1 pos = 6 MIDI clocks.
                # We reposition engine tick accordingly (approximate mapping):
                # engine_tick ~= pos * (ppq / 4)
                eng.tick = int(msg.pos * (ppq / 4))
            elif msg.type == "clock":
                for _ in range(ratio):
                    eng.on_tick(eng.tick + 1)
        except Exception:
            pass

    inp = open_mido_input(port_filter, callback=on_input)

    def shutdown(*_):
        eng.stop()
        try:
            out.send(mido.Message("stop"))
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    # Run forever; callbacks drive the engine
    signal.pause()


def main():
    ap = argparse.ArgumentParser(description="Play an opxyloop-1.0 JSON to OP-XY via MIDI")
    ap.add_argument("loop", nargs="?", default="loop.json", help="Path to loop JSON (default: loop.json)")
    ap.add_argument("--port", help="Substring to match MIDI port (e.g., 'OP-XY')")
    ap.add_argument("--mode", choices=["internal", "external"], default="internal", help="Clock mode: internal or external (OP-XY master)")
    ap.add_argument("--bpm", type=float, default=120.0, help="BPM when using internal mode")
    args = ap.parse_args()

    if args.mode == "internal":
        run_internal(args.loop, args.port, args.bpm)
    else:
        run_external(args.loop, args.port)


if __name__ == "__main__":
    main()

