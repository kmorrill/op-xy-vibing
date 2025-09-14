from __future__ import annotations

def bpm_to_cc80(bpm: float) -> int:
    """Map BPM in [40, 220] to CC80 value 0..127 (inclusive)."""
    b = max(40.0, min(220.0, float(bpm)))
    # 0 -> 40, 127 -> 220; linear mapping
    val = int(round((b - 40.0) / 180.0 * 127.0))
    return max(0, min(127, val))


def cc80_to_bpm(val: int) -> float:
    """Map CC80 value 0..127 back to BPM in [40, 220]."""
    v = max(0, min(127, int(val)))
    return 40.0 + (v / 127.0) * 180.0

