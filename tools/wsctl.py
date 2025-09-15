from __future__ import annotations

import argparse
import asyncio
import json


async def run(url: str, cmd: str, args: argparse.Namespace):
    import websockets  # type: ignore

    connect_url = url
    async with websockets.connect(connect_url) as ws:
        # Read initial doc/state
        init1 = json.loads(await ws.recv())
        init2 = json.loads(await ws.recv())
        doc = init1["payload"] if init1.get("type") == "doc" else init2["payload"]
        doc_version = int(doc.get("docVersion", 0))
        # Transport is device-controlled; do not send play/stop/continue
        if cmd == "tempo":
            await ws.send(json.dumps({"type": "setTempo", "bpm": float(args.bpm)}))
        elif cmd == "patch-vel":
            ops = [{"op": "replace", "path": "/tracks/0/pattern/steps/0/events/0/velocity", "value": int(args.velocity)}]
            await ws.send(json.dumps({"type": "applyPatch", "payload": {"baseVersion": doc_version, "ops": ops, "applyNow": bool(args.apply_now)}}))
        elif cmd == "replace":
            new_doc = json.loads(args.doc)
            await ws.send(json.dumps({"type": "replaceJSON", "payload": {"baseVersion": doc_version, "doc": new_doc, "applyNow": bool(args.apply_now)}}))
        # Print next few messages
        for _ in range(3):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
                print(msg)
            except asyncio.TimeoutError:
                break


def main():
    ap = argparse.ArgumentParser(description="Simple WS controller for Conductor")
    ap.add_argument("--url", default="ws://127.0.0.1:8765")
    sub = ap.add_subparsers(dest="cmd", required=True)
    # Transport commands removed: device is transport authority
    p_tempo = sub.add_parser("tempo"); p_tempo.add_argument("--bpm", required=True)
    p_patch = sub.add_parser("patch-vel"); p_patch.add_argument("--velocity", required=True); p_patch.add_argument("--apply-now", action="store_true")
    p_replace = sub.add_parser("replace"); p_replace.add_argument("--doc", required=True); p_replace.add_argument("--apply-now", action="store_true")
    args = ap.parse_args()
    asyncio.run(run(args.url, args.cmd, args))


if __name__ == "__main__":
    main()
