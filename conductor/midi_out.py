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
            # Sustain off
            self.out.send(mido.Message("control_change", control=64, value=0, channel=ch))
            # All Sound Off (120) then All Notes Off (123)
            self.out.send(mido.Message("control_change", control=120, value=0, channel=ch))
            self.out.send(mido.Message("control_change", control=123, value=0, channel=ch))

    def control_change(self, channel: int, control: int, value: int) -> None:
        import mido

        self.out.send(mido.Message("control_change", control=int(control), value=int(max(0, min(127, value))), channel=int(channel)))


def open_mido_output(name_filter: Optional[str] = None):
    """Open a Mido output port with safe fallbacks.

    - If mido/rtmidi are unavailable or the system MIDI stack is inaccessible,
      return a dummy object exposing `.send()`.
    - If a specific port is requested but not found, also fall back to dummy
      rather than crashing in headless CI environments.
    """
    def _dummy_out():
        class _DummyOut:
            def send(self, *_args, **_kwargs):
                pass
        return _DummyOut()

    try:
        import mido
    except Exception:
        return _dummy_out()

    try:
        if name_filter:
            try:
                for name in mido.get_output_names():
                    if name_filter in name:
                        return mido.open_output(name)
                # Requested filter not found: safe fallback
                return _dummy_out()
            except Exception:
                # Accessing system MIDI may raise in sandboxed environments
                return _dummy_out()
        # Default: open the first available
        try:
            names = mido.get_output_names()
        except Exception:
            return _dummy_out()
        if not names:
            return _dummy_out()
        try:
            return mido.open_output(names[0])
        except Exception:
            return _dummy_out()
    except Exception:
        return _dummy_out()


def open_mido_input(name_filter: Optional[str] = None, callback=None):
    """Open a Mido input port with safe fallbacks.

    Returns a dummy object with `.close()` when system MIDI is unavailable or
    access fails (e.g., CI, sandboxed runners).
    """
    def _dummy_in():
        class _DummyIn:
            def close(self):
                pass
        return _DummyIn()

    try:
        import mido
    except Exception:
        return _dummy_in()

    try:
        if name_filter:
            try:
                for name in mido.get_input_names():
                    if name_filter in name:
                        return mido.open_input(name, callback=callback)
                # Requested filter not found: safe fallback
                return _dummy_in()
            except Exception:
                return _dummy_in()
        # Default: open the first available
        try:
            names = mido.get_input_names()
        except Exception:
            return _dummy_in()
        if not names:
            return _dummy_in()
        try:
            return mido.open_input(names[0], callback=callback)
        except Exception:
            return _dummy_in()
    except Exception:
        return _dummy_in()
