# Changelog – UI External Clock + CC80 Tempo

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

