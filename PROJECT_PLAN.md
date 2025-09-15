# OP‑XY Vibe Coding – Project Plan

## A. Overview
- Problem: Let a human co‑create music with a “vibe coding” agent that edits a canonical loop JSON (`opxyloop‑1.0`) which a Python engine plays in real time to the OP‑XY device.
- Objectives: glitch‑free real‑time playback, bulletproof note‑off lifecycle during edits/hot‑swap, faithful adherence to `docs/opxyloop-1.0.md`, observable behavior with tight jitter bounds, and zero‑data‑loss persistence via Git.
- Scope (MVP): Conductor (file watcher + WS), real‑time playback engine, Web UI grid, JSON Patch edits, external clock priority with internal override, Git history, tests and metrics. Single drum track required; one pitched track optional in v0 UI.
- Non‑goals (MVP): seek/catch‑up behavior, sustain/pedal, free‑running LFOs, multi‑track drums beyond one track.

## Early Proof Points (fast confidence)
- P0: Spec + fixtures load
  - Load `docs/opxyloop-1.0.md`; add 3 minimal fixtures in `conductor/tests/fixtures/` (empty loop, drum bar with accent, CC+LFO example). Validator accepts them.
- P1: Clock smoke tests
  - Internal clock: 24 PPQN metronome logs tick deltas; p95 jitter < 2.0 ms on dev machine.
  - External clock simulator: feed synthetic pulses; state reflects pulses accurately.
- P2: Note lifecycle micro‑demo
  - Engine stub emits a single Note On then off at exact gate without device (virtual sink). Log shows paired on/off with delta within tolerance. Panic triggers send All Notes Off across channels.
- P3: Patch gating
  - Conductor rejects stale patch; accepts valid patch; atomic write proves no torn file; `docVersion` increments.

## B. Architecture Diagram (ASCII)
```
Human ⇄ LLM (Agent)
          │
          ▼
   Conductor (single origin)
     ├── HTTP UI (static)
     ├── WS (doc/state/metrics)
     ├── File watcher (atomic write/watch)
     ├── Git (batched commits)
     └── Playback Engine ⇄ OP‑XY (USB‑C MIDI)

Spec: docs/opxyloop-1.0.md (normative)
```

## C. Requirements
- Functional:
  - Real‑time scheduling with no look‑ahead; events fire on current tick.
  - External MIDI clock/transport (OP‑XY) is authoritative by default.
  - Internal tempo override on request; transmit MIDI Clock only when explicitly in internal clock mode.
  - Transport: external device controls Start/Stop/Continue; optional SPP reposition (no seek UI/API). UI/server never send transport.
  - JSON ownership: `loop.json` on disk is canonical; JSON Patch (RFC 6902) or full replace.
  - Single drum track (GM‑safe fallback); velocity semantics: Accent ≥105, normal 70–100, ghost 30–55; max ratchet density 8/step.
  - CC & LFO: base + bipolar offset, clamp 0–127; phase reset on Play and bar boundary; no catch‑up on seek.
  - Note‑off guarantee across edits/hot‑swap; All Notes Off on stop/hot‑swap/disconnect.
  - Change timing: structural at next bar by default with “apply now” override; non‑structural next tick.
  - No seek/catch‑up in MVP.
- Non‑functional:
  - Latency/jitter targets: track p95/p99 tick jitter; message ordering correctness; throughput within ~2.5k msgs/s global, ~800/track.
  - Safety/panic: rigorous active‑notes accounting; All Notes Off on panic.
  - Atomicity/durability: temp+rename writes; Git batched commits (3–5s) and manual “Checkpoint”.
  - Testability: virtual MIDI, synthetic clock (internal/external), expectation DSL.
  - Observability: broadcast metrics (msgPerSec, jitterMsP95/p99, dropped, clockSrc); hash of canonical JSON; health endpoint; WS hello/ack/ping.

## D. Playback Engine Strategy (no look‑ahead)
- Algorithm (tick loop):
  - Receive clock ticks (24 PPQN) from internal timer or external MIDI Clock.
  - On each tick T: compute due events for T only (no future scheduling). Emit Note On/Off and CC for T, then return to wait.
  - Pairing: when emitting Note On, compute off_tick = on_tick + length_in_ticks; create note_id and push into active‑notes ledger keyed by (channel,pitch) as a stack to support overlapping notes; schedule off on that exact tick even if the JSON changes.
  - Reconciliation: on each bar boundary and on transport stop, reconcile ledger (send Note Off for any overdue); always emit All Notes Off on stop/hot‑swap/disconnect.
