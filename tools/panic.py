from __future__ import annotations

import argparse

from conductor.midi_out import open_mido_output, MidoSink


def main():
    ap = argparse.ArgumentParser(description="Send All Notes Off / All Sound Off to device")
    ap.add_argument("--port", required=True, help="Substring to match MIDI port (e.g., 'OP-XY')")
    args = ap.parse_args()
    out = open_mido_output(args.port)
    MidoSink(out).panic()
    print("panic sent (CC64/120/123)")


if __name__ == "__main__":
    main()

