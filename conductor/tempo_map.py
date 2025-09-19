from __future__ import annotations

def bpm_to_cc80(bpm: float) -> int:
    """Map requested BPM to CC80 value assuming device interprets CC as BPM*2."""
    b = max(0.0, float(bpm))
    val = int(round(b / 2.0))
    return max(0, min(127, val))


def cc80_to_bpm(val: int) -> float:
    """Map CC80 value back to BPM using calibrated slope of 2 BPM per unit."""
    v = max(0, min(127, int(val)))
    return float(v * 2.0)