- Data structures:
  - Active‑notes ledger: dict[(ch,pitch)] -> stack of {note_id, off_tick}.
  - Pending structural doc: staged doc applied at next bar; non‑structural deltas applied at next tick.
  - Rate guard counters: global and per‑track rolling window; lowest‑audibility CCs shed first.
- Threading & timing:
  - Single timing thread for tick loop; all WS/file events post messages to it via lock‑free queue. Use monotonic time; avoid allocations in tick path (pre‑allocate buffers).
  - External clock: derive tick times from incoming pulses; if pulses stall beyond timeout, auto‑pause and surface error.
- Transport & SPP:
  - Start/Stop/Continue honored both ways. If SPP arrives with Start/Continue, reposition runtime to that location; no UI/API seek and no CC catch‑up.
- CC & LFO:
  - At tick, CC_value = clamp(base_value + lfo_offset_bipolar, 0..127). LFO phase resets on Play and bar boundary.
- Safety:
  - Panic command: iterate channels and emit All Notes Off; clear ledger. On device reconnect, send baseline CCs if needed.

## E. Interfaces & Contracts

## D. Interfaces & Contracts
- WebSocket Envelopes: `{type, ts, payload}`.
  - Inbound: `play`, `stop`, `continue`, `setTempo{bpm}`, `applyPatch{baseVersion,ops[]}`, `replaceJSON{baseVersion,doc}`.
  - Outbound: `state{transport,clockSource,bpm,barBeatTick}`, `doc{docVersion,json}`, `metrics{msgPerSec,jitterMsP95,jitterMsP99,dropped,clockSrc}`, `error{code,message,details}`.
- Examples:
  - `{"type":"applyPatch","ts":1699999999,"payload":{"baseVersion":42,"ops":[{"op":"replace","path":"/tracks/0/steps/3/vel","value":110}]}}`
  - `{"type":"state","payload":{"transport":"playing","clockSource":"external","bpm":120,"barBeatTick":"2:1:0"}}`
- Directory Layout:
```
project/
  conductor/
    app.py
    ws_api.py
    midi_engine.py
    clock.py
    store.py
    tests/
      fixtures/*.json
      test_rt_sanity.py
  ui/
    index.html
    app.js
  docs/
    opxyloop-1.0.md
  loop.json
  README.md
```
- Canonical JSON formatting & hashing:
  - Deterministic key ordering and whitespace; newline at EOF.
  - UI may display an SHA‑256 of canonical JSON (footer/comment out of band) for user confidence; Conductor keeps authoritative hash internally.
- Validation pipeline:
  - On every patch/replace: validate against `docs/opxyloop-1.0.md` schema; normalize to canonical form; reject with `error{code,details}` if invalid.
  - Canonical JSON hash: compute (SHA‑256) for metrics; optional UI display.

## F. Milestones & Acceptance Criteria
- M0: Spec, Fixtures, Canonicalizer
  - Deliverables: load `docs/opxyloop-1.0.md`; implement validator + canonical formatter; fixtures (empty, drum, CC+LFO).
  - DoD tests: fixtures validate; canonical formatting stable hash; invalid examples rejected with pinpointed errors.
- M1: Clock Foundations
  - Deliverables: internal clock (24 PPQN) and synthetic external clock driver; timing logger with jitter stats; panic command skeleton.
  - DoD tests: p95 tick jitter < 2.0 ms (dev) and < 4.0 ms (CI); start/stop/continue reflected in state.
- M2: Engine Skeleton + Note Lifecycle
  - Deliverables: active‑notes ledger; on->off pairing; All Notes Off; no device I/O (virtual sink).
  - DoD tests: micro‑demo proves paired on/off within tolerance; “orphan guard” reconciliation clears overdue offs; post‑stop silence for ≥200 ms.
- M3: Real‑time Playback (Internal Clock)
  - Deliverables: map doc steps to ticks; drums path; velocity semantics; rate caps enforced; no look‑ahead.
  - DoD tests: DSL asserts NoteOn/Off ordering and timing windows on fixtures; ledger never leaks; CC clamp verified.
- M4: External Clock Follow
  - Deliverables: MIDI start/stop/continue/clock handling; optional SPP reposition.
  - DoD tests: synthetic external pulses drive playback; tempo changes tracked; stop/continue correct; SPP reposition honored without catch‑up.
