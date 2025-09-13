from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from typing import Any, Dict, List, Tuple


SPEC_PATH = "docs/opxyloop-1.0.md"


class ValidationError(Exception):
    pass


def _err(errors: List[str], path: str, msg: str) -> None:
    errors.append(f"{path}: {msg}")


def validate_loop(loop: Dict[str, Any]) -> List[str]:
    """Lightweight validator aligned to docs/opxyloop-1.0.md §1–10.

    Returns a list of human-readable errors with JSON-pointer-like paths.
    Intentionally checks core MVP constraints to avoid false negatives
    while keeping strict enough to catch common mistakes.
    """
    errors: List[str] = []

    # §1: Top-level
    if loop.get("version") != "opxyloop-1.0":
        _err(errors, "/version", "must equal 'opxyloop-1.0'")

    meta = loop.get("meta")
    if not isinstance(meta, dict):
        _err(errors, "/meta", "required object missing")
    else:
        tempo = meta.get("tempo")
        ppq = meta.get("ppq")
        spb = meta.get("stepsPerBar")
        if not isinstance(tempo, (int, float)):
            _err(errors, "/meta/tempo", "required number (BPM)")
        if not isinstance(ppq, int):
            _err(errors, "/meta/ppq", "required integer (pulses per quarter note)")
        if not isinstance(spb, int):
            _err(errors, "/meta/stepsPerBar", "required integer (grid per bar)")

    dev = loop.get("deviceProfile")
    if dev is not None:
        if not isinstance(dev, dict):
            _err(errors, "/deviceProfile", "must be an object if present")
        else:
            if "drumMap" in dev:
                dmap = dev["drumMap"]
                if not isinstance(dmap, dict) or not all(
                    isinstance(k, str) and isinstance(v, int) and 0 <= v <= 127 for k, v in dmap.items()
                ):
                    _err(errors, "/deviceProfile/drumMap", "string→integer[0..127] map required")

    tracks = loop.get("tracks")
    if not isinstance(tracks, list) or len(tracks) == 0:
        _err(errors, "/tracks", "required non-empty array")
    else:
        for ti, tr in enumerate(tracks):
            tpath = f"/tracks/{ti}"
            if not isinstance(tr, dict):
                _err(errors, tpath, "must be object")
                continue
            for key in ("id", "name", "type"):
                if not isinstance(tr.get(key), str):
                    _err(errors, f"{tpath}/{key}", "required string")
            ch = tr.get("midiChannel")
            if not isinstance(ch, int) or not (0 <= ch <= 15):
                _err(errors, f"{tpath}/midiChannel", "required integer 0..15")

            # §5: pattern
            pat = tr.get("pattern")
            if not isinstance(pat, dict):
                _err(errors, f"{tpath}/pattern", "required object")
            else:
                lb = pat.get("lengthBars")
                steps = pat.get("steps")
                if not isinstance(lb, int) or lb < 1:
                    _err(errors, f"{tpath}/pattern/lengthBars", "integer ≥1 required")
                if not isinstance(steps, list):
                    _err(errors, f"{tpath}/pattern/steps", "required array (sparse allowed)")
                else:
                    for si, st in enumerate(steps):
                        spath = f"{tpath}/pattern/steps[{si}]"
                        if not isinstance(st, dict):
                            _err(errors, spath, "must be object")
                            continue
                        idx = st.get("idx")
                        if not isinstance(idx, int) or idx < 0:
                            _err(errors, f"{spath}/idx", "required integer ≥0")
                        ev = st.get("events")
                        if ev is not None:
                            if not isinstance(ev, list):
                                _err(errors, f"{spath}/events", "must be array if present")
                            else:
                                for ei, e in enumerate(ev):
                                    epath = f"{spath}/events[{ei}]"
                                    if not isinstance(e, dict):
                                        _err(errors, epath, "must be object")
                                        continue
                                    has_pitch = any(k in e for k in ("pitch", "degree", "chord"))
                                    if not has_pitch:
                                        _err(errors, epath, "requires one of pitch|degree|chord")
                                    if "degree" in e and "octaveOffset" not in e:
                                        _err(errors, epath + "/octaveOffset", "required when using degree")
                                    vel = e.get("velocity")
                                    if not isinstance(vel, int) or not (1 <= vel <= 127):
                                        _err(errors, epath + "/velocity", "integer 1..127 required")
                                    ls = e.get("lengthSteps")
                                    if not isinstance(ls, int) or ls < 1:
                                        _err(errors, epath + "/lengthSteps", "integer ≥1 required")
                                    rat = e.get("ratchet")
                                    if rat is not None and (not isinstance(rat, int) or rat < 2 or rat > 8):
                                        _err(errors, epath + "/ratchet", "integer ≥2 and ≤8 (guardrail)")

            # §5.1.2: optional drumKit helper
            dk = tr.get("drumKit")
            if dk is not None:
                if not isinstance(dk, dict):
                    _err(errors, f"{tpath}/drumKit", "must be object if present")
                else:
                    pats = dk.get("patterns")
                    if not isinstance(pats, list) or len(pats) == 0:
                        _err(errors, f"{tpath}/drumKit/patterns", "required non-empty array")
                    else:
                        dmap = (dev or {}).get("drumMap", {}) if isinstance(dev, dict) else {}
                        spb = (meta or {}).get("stepsPerBar") if isinstance(meta, dict) else None
                        for pi, spec in enumerate(pats):
                            ppath = f"{tpath}/drumKit/patterns[{pi}]"
                            if not isinstance(spec, dict):
                                _err(errors, ppath, "must be object")
                                continue
                            bar = spec.get("bar")
                            key = spec.get("key")
                            pattern = spec.get("pattern")
                            if not isinstance(bar, int) or bar < 1:
                                _err(errors, ppath + "/bar", "integer ≥1 required")
                            if not isinstance(key, str):
                                _err(errors, ppath + "/key", "required string")
                            elif key not in dmap:
                                _err(errors, ppath + "/key", "must exist in deviceProfile.drumMap")
                            if not isinstance(pattern, str):
                                _err(errors, ppath + "/pattern", "required string")
                            else:
                                if not isinstance(spb, int):
                                    _err(errors, "/meta/stepsPerBar", "required for drumKit validation")
                                else:
                                    if len(pattern) != spb:
                                        _err(errors, ppath + "/pattern", f"length must equal meta.stepsPerBar ({spb})")
                                    for c in pattern:
                                        if c not in ("x", ".", "-"):
                                            _err(errors, ppath + "/pattern", "allowed chars: 'x' '.' '-' only")
                            if "vel" in spec:
                                v = spec["vel"]
                                if not isinstance(v, int) or not (1 <= v <= 127):
                                    _err(errors, ppath + "/vel", "integer 1..127 required")
                            if "lengthSteps" in spec:
                                ls = spec["lengthSteps"]
                                if not isinstance(ls, int) or ls < 1:
                                    _err(errors, ppath + "/lengthSteps", "integer ≥1 required")

            # §6: ccLanes (optional)
            lanes = tr.get("ccLanes")
            if lanes is not None:
                if not isinstance(lanes, list):
                    _err(errors, f"{tpath}/ccLanes", "must be array if present")
                else:
                    for li, lane in enumerate(lanes):
                        lpath = f"{tpath}/ccLanes[{li}]"
                        if not isinstance(lane, dict):
                            _err(errors, lpath, "must be object")
                            continue
                        if not isinstance(lane.get("id"), str):
                            _err(errors, lpath + "/id", "required string")
                        dest = lane.get("dest")
                        if not (isinstance(dest, int) or (isinstance(dest, str) and (dest.startswith("cc:") or dest.startswith("name:")))):
                            _err(errors, lpath + "/dest", "integer CC# or 'cc:<num>' or 'name:<id>' required")
                        mode = lane.get("mode")
                        if mode not in ("points", "hold", "ramp"):
                            _err(errors, lpath + "/mode", "must be 'points'|'hold'|'ramp'")
                        points = lane.get("points")
                        if not isinstance(points, list) or len(points) == 0:
                            _err(errors, lpath + "/points", "required non-empty array")
                        else:
                            for pi, pt in enumerate(points):
                                ppath = f"{lpath}/points[{pi}]"
                                if not isinstance(pt, dict):
                                    _err(errors, ppath, "must be object")
                                    continue
                                t = pt.get("t")
                                v = pt.get("v")
                                if not isinstance(v, (int, float)) or not (0 <= v <= 127):
                                    _err(errors, ppath + "/v", "0..127 required")
                                if not isinstance(t, dict) or not ("ticks" in t or ("bar" in t and "step" in t)):
                                    _err(errors, ppath + "/t", "must be {ticks:n} or {bar:n, step:n}")

            # §7: lfos (optional)
            lfos = tr.get("lfos")
            if lfos is not None:
                if not isinstance(lfos, list):
                    _err(errors, f"{tpath}/lfos", "must be array if present")
                else:
                    for li, lfo in enumerate(lfos):
                        lpath = f"{tpath}/lfos[{li}]"
                        if not isinstance(lfo, dict):
                            _err(errors, lpath, "must be object")
                            continue
                        if not isinstance(lfo.get("id"), str):
                            _err(errors, lpath + "/id", "required string")
                        dest = lfo.get("dest")
                        if not (isinstance(dest, int) or (isinstance(dest, str) and (dest.startswith("cc:") or dest.startswith("name:")))):
                            _err(errors, lpath + "/dest", "integer CC# or 'cc:<num>' or 'name:<id>' required")
                        depth = lfo.get("depth")
                        if not isinstance(depth, int) or not (0 <= depth <= 127):
                            _err(errors, lpath + "/depth", "integer 0..127 required")
                        rate = lfo.get("rate")
                        if not isinstance(rate, dict) or not ("sync" in rate or "hz" in rate):
                            _err(errors, lpath + "/rate", "must be {sync:""}|{hz:n}")
                        shape = lfo.get("shape")
                        if shape not in ("sine", "triangle", "saw", "ramp", "square", "samplehold"):
                            _err(errors, lpath + "/shape", "invalid shape")

    return errors


