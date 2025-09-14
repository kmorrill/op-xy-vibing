from __future__ import annotations

from typing import Optional


class CoreSink:
    """Abstract sink interface used by Engine."""

    def note_on(self, channel: int, pitch: int, velocity: int) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def note_off(self, channel: int, pitch: int) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def panic(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def control_change(self, channel: int, control: int, value: int) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class MidoSink(CoreSink):
    def __init__(self, out_port, also_send_clock: bool = False):
        self.out = out_port
        self.also_send_clock = also_send_clock

    def note_on(self, channel: int, pitch: int, velocity: int) -> None:
        import mido

        self.out.send(mido.Message("note_on", note=int(pitch), velocity=int(velocity), channel=int(channel)))

    def note_off(self, channel: int, pitch: int) -> None:
        import mido

        self.out.send(mido.Message("note_off", note=int(pitch), velocity=0, channel=int(channel)))

    def panic(self) -> None:
        import mido

        # Send All Notes Off across all channels
        for ch in range(16):
            self.out.send(mido.Message("control_change", control=123, value=0, channel=ch))

    def control_change(self, channel: int, control: int, value: int) -> None:
        import mido

        self.out.send(mido.Message("control_change", control=int(control), value=int(max(0, min(127, value))), channel=int(channel)))


def open_mido_output(name_filter: Optional[str] = None):
    import mido

    if name_filter:
        for name in mido.get_output_names():
            if name_filter in name:
                return mido.open_output(name)
        raise RuntimeError(f"MIDI out port matching '{name_filter}' not found. Available: {mido.get_output_names()}")
    # Default: open the first available
    names = mido.get_output_names()
    if not names:
        raise RuntimeError("No MIDI output ports available")
    return mido.open_output(names[0])


def open_mido_input(name_filter: Optional[str] = None, callback=None):
    import mido

    if name_filter:
        for name in mido.get_input_names():
            if name_filter in name:
                return mido.open_input(name, callback=callback)
        raise RuntimeError(f"MIDI in port matching '{name_filter}' not found. Available: {mido.get_input_names()}")
    # Default: open the first available
    names = mido.get_input_names()
    if not names:
        raise RuntimeError("No MIDI input ports available")
    return mido.open_input(names[0], callback=callback)
