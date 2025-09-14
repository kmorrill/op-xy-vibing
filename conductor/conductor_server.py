from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import tempfile
import threading
import time
from typing import Any, Dict, Optional, Set

from conductor.clock import InternalClock
from conductor.midi_engine import Engine
from conductor.midi_out import MidoSink, open_mido_output
from conductor.validator import validate_loop, canonicalize
from conductor.ws_server import start_ws_server
from conductor.patch_utils import apply_patch as apply_json_patch


def _atomic_write_json(path: str, obj: Dict[str, Any]) -> None:
    data = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    d = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(prefix=".tmp_loop_", dir=d, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


def _load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class Conductor:
    def __init__(self, loop_path: str, port_filter: Optional[str], bpm: float):
        self.loop_path = loop_path
        self.doc: Dict[str, Any] = _load_json(loop_path)
        self.doc_version = int(self.doc.get("docVersion", 0))
        self.out = open_mido_output(port_filter)
        self.sink = MidoSink(self.out, also_send_clock=True)
        self.engine = Engine(self.sink)
        self.engine.load(self.doc)
        self.playing = False
        self._lock = threading.Lock()

        def on_clock_pulse(_):
            # Adapt 24 PPQN -> meta.ppq
            meta = self.doc.get("meta", {})
            ppq = int(meta.get("ppq", 96))
            ratio = max(1, ppq // 24)
            for _ in range(ratio):
                self.engine.on_tick(self.engine.tick + 1)
                # Evaluate pending structural applies at bar boundary
                self._maybe_apply_pending()

        def send_midi_clock():
            import mido

            try:
                self.out.send(mido.Message("clock"))
            except Exception:
                pass

        # Pending structural doc replace (apply at next bar boundary)
        self._pending_doc: Optional[Dict[str, Any]] = None
        self.clock = InternalClock(bpm=bpm, tick_handler=on_clock_pulse, send_midi_clock=send_midi_clock)
        self.clock.start()

    # --- State/doc ---
    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            # Compute bar:beat:tick within current bar (4/4 assumed)
            meta = self.doc.get("meta", {})
            ppq = int(meta.get("ppq", 96))
            spb = int(meta.get("stepsPerBar", 16))
            step_ticks = int((ppq * 4) / spb) if spb > 0 else 0
            bar_ticks = step_ticks * spb if step_ticks > 0 else 0
            t = int(self.engine.tick)
            if bar_ticks > 0:
                tick_in_bar = t % bar_ticks
            else:
                tick_in_bar = 0
            # beat index (0..3) in 4/4, ticks per beat = ppq
            beat = (tick_in_bar // max(1, ppq)) % 4
            return {
                "transport": "playing" if self.playing else "stopped",
                "bpm": self.clock.bpm,
                "tick": t,
                "barBeatTick": {
                    "beat": int(beat),
                    "tickInBar": int(tick_in_bar),
                    "barTicks": int(bar_ticks),
                },
            }

    def get_doc(self) -> Dict[str, Any]:
        with self._lock:
            import hashlib, json

            canon_bytes = json.dumps(self.doc, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
            sha = hashlib.sha256(canon_bytes).hexdigest()
            return {"docVersion": self.doc_version, "json": self.doc, "sha256": sha}

    # --- Control ---
    def do_play(self) -> None:
        with self._lock:
            if not self.playing:
                self.engine.start()
                self.playing = True
                # Emit tick 0 (or current tick) immediately to avoid missing step-0 events
                try:
                    self.engine.on_tick(self.engine.tick)
                except Exception:
                    pass

    def do_continue(self) -> None:
        # Same as play for MVP; tick preserved
        self.do_play()

    def do_stop(self) -> None:
        with self._lock:
            if self.playing:
                self.engine.stop()  # flush offs + panic
                self.playing = False
                # best-effort MIDI stop message
                try:
                    import mido

                    self.out.send(mido.Message("stop"))
                except Exception:
                    pass

    def do_set_tempo(self, bpm: float) -> None:
        self.clock.set_bpm(bpm)

    def do_replace_json(self, base_version: int, new_doc: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            if base_version != self.doc_version:
                return {"ok": False, "error": "stale", "expected": self.doc_version}
            errors = validate_loop(new_doc)
            if errors:
                return {"ok": False, "error": "validation", "details": errors}
            canon = canonicalize(new_doc)
            # increment version and persist
            self.doc_version += 1
            canon["docVersion"] = self.doc_version
            _atomic_write_json(self.loop_path, canon)
            self.doc = canon
            self.engine.replace_doc(self.doc)
            return {"ok": True, "docVersion": self.doc_version}

    # --- Apply scheduling helpers ---
    def _is_structural_ops(self, ops: list) -> bool:
        structural_prefixes = ("/meta/", "/deviceProfile")
        track_structural_suffixes = (
            "/id",
            "/name",
            "/type",
            "/midiChannel",
            "/role",
            "/pattern/lengthBars",
            "/drumKit",
        )
        for op in ops:
            p = str(op.get("path", ""))
            if any(p.startswith(pref) for pref in structural_prefixes):
                return True
            if p.startswith("/tracks/"):
                parts = p.split("/")
                if len(parts) >= 4:
                    suffix = "/" + "/".join(parts[3:])
                    if any(suffix.startswith(s) for s in track_structural_suffixes):
                        return True
        return False

    def _schedule_or_apply(self, base_version: int, doc: Dict[str, Any], structural: bool, apply_now: bool = False) -> Dict[str, Any]:
        if apply_now or not structural or not self.playing:
            return self.do_replace_json(base_version, doc)
        # queue for next bar boundary
        with self._lock:
            self._pending_doc = doc
        return {"ok": True, "pending": True, "when": "next_bar", "docVersion": self.doc_version}

    def _maybe_apply_pending(self) -> None:
        if self._pending_doc is None:
            return
        # Apply at bar boundary (tick % bar_ticks == 0)
        meta = self.doc.get("meta", {})
        ppq = int(meta.get("ppq", 96))
        spb = int(meta.get("stepsPerBar", 16))
        step_ticks = int((ppq * 4) / spb) if spb > 0 else 0
        bar_ticks = step_ticks * spb if step_ticks > 0 else 0
        if bar_ticks <= 0 or (self.engine.tick % bar_ticks) == 0:
            with self._lock:
                nd = self._pending_doc
                self._pending_doc = None
            if isinstance(nd, dict):
                self.do_replace_json(self.doc_version, nd)


async def serve_ws(conductor: Conductor, host: str, port: int):
    try:
        import websockets  # type: ignore
    except Exception:
        print("[ws] websockets not installed; cannot start Conductor WS")
        return

    clients: Set[Any] = set()

    async def broadcast(obj: Dict[str, Any]):
        if not clients:
            return
        msg = json.dumps(obj)
        await asyncio.gather(*[c.send(msg) for c in list(clients)], return_exceptions=True)

    async def metrics_task():
        while True:
            await asyncio.sleep(1.0)
            try:
                await broadcast({
                    "type": "metrics",
                    "ts": time.time(),
                    "payload": {
                        "engine": conductor.engine.get_metrics(),
                        "clock": conductor.clock.get_metrics(),
                    },
                })
                await broadcast({"type": "state", "ts": time.time(), "payload": conductor.get_state()})
            except Exception:
                pass

    async def handler(ws, *args):
        clients.add(ws)
        # Send initial doc/state
        await ws.send(json.dumps({"type": "doc", "ts": time.time(), "payload": conductor.get_doc()}))
        await ws.send(json.dumps({"type": "state", "ts": time.time(), "payload": conductor.get_state()}))
        try:
            async for message in ws:
                try:
                    obj = json.loads(message)
                except Exception:
                    continue
                t = obj.get("type")
                if t == "play":
                    conductor.do_play()
                elif t == "stop":
                    conductor.do_stop()
                elif t == "continue":
                    conductor.do_continue()
                elif t == "setTempo":
                    bpm = float(obj.get("bpm", conductor.clock.bpm))
                    conductor.do_set_tempo(bpm)
                elif t == "replaceJSON":
                    payload = obj.get("payload", {})
                    base = int(payload.get("baseVersion", -1))
                    new_doc = payload.get("doc")
                    apply_now = bool(payload.get("applyNow", False))
                    if isinstance(new_doc, dict):
                        # Determine structural by comparing key fields
                        res = conductor._schedule_or_apply(base, new_doc, structural=True, apply_now=apply_now)
                        await ws.send(json.dumps({"type": "doc", "ts": time.time(), "payload": conductor.get_doc()}))
                        await ws.send(json.dumps({"type": "error", "ts": time.time(), "payload": res}) if not res.get("ok") else json.dumps({"type": "ack", "ts": time.time(), "payload": res}))
                elif t == "applyPatch":
                    payload = obj.get("payload", {})
                    base = int(payload.get("baseVersion", -1))
                    ops = payload.get("ops")
                    apply_now = bool(payload.get("applyNow", False))
                    if not isinstance(ops, list):
                        await ws.send(json.dumps({"type": "error", "ts": time.time(), "payload": {"ok": False, "error": "invalid_ops"}}))
                    else:
                        with conductor._lock:
                            if base != conductor.doc_version:
                                await ws.send(json.dumps({"type": "error", "ts": time.time(), "payload": {"ok": False, "error": "stale", "expected": conductor.doc_version}}))
                            else:
                                try:
                                    patched = apply_json_patch(conductor.doc, ops)
                                except Exception as e:
                                    await ws.send(json.dumps({"type": "error", "ts": time.time(), "payload": {"ok": False, "error": "patch_apply", "details": str(e)}}))
                                    patched = None
                                if isinstance(patched, dict):
                                    structural = conductor._is_structural_ops(ops)
                                    res = conductor._schedule_or_apply(conductor.doc_version, patched, structural=structural, apply_now=apply_now)
                                    if res.get("ok"):
                                        await ws.send(json.dumps({"type": "doc", "ts": time.time(), "payload": conductor.get_doc()}))
                                    else:
                                        await ws.send(json.dumps({"type": "error", "ts": time.time(), "payload": res}))
                # broadcast updated state after commands
                await ws.send(json.dumps({"type": "state", "ts": time.time(), "payload": conductor.get_state()}))
        finally:
            clients.discard(ws)

    async def main():
        async with websockets.serve(handler, host, port):
            print(f"[ws] Conductor listening on ws://{host}:{port}")
            asyncio.create_task(metrics_task())
            await asyncio.Future()

    await main()


def main():
    ap = argparse.ArgumentParser(description="Conductor WS server (doc/state/metrics + transport)")
    ap.add_argument("--loop", default="loop.json")
    ap.add_argument("--port", help="Substring to match MIDI port (e.g., 'OP-XY')")
    ap.add_argument("--bpm", type=float, default=120.0)
    ap.add_argument("--ws-host", default="127.0.0.1")
    ap.add_argument("--ws-port", type=int, default=8765)
    args = ap.parse_args()

    conductor = Conductor(args.loop, args.port, args.bpm)

    def shutdown(*_):
        try:
            conductor.do_stop()
        except Exception:
            pass
        print("[ws] shutting down")
        os._exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        asyncio.run(serve_ws(conductor, args.ws_host, args.ws_port))
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