def canonicalize(loop: Dict[str, Any]) -> Dict[str, Any]:
    """Return a canonicalized deep copy for stable diffs.

    - Sort tracks by id
    - Sort steps by idx
    - Sort ccLanes/lfos by id
    - Sort cc points by time (bar/step or ticks)
    - Sort drumKit.patterns by (bar, key)
    - Use deterministic key ordering on dump
    """
    doc = copy.deepcopy(loop)

    def sort_points(points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def key_fn(p: Dict[str, Any]) -> Tuple[int, int, int]:
            t = p.get("t", {})
            if "ticks" in t:
                return (0, int(t.get("ticks", 0)), 0)
            return (1, int(t.get("bar", 0)), int(t.get("step", 0)))

        return sorted(points, key=key_fn)

    tracks = doc.get("tracks")
    if isinstance(tracks, list):
        tracks.sort(key=lambda t: t.get("id", ""))
        for tr in tracks:
            pat = tr.get("pattern")
            if isinstance(pat, dict) and isinstance(pat.get("steps"), list):
                pat["steps"].sort(key=lambda s: s.get("idx", 0))
            if isinstance(tr.get("ccLanes"), list):
                tr["ccLanes"].sort(key=lambda l: l.get("id", ""))
                for lane in tr["ccLanes"]:
                    if isinstance(lane.get("points"), list):
                        lane["points"] = sort_points(lane["points"])
            if isinstance(tr.get("lfos"), list):
                tr["lfos"].sort(key=lambda l: l.get("id", ""))
            dk = tr.get("drumKit")
            if isinstance(dk, dict) and isinstance(dk.get("patterns"), list):
                dk["patterns"].sort(key=lambda p: (p.get("bar", 0), p.get("key", "")))

    return doc


def sha256_canonical(doc: Dict[str, Any]) -> str:
    """Compute SHA-256 of canonical JSON string (sorted keys, compact)."""
    s = json.dumps(doc, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate and canonicalize opxyloop-1.0 JSON")
    ap.add_argument("path", help="Path to loop JSON file")
    ap.add_argument("--write", "-w", action="store_true", help="Rewrite file with canonical formatting")
    ap.add_argument("--print-hash", action="store_true", help="Print SHA-256 of canonical JSON")
    args = ap.parse_args(argv)

    try:
        with open(args.path, "r", encoding="utf-8") as f:
            loop = json.load(f)
    except Exception as e:
        print(f"error: failed to read {args.path}: {e}", file=sys.stderr)
        return 2

    errors = validate_loop(loop)
    if errors:
        print("invalid loop.json:")
        for e in errors:
            print(f" - {e}")
        return 1

    doc = canonicalize(loop)
    if args.print_hash:
        print(sha256_canonical(doc))

    if args.write:
        # Write canonical JSON with sorted keys, compact separators, newline at EOF
        data = json.dumps(doc, sort_keys=True, indent=2, ensure_ascii=False)
        if not data.endswith("\n"):
            data += "\n"
        with open(args.path, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"wrote canonical form to {args.path}")
    else:
        # Print a short OK message.
        print("ok: valid and canonicalizable")

    return 0


if __name__ == "__main__":
    sys.exit(main())

