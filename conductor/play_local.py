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


def run_internal(loop_path: str, port_filter: Optional[str], bpm: float, loops: Optional[int] = None):
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
    spb = int(meta.get("stepsPerBar", 16))
    step_ticks = int((ppq * 4) / spb) if spb > 0 else 0
    bar_ticks = step_ticks * spb if step_ticks > 0 else 0

    # Determine overall loop length in bars (max across tracks)
    total_bars = 1
    try:
        tracks = loop.get("tracks", [])
        total_bars = max(1, max(int(t.get("pattern", {}).get("lengthBars", 1)) for t in tracks) if tracks else 1)
    except Exception:
        total_bars = 1

    # If loops specified, compute stop_at_tick after N full cycles
    stop_at_tick: Optional[int] = None
    if loops and loops > 0 and bar_ticks > 0:
        stop_at_tick = total_bars * bar_ticks * int(loops)

    # Send Start and begin
    out.send(mido.Message("start"))
    eng.start()

    done = threading.Event()

    def on_clock_pulse(_pulses: int):
        # For each incoming 24-PPQN clock pulse, advance engine by `ratio` ticks
        nonlocal stop_at_tick
        for _ in range(ratio):
            next_tick = eng.tick + 1
            eng.on_tick(next_tick)
            if stop_at_tick is not None and next_tick >= stop_at_tick:
                # Stop cleanly after requested loops
                try:
                    clk.stop()
                except Exception:
                    pass
                try:
                    eng.stop()
                    out.send(mido.Message("stop"))
                except Exception:
                    pass
                done.set()
                return

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
    # Wait until requested loops complete or until interrupted
    if stop_at_tick is not None:
        done.wait()
    else:
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
    ap.add_argument("--loops", type=int, default=0, help="Number of full loop cycles to play (internal mode). 0 = infinite")
    args = ap.parse_args()

    if args.mode == "internal":
        run_internal(args.loop, args.port, args.bpm, loops=(args.loops if args.loops and args.loops > 0 else None))
    else:
        run_external(args.loop, args.port)


if __name__ == "__main__":
    main()
