from __future__ import annotations

import copy
from typing import Any, Dict, List


def _json_pointer_get_parent(root: Any, pointer: str):
    """Return (parent, key) for a JSON pointer path like /a/b/0.

    Supports dicts and lists. Does not support escaped ~0/~1 (MVP need).
    Raises KeyError/IndexError on invalid path.
    """
    if not pointer or pointer == "/":
        return None, None
    parts = [p for p in pointer.split("/") if p != ""]
    cur = root
    for i, p in enumerate(parts[:-1]):
        # arrays use integer indices
        if isinstance(cur, list):
            idx = int(p)
            cur = cur[idx]
        else:
            cur = cur[p]
    last = parts[-1] if parts else None
    return cur, last


def _apply_replace(root: Any, path: str, value: Any):
    parent, key = _json_pointer_get_parent(root, path)
    if parent is None:
        raise KeyError("cannot replace root")
    if isinstance(parent, list):
        idx = int(key)
        parent[idx] = value
    else:
        parent[key] = value


def _apply_add(root: Any, path: str, value: Any):
    parent, key = _json_pointer_get_parent(root, path)
    if parent is None:
        raise KeyError("cannot add at root")
    if isinstance(parent, list):
        if key == "-":
            parent.append(value)
        else:
            idx = int(key)
            # RFC6902 inserts before index
            parent.insert(idx, value)
    else:
        parent[key] = value


def _apply_remove(root: Any, path: str):
    parent, key = _json_pointer_get_parent(root, path)
    if parent is None:
        raise KeyError("cannot remove root")
    if isinstance(parent, list):
        idx = int(key)
        parent.pop(idx)
    else:
        del parent[key]


def apply_patch(doc: Dict[str, Any], ops: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply an RFC 6902 JSON Patch ops array to a deep copy of doc.

    Tries to use 'jsonpatch' if installed; otherwise falls back to a
    minimal implementation for add/replace/remove paths we use in UI.
    """
    base = copy.deepcopy(doc)
    try:
        import jsonpatch  # type: ignore

        patch = jsonpatch.JsonPatch(ops)
        return patch.apply(base, in_place=False)
    except Exception:
        # Minimal fallback
        for op in ops:
            t = op.get("op")
            path = op.get("path")
            if not isinstance(path, str):
                raise ValueError("invalid path in op")
            if t == "replace":
                _apply_replace(base, path, op.get("value"))
            elif t == "add":
                _apply_add(base, path, op.get("value"))
            elif t == "remove":
                _apply_remove(base, path)
            else:
                raise NotImplementedError(f"op '{t}' not supported in fallback")
        return base
