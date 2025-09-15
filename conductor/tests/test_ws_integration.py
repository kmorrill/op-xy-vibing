from __future__ import annotations

import asyncio
import json
import socket
import contextlib
from pathlib import Path
import unittest

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


class TestWSIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmpdir = Path(self._get_tmpdir())
        self.loop_path = self.tmpdir / "loop.json"
        self.tmpdir.mkdir(parents=True, exist_ok=True)
        init = {
            "version": "opxyloop-1.0",
            "meta": {"tempo": 100, "ppq": 96, "stepsPerBar": 16},
            "deviceProfile": {"drumMap": {"kick": 53, "snare": 55, "closed_hat": 61, "open_hat": 62}},
            "tracks": [
                {
                    "id": "t-drums",
                    "name": "Drums",
                    "type": "sampler",
                    "role": "drums",
                    "midiChannel": 0,
                    "pattern": {"lengthBars": 1, "steps": []},
                    "drumKit": {
                        "patterns": [
                            {"bar": 1, "key": "kick", "pattern": "x.......x.......", "vel": 120},
                            {"bar": 1, "key": "snare", "pattern": "....x.......x...", "vel": 110},
                        ]
                    }
                }
            ],
            "docVersion": 0,
        }
        self.loop_path.write_text(json.dumps(init))

        self.c = Conductor(str(self.loop_path), port_filter=None, bpm=100.0, clock_source="external")
        self.ws_port = _free_port()
        self.server_task = asyncio.create_task(serve_ws(self.c, "127.0.0.1", self.ws_port))
        self.ws = await _connect(f"ws://127.0.0.1:{self.ws_port}")
        # Drain initial messages
        await asyncio.sleep(0.05)

    async def asyncTearDown(self):
        with contextlib.suppress(Exception):
            await self.ws.close()
        self.server_task.cancel()
        with contextlib.suppress(Exception):
            await self.server_task

    def _get_tmpdir(self) -> str:
        import tempfile
        return tempfile.mkdtemp(prefix="ws-it-")

    async def test_add_closed_hat_and_toggle_snare(self):
        # Add a new closed_hat row
        doc = self.c.get_doc(); base = int(doc.get("docVersion", 0))
        spec = {"bar": 1, "key": "closed_hat", "pattern": "x.x.x.x.x.x.x.x.", "vel": 90}
        add_msg = {"type": "applyPatch", "id": 200, "payload": {"baseVersion": base, "ops": [{"op": "add", "path": "/tracks/0/drumKit/patterns/-", "value": spec}], "applyNow": False}}
        await self.ws.send(json.dumps(add_msg))
        # Await doc reflecting change
        ok_add = False
        for _ in range(20):
            raw = await asyncio.wait_for(self.ws.recv(), timeout=2.0)
            obj = json.loads(raw)
            if obj.get("type") == "doc":
                on_disk = json.loads(self.loop_path.read_text())
                hats = [p for p in on_disk["tracks"][0]["drumKit"]["patterns"] if p.get("key") == "closed_hat"]
                if hats and hats[0].get("pattern") == spec["pattern"]:
                    ok_add = True
                    break
        self.assertTrue(ok_add, "expected closed_hat row to be added")

        # Toggle snare step 0 to 'x' via replace
        doc2 = self.c.get_doc(); base2 = int(doc2.get("docVersion", 0))
        snare_idx = None
        for i, p in enumerate(doc2["json"]["tracks"][0]["drumKit"]["patterns"]):
            if p.get("key") == "snare":
                snare_idx = i; break
        self.assertIsNotNone(snare_idx)
        new_snare = "x...x.......x..."
        rep_msg = {"type": "applyPatch", "id": 201, "payload": {"baseVersion": base2, "ops": [{"op": "replace", "path": f"/tracks/0/drumKit/patterns/{snare_idx}/pattern", "value": new_snare}], "applyNow": False}}
        await self.ws.send(json.dumps(rep_msg))
        ok_rep = False
        for _ in range(20):
            raw = await asyncio.wait_for(self.ws.recv(), timeout=2.0)
            obj = json.loads(raw)
            if obj.get("type") == "doc":
                cur = json.loads(self.loop_path.read_text())
                sn = [p for p in cur["tracks"][0]["drumKit"]["patterns"] if p.get("key") == "snare"][0]
                if sn.get("pattern") == new_snare:
                    ok_rep = True
                    break
        self.assertTrue(ok_rep, "expected snare pattern to be replaced")

