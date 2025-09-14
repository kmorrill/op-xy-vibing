from __future__ import annotations

import asyncio
import json
import threading
from typing import Any, Dict, Optional


async def _metrics_task(websocket, engine, clock):
    while True:
        try:
            payload = {
                "type": "metrics",
                "ts": asyncio.get_event_loop().time(),
                "payload": {
                    "engine": engine.get_metrics() if hasattr(engine, "get_metrics") else {},
                    "clock": clock.get_metrics() if hasattr(clock, "get_metrics") else {},
                },
            }
            await websocket.send(json.dumps(payload))
            await asyncio.sleep(1.0)
        except Exception:
            break


async def _handler(websocket, path, engine, clock, get_doc):
    tasks = [asyncio.create_task(_metrics_task(websocket, engine, clock))]
    try:
        async for _ in websocket:
            pass
    finally:
        for t in tasks:
            t.cancel()


def start_ws_server(engine, clock, host: str = "127.0.0.1", port: int = 8765, get_doc=None) -> Optional[threading.Thread]:
    """Start a minimal WS server broadcasting metrics once per second.

    Requires the 'websockets' package. Returns a daemon thread running the server,
    or None if 'websockets' is unavailable.
    """
    try:
        import websockets  # type: ignore
    except Exception:
        print("[ws] websockets not installed; skipping WS server")
        return None

    def _runner():
        async def _main():
            async def handler(ws, path):
                return await _handler(ws, path, engine, clock, get_doc)
            async with websockets.serve(handler, host, port):
                print(f"[ws] serving metrics on ws://{host}:{port}")
                await asyncio.Future()

        asyncio.run(_main())

    th = threading.Thread(target=_runner, daemon=True)
    th.start()
    return th

