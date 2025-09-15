from __future__ import annotations

import asyncio
import json
import contextlib
import os
import socket
from pathlib import Path

import pytest

from conductor.conductor_server import Conductor, serve_ws


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    addr, port = s.getsockname()
    s.close()
    return port


async def _connect(url: str):
    import websockets  # type: ignore

    for _ in range(50):  # retry for up to ~2.5s while server boots
        try:
            return await websockets.connect(url)
        except Exception:
            await asyncio.sleep(0.05)
    raise RuntimeError("failed to connect to WS server")


async def _recv_until(ws, want_types: set[str], timeout: float = 2.0):
    msgs = []
    deadline = asyncio.get_event_loop().time() + timeout
    seen = set()
    while asyncio.get_event_loop().time() < deadline:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=deadline - asyncio.get_event_loop().time())
        except asyncio.TimeoutError:
            break
        obj = json.loads(raw)
        msgs.append(obj)
        t = obj.get("type")
        if t:
            seen.add(t)
        if want_types.issubset(seen):
            break
    return msgs


@pytest.mark.asyncio
async def test_ws_roundtrip_sequential_patches(tmp_path: Path):
    loop_path = tmp_path / "loop.json"
    # Provide an initial minimal loop on disk (server no longer defaults)
    (tmp_path).mkdir(parents=True, exist_ok=True)
    init = {
        "version": "opxyloop-1.0",
        "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
        "tracks": [
            {"id": "t1", "name": "Track 1", "type": "sampler", "midiChannel": 0, "pattern": {"lengthBars": 1, "steps": []}}
        ],
        "docVersion": 0,
    }
    loop_path.write_text(json.dumps(init))
    # Start conductor with external clock (no internal tick thread needed)
    c = Conductor(str(loop_path), port_filter=None, bpm=120.0, clock_source="external")
    ws_port = _free_port()
    server_task = asyncio.create_task(serve_ws(c, "127.0.0.1", ws_port))
    try:
        ws = await _connect(f"ws://127.0.0.1:{ws_port}")
        try:
            # Drain initial hello/doc/state
            await _recv_until(ws, {"doc", "state"}, timeout=3.0)
            # Add first step
            doc = c.get_doc()
            base = int(doc.get("docVersion", 0))
            step1 = {"idx": 2, "events": [{"pitch": 60, "velocity": 100, "lengthSteps": 1}]}
            msg1 = {"type": "applyPatch", "id": 1, "payload": {"baseVersion": base, "ops": [{"op": "add", "path": "/tracks/0/pattern/steps/-", "value": step1}], "applyNow": False}}
            await ws.send(json.dumps(msg1))
            # Expect doc + ack
            msgs = await _recv_until(ws, {"doc", "ack"}, timeout=3.0)
            # Confirm file on disk updated
            on_disk = json.loads(Path(loop_path).read_text())
            steps = on_disk["tracks"][0]["pattern"]["steps"]
            assert any(s.get("idx") == 2 for s in steps)
            v1 = int(on_disk.get("docVersion", 0))
            assert v1 >= base + 1

            # Add second step, now base should be latest
            doc2 = c.get_doc()
            base2 = int(doc2.get("docVersion", 0))
            step2 = {"idx": 5, "events": [{"pitch": 60, "velocity": 100, "lengthSteps": 1}]}
            msg2 = {"type": "applyPatch", "id": 2, "payload": {"baseVersion": base2, "ops": [{"op": "add", "path": "/tracks/0/pattern/steps/-", "value": step2}], "applyNow": False}}
            await ws.send(json.dumps(msg2))
            msgs2 = await _recv_until(ws, {"doc", "ack"}, timeout=3.0)
            on_disk2 = json.loads(Path(loop_path).read_text())
            steps2 = on_disk2["tracks"][0]["pattern"]["steps"]
            assert any(s.get("idx") == 2 for s in steps2) and any(s.get("idx") == 5 for s in steps2)
            v2 = int(on_disk2.get("docVersion", 0))
            assert v2 >= v1 + 1
        finally:
            await ws.close()
    finally:
        server_task.cancel()
        with contextlib.suppress(Exception):
            await server_task


@pytest.mark.asyncio
async def test_ws_stale_error_on_back_to_back_without_ack(tmp_path: Path):
    import contextlib
    loop_path = tmp_path / "loop.json"
    init = {
        "version": "opxyloop-1.0",
        "meta": {"tempo": 120, "ppq": 96, "stepsPerBar": 16},
        "tracks": [
            {"id": "t1", "name": "Track 1", "type": "sampler", "midiChannel": 0, "pattern": {"lengthBars": 1, "steps": []}}
        ],
        "docVersion": 0,
    }
    loop_path.write_text(json.dumps(init))
    c = Conductor(str(loop_path), port_filter=None, bpm=120.0, clock_source="external")
    ws_port = _free_port()
    server_task = asyncio.create_task(serve_ws(c, "127.0.0.1", ws_port))
    try:
        ws = await _connect(f"ws://127.0.0.1:{ws_port}")
        try:
            await _recv_until(ws, {"doc", "state"}, timeout=3.0)
            base = int(c.get_doc().get("docVersion", 0))
            stepA = {"idx": 1, "events": [{"pitch": 60, "velocity": 100, "lengthSteps": 1}]}
            stepB = {"idx": 3, "events": [{"pitch": 60, "velocity": 100, "lengthSteps": 1}]}
            m1 = {"type": "applyPatch", "id": 10, "payload": {"baseVersion": base, "ops": [{"op": "add", "path": "/tracks/0/pattern/steps/-", "value": stepA}], "applyNow": False}}
            m2 = {"type": "applyPatch", "id": 11, "payload": {"baseVersion": base, "ops": [{"op": "add", "path": "/tracks/0/pattern/steps/-", "value": stepB}], "applyNow": False}}
            # Send back-to-back without waiting for doc
            await ws.send(json.dumps(m1))
            await ws.send(json.dumps(m2))
            # Expect to see an error with 'stale' for the second
            saw_stale = False
            for _ in range(8):
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=3.0)
                except asyncio.TimeoutError:
                    break
                obj = json.loads(raw)
                if obj.get("type") == "error" and (obj.get("payload") or {}).get("error") == "stale":
                    saw_stale = True
                    break
            assert saw_stale, "expected a stale error for back-to-back patches without ack"
        finally:
            await ws.close()
    finally:
        server_task.cancel()
        with contextlib.suppress(Exception):
            await server_task
