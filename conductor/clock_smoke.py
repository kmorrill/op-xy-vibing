from __future__ import annotations

import argparse
import statistics
import time


def percentiles(samples, ps):
    if not samples:
        return {p: 0.0 for p in ps}
    s = sorted(samples)
    out = {}
    for p in ps:
        k = (len(s) - 1) * (p / 100.0)
        f = int(k)
        c = min(f + 1, len(s) - 1)
        if f == c:
            out[p] = s[f]
        else:
            d0 = s[f] * (c - k)
            d1 = s[c] * (k - f)
            out[p] = d0 + d1
    return out


def run(bpm: float, seconds: float) -> None:
    # 24 PPQN clock target interval in seconds
    interval = 60.0 / (bpm * 24.0)
    end_time = time.monotonic() + seconds

    last = time.monotonic()
    deltas = []
    ticks = 0
    while time.monotonic() < end_time:
        # Busy-waiting shortly before target time can reduce jitter, but we keep it simple here.
        time.sleep(interval)
        now = time.monotonic()
        deltas.append((now - last) - interval)
        last = now
        ticks += 1

    # Convert to ms and absolute jitter
    jit_ms = [abs(d) * 1000.0 for d in deltas]
    p = percentiles(jit_ms, [50, 95, 99])
    avg = statistics.mean(jit_ms) if jit_ms else 0.0
    print(f"bpm={bpm} seconds={seconds} ticks={ticks}")
    print(f"tick interval target={interval*1000:.3f}ms avg_jitter={avg:.3f}ms p50={p[50]:.3f}ms p95={p[95]:.3f}ms p99={p[99]:.3f}ms")


def main():
    ap = argparse.ArgumentParser(description="Internal clock jitter smoke test (24 PPQN)")
    ap.add_argument("--bpm", type=float, default=120.0)
    ap.add_argument("--seconds", type=float, default=5.0)
    args = ap.parse_args()
    run(args.bpm, args.seconds)


if __name__ == "__main__":
    main()

