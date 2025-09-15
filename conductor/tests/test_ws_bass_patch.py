from __future__ import annotations

import asyncio
import json
import socket
import contextlib
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
    for _ in range(50):
        try:
            return await websockets.connect(url)
        except Exception:
            await asyncio.sleep(0.05)
    raise RuntimeError("failed to connect to WS server")


@pytest.mark.asyncio
async def test_ws_add_and_replace_bass_step(tmp_path: Path):
    # Seed a loop with drumkit + empty bass steps
    loop_path = tmp_path / "loop.json"
    init = {
        "version": "opxyloop-1.0",
        "meta": {"tempo": 100, "ppq": 96, "stepsPerBar": 16},
        "deviceProfile": {"drumMap": {"kick": 53}},
        "tracks": [
            {
                "id": "t-drums",
                "midiChannel": 0,
                "pattern": {"lengthBars": 1, "steps": []},
                "drumKit": {"patterns": [{"bar": 1, "key": "kick", "pattern": "x.......x.......", "vel": 120}]},
            },
            {
                "id": "t-bass",
                "midiChannel": 2,
                "pattern": {"lengthBars": 1, "steps": []},
            },
        ],
        "docVersion": 0,
    }
    loop_path.write_text(json.dumps(init))

    c = Conductor(str(loop_path), port_filter=None, bpm=100.0, clock_source="external")
    ws_port = _free_port()
    server_task = asyncio.create_task(serve_ws(c, "127.0.0.1", ws_port))
    try:
        ws = await _connect(f"ws://127.0.0.1:{ws_port}")
        try:
            # Drain initial hello/doc/state
            await asyncio.sleep(0.05)
            base = int(c.get_doc().get("docVersion", 0))
            step = {"idx": 0, "events": [{"pitch": 40, "velocity": 100, "lengthSteps": 4}]}
            add = {"type": "applyPatch", "id": 301, "payload": {"baseVersion": base, "ops": [{"op": "add", "path": "/tracks/1/pattern/steps/-", "value": step}], "applyNow": False}}
            await ws.send(json.dumps(add))
            saw_add = False
            for _ in range(20):
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                obj = json.loads(raw)
                if obj.get("type") == "doc":
                    on_disk = json.loads(loop_path.read_text())
                    steps = on_disk["tracks"][1]["pattern"]["steps"]
                    if any(s.get("idx") == 0 for s in steps):
                        saw_add = True
                        break
            assert saw_add

            # Replace velocity on that step
            base2 = int(c.get_doc().get("docVersion", 0))
            # find index 0 array position
            arr_index = None
            for i, s in enumerate(json.loads(loop_path.read_text())["tracks"][1]["pattern"]["steps"]):
                if int(s.get("idx", -1)) == 0:
                    arr_index = i
                    break
            assert arr_index is not None
            repl = {"type": "applyPatch", "id": 302, "payload": {"baseVersion": base2, "ops": [{"op": "replace", "path": f"/tracks/1/pattern/steps/{arr_index}/events/0/velocity", "value": 90}], "applyNow": False}}
            await ws.send(json.dumps(repl))
            saw_replace = False
            for _ in range(20):
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                obj = json.loads(raw)
                if obj.get("type") == "doc":
                    on_disk2 = json.loads(loop_path.read_text())
                    step0 = [s for s in on_disk2["tracks"][1]["pattern"]["steps"] if int(s.get("idx", -1)) == 0][0]
                    if int(step0["events"][0]["velocity"]) == 90:
                        saw_replace = True
                        break
            assert saw_replace
        finally:
            await ws.close()
    finally:
        server_task.cancel()
        with contextlib.suppress(Exception):
            await server_task

