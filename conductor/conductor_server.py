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
from conductor.midi_out import MidoSink, open_mido_output, open_mido_input
from conductor.validator import validate_loop, canonicalize
from conductor.patch_utils import apply_patch as apply_json_patch
from conductor.tempo_map import bpm_to_cc80


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


"""Conductor server for OP-XY loops.

This module intentionally does not embed a default loop JSON. The loop file
should be provided on disk (e.g., loop.json in repo). If missing, loading
will raise FileNotFoundError.
"""


def _load_json(path: str) -> Dict[str, Any]:
    # Ensure parent dir exists
    d = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(d, exist_ok=True)
    if not os.path.exists(path):
        raise FileNotFoundError(f"loop file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class Conductor:
    def __init__(self, loop_path: str, port_filter: Optional[str], bpm: float, clock_source: str = "internal"):
        self.loop_path = loop_path
        self.doc: Dict[str, Any] = _load_json(loop_path)
        self.doc_version = int(self.doc.get("docVersion", 0))
        # Track file mtime to detect external edits
        try:
            self._file_mtime = os.path.getmtime(self.loop_path)
        except Exception:
            self._file_mtime = time.time()
        self._port_filter = port_filter
        try:
            self.out = open_mido_output(port_filter)
        except Exception:
            self.out = open_mido_output(None)
        self.clock_source = clock_source if clock_source in ("internal", "external") else "internal"
        # Never send MIDI Clock out; device remains master. Only send CC80 for tempo nudges.
        self.sink = MidoSink(self.out, also_send_clock=False)
        self.engine = Engine(self.sink)
        self.engine.load(self.doc)
        self.playing = False
        # Use reentrant lock: WS handler holds the lock and calls methods
        # that also acquire it (e.g., do_replace_json via _schedule_or_apply).
        # A non-reentrant Lock deadlocks in that path.
        self._lock = threading.RLock()
        # External BPM estimation (when clock_source == 'external')
        self._ext_last_ts: Optional[float] = None
        self._ext_interval_ema: Optional[float] = None
        self._ext_bpm: float = float(self.doc.get("meta", {}).get("tempo", 120))
        # External transport heuristics
        self._last_spp_ts: Optional[float] = None

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
            # Intentionally no-op: do not send MIDI clock to device
            return

        # Pending structural doc replace (apply at next bar boundary)
        self._pending_doc: Optional[Dict[str, Any]] = None
        self.clock: Optional[InternalClock] = None
        self.inp = None
        if self.clock_source == "internal":
            self.clock = InternalClock(bpm=bpm, tick_handler=on_clock_pulse, send_midi_clock=send_midi_clock)
            self.clock.start()
        else:
            # External clock: listen for transport + MIDI clock on input
            def on_input(msg):
                try:
                    # Debug (suppress high-frequency clock spam)
                    try:
                        if getattr(msg, 'type', None) != 'clock':
                            print(f"[midi-in] {msg}", flush=True)
                    except Exception:
                        pass
                    if msg.type == "start":
                        # Start from bar 0 unless SPP arrives
                        try:
                            self.engine.tick = 0
                        except Exception:
                            pass
                        self.do_play()
                    elif msg.type == "continue":
                        self.do_continue()
                    elif msg.type == "stop":
                        self.do_stop()
                    elif msg.type == "songpos":
                        meta = self.doc.get("meta", {})
                        ppq = int(meta.get("ppq", 96))
                        self.engine.tick = int(msg.pos * (ppq / 4))
                        self._last_spp_ts = time.time()
                    elif msg.type == "clock":
                        now = time.time()
                        if self._ext_last_ts is not None:
                            dt = max(1e-6, now - self._ext_last_ts)
                            # EMA for clock pulse interval
                            self._ext_interval_ema = dt if self._ext_interval_ema is None else (0.85 * self._ext_interval_ema + 0.15 * dt)
                            self._ext_bpm = float(60.0 / (max(1e-6, self._ext_interval_ema) * 24.0))
                        self._ext_last_ts = now
                        meta = self.doc.get("meta", {})
                        ppq = int(meta.get("ppq", 96))
                        ratio = max(1, ppq // 24)
                        # If device sent SPP very recently but no Start/Continue observed (attach mid-play), arm playback
                        if not self.playing and self._last_spp_ts and (now - self._last_spp_ts) < 1.0:
                            try:
                                print("[midi-in] inferred-continue after SPP", flush=True)
                                self.do_continue()
                            except Exception:
                                pass
                        # Only advance engine ticks while playing
                        if self.playing:
                            for _ in range(ratio):
                                self.engine.on_tick(self.engine.tick + 1)
                                self._maybe_apply_pending()
                except Exception:
                    pass
            try:
                self.inp = open_mido_input(port_filter, callback=on_input)
            except Exception:
                self.inp = None
                def _retry_in():
                    while self.inp is None:
                        try:
                            self.inp = open_mido_input(self._port_filter, callback=on_input)
                            break
                        except Exception:
                            time.sleep(1.5)
                threading.Thread(target=_retry_in, daemon=True).start()

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
                "bpm": (self.clock.bpm if self.clock_source == "internal" and self.clock else self._ext_bpm),
                "tick": t,
                "clockSource": self.clock_source,
                "barBeatTick": {
                    "beat": int(beat),
                    "tickInBar": int(tick_in_bar),
                    "barTicks": int(bar_ticks),
                },
                "ccNow": self.engine.get_cc_snapshot(),
                "activeNotes": self.engine.get_active_notes_snapshot(),
            }

    def get_doc(self) -> Dict[str, Any]:
        with self._lock:
            import hashlib, json

            canon_bytes = json.dumps(self.doc, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
            sha = hashlib.sha256(canon_bytes).hexdigest()
            return {"docVersion": self.doc_version, "json": self.doc, "sha256": sha, "path": os.path.abspath(self.loop_path)}

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
                # Do not send MIDI transport; device is transport authority

    def do_set_tempo(self, bpm: float) -> None:
        if self.clock and self.clock_source == "internal":
            self.clock.set_bpm(bpm)

    def do_set_tempo_cc(self, bpm: float) -> None:
        """Set device tempo via CC80 on channel 0 using a 40..220 BPM scale.

        Mapping: 0..127 -> 40..220 BPM. Clamped. Does not change clock source.
        """
        try:
            import mido
            # Scale bpm to 0..127
            val = bpm_to_cc80(float(bpm))
            # Send on channel 0
            self.out.send(mido.Message("control_change", control=80, value=val, channel=0))
            # Nudge external BPM estimator toward requested value for UI continuity
            self._ext_bpm = float(max(40.0, min(220.0, float(bpm))))
        except Exception:
            pass

    def do_set_clock_source(self, source: str) -> None:
        source = source if source in ("internal", "external") else self.clock_source
        if source == self.clock_source:
            return
        # Tear down existing clock/input
        if self.clock:
            try:
                self.clock.stop()
            except Exception:
                pass
            self.clock = None
        if self.inp:
            try:
                self.inp.close()
            except Exception:
                pass
            self.inp = None
        self.clock_source = source
        # Update sink for MIDI clock sending behavior
        # Never send clock regardless of source
        self.sink.also_send_clock = False
        # Recreate clock or input
        if self.clock_source == "internal":
            def on_clock_pulse(_):
                meta = self.doc.get("meta", {})
                ppq = int(meta.get("ppq", 96))
                ratio = max(1, ppq // 24)
                for _ in range(ratio):
                    self.engine.on_tick(self.engine.tick + 1)
                    self._maybe_apply_pending()
            def send_midi_clock():
                return
            self.clock = InternalClock(bpm=float(self.doc.get("meta",{}).get("tempo", 120)), tick_handler=on_clock_pulse, send_midi_clock=send_midi_clock)
            self.clock.start()
            self._ext_last_ts = None; self._ext_interval_ema = None
        else:
            def on_input(msg):
                try:
                    if msg.type == "start":
                        self.do_play()
                    elif msg.type == "continue":
                        self.do_continue()
                    elif msg.type == "stop":
                        self.do_stop()
                    elif msg.type == "songpos":
                        meta = self.doc.get("meta", {})
                        ppq = int(meta.get("ppq", 96))
                        self.engine.tick = int(msg.pos * (ppq / 4))
                    elif msg.type == "clock":
                        now = time.time()
                        if self._ext_last_ts is not None:
                            dt = max(1e-6, now - self._ext_last_ts)
                            self._ext_interval_ema = dt if self._ext_interval_ema is None else (0.85 * self._ext_interval_ema + 0.15 * dt)
                            self._ext_bpm = float(60.0 / (max(1e-6, self._ext_interval_ema) * 24.0))
                        self._ext_last_ts = now
                        meta = self.doc.get("meta", {})
                        ppq = int(meta.get("ppq", 96))
                        ratio = max(1, ppq // 24)
                        for _ in range(ratio):
                            self.engine.on_tick(self.engine.tick + 1)
                            self._maybe_apply_pending()
                except Exception:
                    pass
            self._ext_last_ts = None; self._ext_interval_ema = None
            self.inp = open_mido_input(self._port_filter, callback=on_input)

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
            try:
                print(f"[ws] saved {self.loop_path} (docVersion={self.doc_version})", flush=True)
            except Exception:
                pass
            try:
                self._file_mtime = os.path.getmtime(self.loop_path)
            except Exception:
                self._file_mtime = time.time()
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

    last_doc_version = conductor.doc_version
    async def metrics_task():
        nonlocal last_doc_version
        while True:
            await asyncio.sleep(0.5)
            # Broadcast metrics (tolerate missing internal clock)
            try:
                clock_metrics = conductor.clock.get_metrics() if getattr(conductor, 'clock', None) else {"externalBpm": getattr(conductor, '_ext_bpm', None)}
                await broadcast({
                    "type": "metrics",
                    "ts": time.time(),
                    "payload": {
                        "engine": conductor.engine.get_metrics(),
                        "clock": clock_metrics,
                        "ws": {"clients": len(clients)},
                    },
                })
            except Exception:
                pass
            # Broadcast state separately so a metrics error doesn't block state updates
            try:
                await broadcast({"type": "state", "ts": time.time(), "payload": conductor.get_state()})
            except Exception:
                pass
            # Detect external file edits and broadcast updated doc
            try:
                m = os.path.getmtime(conductor.loop_path)
            except Exception:
                m = None
            if m and m != getattr(conductor, '_file_mtime', None):
                try:
                    loaded = _load_json(conductor.loop_path)
                    # Compare canonical JSONs
                    old_canon = json.dumps(conductor.doc, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    new_canon = json.dumps(loaded, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    import hashlib
                    if hashlib.sha256(old_canon).hexdigest() != hashlib.sha256(new_canon).hexdigest():
                        with conductor._lock:
                            errs = validate_loop(loaded)
                            if not errs:
                                canon = canonicalize(loaded)
                                conductor.doc_version = int(canon.get("docVersion", conductor.doc_version)) + 1
                                canon["docVersion"] = conductor.doc_version
                                conductor.doc = canon
                                conductor.engine.replace_doc(conductor.doc)
                        await broadcast({"type": "doc", "ts": time.time(), "payload": conductor.get_doc()})
                except Exception:
                    pass
                conductor._file_mtime = m
            # Broadcast doc on version change (captures scheduled applies)
            if conductor.doc_version != last_doc_version:
                last_doc_version = conductor.doc_version
                try:
                    await broadcast({"type": "doc", "ts": time.time(), "payload": conductor.get_doc()})
                except Exception:
                    pass

    async def handler(ws, *maybe_path):
        # Log client connection (helps debug UI connect issues)
        try:
            ra = getattr(ws, 'remote_address', None)
            print(f"[ws] client connected: {ra}", flush=True)
        except Exception:
            pass
        clients.add(ws)
        # Send initial hello/doc/state
        await ws.send(json.dumps({"type": "hello", "ts": time.time(), "payload": {"protocol": 1, "docVersion": conductor.doc_version}}))
        await ws.send(json.dumps({"type": "doc", "ts": time.time(), "payload": conductor.get_doc()}))
        await ws.send(json.dumps({"type": "state", "ts": time.time(), "payload": conductor.get_state()}))
        try:
            async for message in ws:
                try:
                    obj = json.loads(message)
                except Exception:
                    continue
                t = obj.get("type")
                req_id = obj.get("id")
                # Debug log incoming command types
                try:
                    print(f"[ws] recv type={t}", flush=True)
                except Exception:
                    pass
                if t == "play" or t == "stop" or t == "continue":
                    # Transport is device-controlled; ignore UI transport commands
                    await ws.send(json.dumps({"type": "error", "ts": time.time(), "id": req_id, "payload": {"ok": False, "error": "transport_external_only"}}))
                
                elif t == "subscribe":
                    await ws.send(json.dumps({"type": "ack", "ts": time.time(), "id": req_id, "payload": {"ok": True, "subscribed": True}}))
                elif t == "ping":
                    await ws.send(json.dumps({"type": "pong", "ts": time.time(), "id": req_id}))
                elif t == "setTempo":
                    bpm = float(obj.get("bpm", conductor.clock.bpm))
                    conductor.do_set_tempo(bpm)
                    await ws.send(json.dumps({"type": "ack", "ts": time.time(), "id": req_id, "payload": {"ok": True}}))
                elif t == "setClockSource":
                    src = obj.get("source", "internal")
                    conductor.do_set_clock_source(str(src))
                    await ws.send(json.dumps({"type": "ack", "ts": time.time(), "id": req_id, "payload": {"ok": True}}))
                elif t == "setTempoCC":
                    bpm = float(obj.get("bpm", 0))
                    conductor.do_set_tempo_cc(bpm)
                    await ws.send(json.dumps({"type": "ack", "ts": time.time(), "id": req_id, "payload": {"ok": True}}))
                elif t == "getState":
                    # Explicit poll for current state (UI fallback)
                    await ws.send(json.dumps({"type": "state", "ts": time.time(), "payload": conductor.get_state()}))
                elif t == "getDoc":
                    await ws.send(json.dumps({"type": "doc", "ts": time.time(), "id": req_id, "payload": conductor.get_doc()}))
                elif t == "replaceJSON":
                    payload = obj.get("payload", {})
                    base = int(payload.get("baseVersion", -1))
                    new_doc = payload.get("doc")
                    apply_now = bool(payload.get("applyNow", False))
                    if isinstance(new_doc, dict):
                        # Determine structural by comparing key fields
                        res = conductor._schedule_or_apply(base, new_doc, structural=True, apply_now=apply_now)
                        await ws.send(json.dumps({"type": "doc", "ts": time.time(), "payload": conductor.get_doc()}))
                        await ws.send(json.dumps({"type": "error", "ts": time.time(), "id": req_id, "payload": res}) if not res.get("ok") else json.dumps({"type": "ack", "ts": time.time(), "id": req_id, "payload": res}))
                elif t == "applyPatch":
                    try:
                        payload = obj.get("payload", {})
                        base = int(payload.get("baseVersion", -1))
                        ops = payload.get("ops")
                        apply_now = bool(payload.get("applyNow", False))
                        print(f"[ws] applyPatch base={base} ops={ops} apply_now={apply_now}")
                        if not isinstance(ops, list):
                            await ws.send(json.dumps({"type": "error", "ts": time.time(), "id": req_id, "payload": {"ok": False, "error": "invalid_ops"}}))
                        else:
                            with conductor._lock:
                                if base != conductor.doc_version:
                                    print(f"[ws] stale patch: client={base} server={conductor.doc_version}")
                                    await ws.send(json.dumps({"type": "error", "ts": time.time(), "id": req_id, "payload": {"ok": False, "error": "stale", "expected": conductor.doc_version}}))
                                else:
                                    try:
                                        patched = apply_json_patch(conductor.doc, ops)
                                    except Exception as e:
                                        print(f"[ws] patch_apply error: {e}")
                                        await ws.send(json.dumps({"type": "error", "ts": time.time(), "id": req_id, "payload": {"ok": False, "error": "patch_apply", "details": str(e)}}))
                                        patched = None
                                    if isinstance(patched, dict):
                                        structural = conductor._is_structural_ops(ops)
                                        print(f"[ws] structural={structural}")
                                        res = conductor._schedule_or_apply(conductor.doc_version, patched, structural=structural, apply_now=apply_now)
                                        print(f"[ws] apply result: {res}")
                                        if res.get("ok"):
                                            print(f"[ws] patch applied ok; new docVersion={conductor.doc_version}")
                                            await ws.send(json.dumps({"type": "doc", "ts": time.time(), "payload": conductor.get_doc()}))
                                            await ws.send(json.dumps({"type": "ack", "ts": time.time(), "id": req_id, "payload": res}))
                                        else:
                                            print(f"[ws] patch error response: {res}")
                                            await ws.send(json.dumps({"type": "error", "ts": time.time(), "id": req_id, "payload": res}))
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        try:
                            await ws.send(json.dumps({"type": "error", "ts": time.time(), "id": req_id, "payload": {"ok": False, "error": "exception", "details": str(e)}}))
                        except Exception:
                            pass
                # broadcast updated state after commands (except explicit getState which already responded)
                if t != "getState":
                    await ws.send(json.dumps({"type": "state", "ts": time.time(), "payload": conductor.get_state()}))
        finally:
            clients.discard(ws)

    async def main():
        async with websockets.serve(handler, host, port):
            print(f"[ws] Conductor listening on ws://{host}:{port}", flush=True)
            asyncio.create_task(metrics_task())
            await asyncio.Future()

    await main()


def main():
    ap = argparse.ArgumentParser(description="Conductor WS server (doc/state/metrics + transport)")
    ap.add_argument("--loop", default="loop.json")
    ap.add_argument("--port", help="Substring to match MIDI port (e.g., 'OP-XY')")
    ap.add_argument("--bpm", type=float, default=120.0)
    ap.add_argument("--clock-source", choices=["internal","external"], default="external")
    ap.add_argument("--ws-host", default="127.0.0.1")
    ap.add_argument("--ws-port", type=int, default=8765)
    ap.add_argument("--http-port", type=int, default=8080)
    args = ap.parse_args()

    conductor = Conductor(args.loop, args.port, args.bpm, clock_source=args.clock_source)

    def shutdown(*_):
        try:
            conductor.do_stop()
        except Exception:
            pass
        print("[ws] shutting down")
        os._exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Serve static UI in-process on 127.0.0.1
    def start_http_server():
        import http.server, socketserver
        from pathlib import Path
        ui_dir = Path(__file__).resolve().parent.parent / 'ui'
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=str(ui_dir), **kw)
        try:
            httpd = socketserver.TCPServer(("127.0.0.1", args.http_port), Handler)
        except OSError as e:
            print(f"[http] could not bind 127.0.0.1:{args.http_port}: {e}; continuing without HTTP")
            return
        with httpd:
            print(f"[http] serving UI on http://127.0.0.1:{args.http_port}")
            try:
                httpd.serve_forever()
            except Exception:
                pass
    threading.Thread(target=start_http_server, daemon=True).start()

    # Always force bind to localhost to avoid external exposure
    host = "127.0.0.1"
    try:
        asyncio.run(serve_ws(conductor, host, args.ws_port))
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
