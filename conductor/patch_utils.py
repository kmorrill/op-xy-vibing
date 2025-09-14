from __future__ import annotations

import copy
from typing import Any, Dict, List


def apply_patch(doc: Dict[str, Any], ops: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Apply an RFC 6902 JSON Patch ops array to a deep copy of doc.

    Requires jsonpatch package. Returns the patched document.
    """
    import jsonpatch  # type: ignore

    base = copy.deepcopy(doc)
    patch = jsonpatch.JsonPatch(ops)
    return patch.apply(base, in_place=False)