- M5: Edits & Persistence
  - Deliverables: JSON Patch apply & reject stale; atomic temp+rename; next‑bar apply for structural edits; UI can patch simple toggles.
  - DoD tests: edits during sounding notes preserve note‑offs; structural edits delayed to bar; docVersion monotonic; atomicity proven.
- M6: LFO/CC Implementation
  - Deliverables: CC lane + bipolar LFO offset; clamp; phase reset on Play/bar; rate guard shedding of CC bursts.
  - DoD tests: DSL verifies `atLeastHz` behavior and clamping; shedding triggers under load without affecting notes.
- M7: Git History & Checkpoints
  - Deliverables: batched commits (3–5s) including docVersion; manual “Checkpoint”; crash recovery.
  - DoD tests: simulate crash between writes and recover from last commit; clear commit messages.
- M8: Web UI v0
  - Deliverables: Safari grid for single drum + one pitched track; lossless JSON round‑trip; transport controls.
  - DoD tests: UI patches apply; stale rebased; doc reflects instantly; no seek UI.
- M9: Observability & SLOs
  - Deliverables: metrics broadcast (msgPerSec, jitter p95/p99, dropped, clockSrc, activeNotes, hash); structured event logs.
  - DoD tests: harness consumes metrics and asserts thresholds; logs include note_id with schedule vs emit delta.

## G. Test Harness & Integration Tests
- Virtual MIDI destination to capture all MIDI; timestamp events.
- Synthetic clock drivers: internal and simulated external (24 PPQN + Start/Stop/Continue + optional SPP).
- Python WebSocket client helper to subscribe, patch, and assert:
  - hello + doc on connect
  - ack/error with ids
  - doc/state rebroadcast on effective change (including next‑bar applies)
  - no spurious redraws when hash unchanged
- DSL examples:
```
@bpm 120
expect on  ch10 36 vel>=105 within 10ms of 0.000s
expect off ch10 36 within 5ms  of 0.250s
expect cc  ch1  74 atLeastHz 120 for 2.0s
# Edit while a note is sounding — note-off must still occur:
during edit replaceJSON {...}
expect off ch1 60 within 5ms of 0.500s  # note-off not lost
after stop expect no on|cc for 200ms; allNotesOff observed
```
- Timing tolerances: use windows (p95/p99) not absolutes; define flakiness budget; CI parallelism with isolated virtual MIDI ports per worker.
 - Determinism aids: use monotonic fake time in unit tests; reserve real‑time tolerance tests for integration layer; WS tests stable with timeouts and retries.
 - Coverage focus: note‑off during live edits, structural apply next bar, CC+LFO merge clamp, panic after stop/hot‑swap/disconnect.

## H. Risks & Mitigations
- Real‑time jitter: use high‑priority timing loop; CoreMIDI timestamps where possible; minimize GC/allocs; precompute step state per tick.
- File watcher edge cases: debounce, re‑read after writes, guard partial writes with temp+rename.
- External clock instability: smooth BPM estimation; handle missing clocks with timeout and auto‑pause.
- OP‑XY disconnects: detect promptly; emit panic; auto‑retry connection; surface error state.
- Note‑off integrity: maintain active‑notes registry across doc swaps; periodic reconciliation; All Notes Off on stop/hot‑swap/disconnect.
 - Bug traps: assert no events 200 ms after stop; watchdog for overdue offs; drop CCs first under load.

## I. Backlog / Future
- Multi‑track drums; choke groups; per‑LFO free‑run; humanize/swing layer; device profile tooling; advanced UI (automation curves); seek and catch‑up.

## J. Open Questions
- SPP handling in MVP: honor reposition when provided, or defer? (Current: may reposition runtime; no seek UI.)
- Canonical JSON hash exposure: UI footer or WS‑only?
- Minimum macOS version and CoreMIDI backend constraints?
- Exact metrics schema versioning and retention policy?

## Notes on Spec Reference
- `docs/opxyloop-1.0.md` is the normative reference and is present in this repo. Track tasks: schema enforcement in validator, canonical formatting rules, device maps, fixtures, and validator wiring to Conductor writes.

## Runbook (manual checks through M3)
- Start Conductor in dev mode; watch logs.
- P1: run clock smoke (`make clock-smoke`): verify p95 jitter < 2 ms (dev).
- P2: run `make demo-note`: observe one Note On at t=0.000 and Note Off at t=gate with delta ≤ 5 ms.
- P3: apply a patch during the sounding note: verify off still occurs at scheduled time; then `stop` and confirm 200 ms silence and All Notes Off observed.
