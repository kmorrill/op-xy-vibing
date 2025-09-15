# Changelog – UI External Clock + CC80 Tempo

## LFO Feature Set
### Added
- Full LFO support in playback engine: shapes sine, triangle, ramp (rise), saw (fall), square and sample-hold.
- Dual rate modes: musical sync (e.g., 1/8, 1/8T) and absolute Hz; per-spec phase (0..1), offset, fade-in (ms), and active windows.
- Per-tick evaluation with deterministic sample-hold and bar-boundary phase reset.
- Live CC merging semantics: LFOs modulate around ccLane base if present; otherwise around `offset` (default 64).
- Post-merge clamping honors any ccLane `range` for the same target.

### Changed
- CC emission now aggregates per-target contributions over channel+CC pairs, with unchanged-value dedupe and existing per-tick rate guards.

### How to verify
- Use `conductor/tests/test_lfo_engine.py` for core shape/params sanity (no device needed).
- In UI, watch Automation panel for live CC modulation when a loop with `lfos` is loaded.

## Added
- Web UI (Safari) to view patterns per track and control transport/tempo.
- External clock support: Conductor listens to OP‑XY MIDI Start/Stop/Continue/SPP/Clock; UI shows device BPM in real time.
- Tempo control via MIDI CC80 on channel 0 (0..127 → 40..220 BPM). Device remains master; no clock takeover.
- Velocity A/B smoke fixtures and Make targets (Channel 1 D3 alternating loud/quiet with rests).
- Panic/kill helpers for clean real-device runs.

## Changed
- Runtime triggers tick 0 on Play to avoid missing step-0 events.
- WS server broadcasts state regularly; UI auto-polls as fallback for external BPM.

## How to verify
- Clean slate: kill processes, free 8765, send panic (see AGENTS.md Real Device Safety).
- Run Conductor (external clock) and open UI: tempo follows device changes.
- In UI, type BPM and Push tempo: device BPM changes; device knob remains responsive.
- Run velocity A/B: loud, rest, quiet, loud, rest, quiet; stops cleanly.
