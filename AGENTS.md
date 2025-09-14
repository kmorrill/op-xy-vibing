# OP‑XY Vibe Coding – Agents & Components Spec

Reference: `docs/opxyloop-1.0.md` is normative for the loop JSON.

## Data Model Overview (MVP)
- Single source of truth: `loop.json` on disk (git tracked).
- Tracks: at least one drum track (GM‑safe fallback device map). Optional one pitched track in early UI. CC names resolve via the OP‑XY fixed CC map.
- CC lanes: base value per time; LFO: bipolar offset; merge = base + offset, clamped 0–127.
- LFO phase: reset on Play and bar boundary by default; free‑run is future work.
- Meta: tempo, length, docVersion, device profile. No seek/catch‑up in MVP.

## Concurrency & Apply Rules
- `docVersion`: monotonically increasing; stale patches are rejected and must rebase.
- Atomic persistence: write to temp then rename; broadcast new doc on success.
- Apply timing: structural edits (tempo/length/track defs) at next bar by default (allow explicit “apply now”); non‑structural (step toggle, velocity, CC point) on next tick.

## Edge Rules & Invariants
- No look‑ahead: schedule in true real time on current tick only.
- Note‑off guarantee: every Note On emits a matching Note Off, even during live edits/hot‑swap. Maintain active‑notes registry; emit All Notes Off on stop/hot‑swap/disconnect.
- Clock: external OP‑XY MIDI clock/transport authoritative by default; internal tempo override on explicit user request (then transmit MIDI Clock out).
- Transport: bi‑directional play/stop/continue. SPP may reposition runtime, but no seek UI/API in MVP and no CC catch‑up on seek.
- Safety: rate guards (~2.5k msgs/s global, ~800/track); shed lowest‑audibility CC bursts first.

---

## Vibe Coding Agent (LLM)

| Area | Details |
|---|---|
| Purpose & Success | Co‑create music by authoring/editing `opxyloop-1.0` JSON; changes apply without breaking playback; docVersion stays in sync. |
| Responsibilities | Generate patches or full JSON; respect schema; avoid structural churn unless asked; explain proposed changes when needed. |
| Inputs | Current `doc{docVersion,json}` broadcasts; prompts from human. |
| Outputs | `applyPatch{baseVersion,ops[]}` or `replaceJSON{baseVersion,doc}` via Conductor WS. |
| Invariants | Single source of truth; no seek; structural edits usually next bar. |
| APIs & Protocols | WebSocket envelopes `{type, ts, payload}`; RFC 6902 JSON Patch. |
| Failures & Recovery | Patch rejected (stale): fetch latest, rebase, retry. Validation error: request fix‑it hints from Validator. |
| Observability & KPIs | Patch acceptance rate, docVersion drift, edit latency to “effective at tick/bar”. |
| Runbook | Connect to Conductor WS; subscribe to `doc` and `state`; send patches with correct `baseVersion`. |

## Conductor (watcher + patch gate + broadcaster + metrics)

| Area | Details |
|---|---|
| Purpose & Success | Canonical doc manager; gatekeeper for edits; broadcaster of state/doc/metrics; ensures atomicity and history. |
| Responsibilities | Watch file; validate; apply patches/full replace; atomic write/rename; broadcast; commit batched history; clock/transport state; metrics. |
| Inputs | FS events on `loop.json`; WS inbound: `play/stop/continue/setTempo/applyPatch/replaceJSON`. |
| Outputs | WS outbound: `state`, `doc`, `metrics`, `error`; MIDI transport if internal clock. |
| Invariants | Monotonic `docVersion`; no partial writes; next‑bar apply for structural edits. |
| APIs & Protocols | WebSocket JSON; RFC 6902; Git CLI; file I/O with temp+rename. |
| Failures & Recovery | File conflict: re‑read, reconcile, reject stale; crash during write: recover from last good file or last Git commit; device unplug: notify, panic. |
| Observability & KPIs | jitter p95/p99, msgs/sec, dropped events, clockSource, SHA of canonical JSON, last commit age. |
| Runbook | Start Conductor; open WS; choose clock source; optional “Checkpoint”; on anomalies, issue panic (All Notes Off). |

## Playback Engine (real‑time MIDI)

| Area | Details |
|---|---|
| Purpose & Success | Emit correct MIDI in real time with zero look‑ahead; preserve note lifecycles across edits. |
| Responsibilities | Tick scheduling; active‑notes registry; Note On/Off; CC lane + LFO merge; All Notes Off on stop/hot‑swap/disconnect; implement rate guards. |
| Inputs | Clock ticks (internal or external 24 PPQN); current doc snapshot; transport commands. |
| Outputs | MIDI Note/CC/Clock; All Notes Off on panic/stop. |
| Invariants | Note‑offs never orphaned; CC clamp 0–127; LFO phase reset on Play/bar by default. |
| APIs & Protocols | CoreMIDI (macOS) or RtMidi; MIDI Clock (24 PPQN), Start/Stop/Continue; optional SPP reposition. |
| Failures & Recovery | Missed Note Off detection: periodic reconciliation; device disconnect: panic and pause; overload: shed CCs first. |
| Observability & KPIs | Tick jitter p95/p99, on/off ordering correctness, active‑notes count, shed counts. |
| Runbook | Connect OP‑XY via USB‑C; select MIDI ports; verify clock source; test panic; verify drum map. |

## Web UI (Safari grid)

| Area | Details |
|---|---|
| Purpose & Success | DAW‑style grid editor that edits the same JSON losslessly; immediate feedback with transport controls. |
| Responsibilities | Render doc; edit steps/velocities/CC points; send patches; show transport/clock; optional presence; no seek UI. |
| Inputs | `doc`, `state`, `metrics`. |
| Outputs | `applyPatch` / `replaceJSON`; optional `setTempo`; `play/stop/continue`. |
| Invariants | Lossless round‑trip of JSON; structural edits default next bar. |
| APIs & Protocols | WebSocket to Conductor; canonical JSON formatting; SHA‑256 footer hash optional for integrity. |
| Failures & Recovery | Stale patch rejection: rebase UI buffer; WS drop: reconnect and resync; invalid edit: highlight and show Validator hints. |
| Observability & KPIs | Patch round‑trip latency, rebases per minute, docVersion drift. |
| Runbook | Open `ui/index.html` in Safari; connect WS; edit grid; use transport; trigger “Checkpoint” from UI as needed. |

## Validator / Schema Agent

| Area | Details |
|---|---|
| Purpose & Success | Enforce `opxyloop-1.0` schema; provide actionable fix‑it hints. |
| Responsibilities | Validate on load/patch; normalize/canonicalize; surface errors with pointers; maintain canonical formatting. |
| Inputs | Candidate JSON or patch results; normative spec. |
| Outputs | Pass/Fail with error path/messages; possibly auto‑fix suggestions. |
| Invariants | Spec‑compliant JSON only; stable formatting for diffs. |
| APIs & Protocols | JSON Schema (draft 2020‑12) or custom validator; formatter. |
| Failures & Recovery | On fail: reject write, emit `error{code,details}`; do not partially apply. |
| Observability & KPIs | Validation latency; error rate by category. |
| Runbook | Load spec, validate on every change, refuse non‑conformant writes. |

## Git Historian

| Area | Details |
|---|---|
| Purpose & Success | Durable history with batched commits and manual checkpoints. |
| Responsibilities | Batch commits every 3–5s or on “Checkpoint”; include `docVersion` in messages; manage migrations/versioning. |
| Inputs | File changes; operator “Checkpoint”. |
| Outputs | Git commits; tags for checkpoints; migration scripts if schema bumps. |
| Invariants | Canonical JSON formatting for stable diffs. |
| APIs & Protocols | Git CLI. |
| Failures & Recovery | Commit failure: retry/backoff; crash: recover from last commit. |
| Observability & KPIs | Time since last commit, commit size, rollback success. |
| Runbook | Ensure repo initialized; configure author; verify `.gitignore`; review diffs; checkpoint before risky edits. |

## PR Workflow (GitHub CLI)

- Work via Pull Requests, not direct pushes to `main`.
- Use GitHub CLI (`gh`) to open, review, and merge PRs from the terminal.
- Typical flow:
  - `git checkout -b feat/<short-scope>` and implement changes
  - `git push -u origin HEAD`
  - `gh pr create --base main --head <branch> --title "<title>" --body "<summary + Verify: steps>"`
  - `gh pr list -s open` and `gh pr view <PR#> --web` (or `--comments`)
  - `gh pr merge <PR#> --merge --delete-branch` (use `--squash`/`--rebase` per policy)
  - `git checkout main && git pull --ff-only`

Policy:
- Keep PRs small and vertical with explicit Verify steps and expected outcomes.
- Do not merge with failing CI; adjust tests or tolerances only with justification.

## Test Harness Agent

| Area | Details |
|---|---|
| Purpose & Success | Deterministically verify timing/order/invariants with virtual MIDI and synthetic clocks. |
| Responsibilities | Provide virtual MIDI destination; drive internal/external clock; capture events with timestamps; DSL assertions; metrics capture. |
| Inputs | Test scenarios; expected DSL; current code. |
| Outputs | Pass/fail with timing windows (tolerances, not absolutes); metrics. |
| Invariants | Note‑off never orphaned; no events after stop; CC/LFO rates within caps. |
| APIs & Protocols | Python test runner; virtual MIDI backend; DSL parser. |
| Failures & Recovery | Flaky timing: widen tolerances within budget; parallelize with isolation. |
| Observability & KPIs | Jitter distributions, dropped counts, event throughput. |
| Runbook | Run tests with virtual MIDI; simulate external clock; assert expectations. |

## WebSocket Types (first cut)
- Inbound: `play`, `stop`, `continue`, `setTempo{bpm}`, `applyPatch{baseVersion,ops[]}`, `replaceJSON{baseVersion,doc}`.
- Outbound: `state{transport,clockSource,bpm,barBeatTick}`, `doc{docVersion,json}`, `error{code,message,details}`, `metrics{msgPerSec,jitterMsP95,dropped,clockSrc}`.

## Schema Integration Tasks & Canonicalization
- Author/align JSON Schema and examples per spec; define drum device profile map with GM fallback.
- Define and document OP‑XY CC name map (e.g., `cutoff`→32, `resonance`→33, etc.) and keep runtime mapping in sync with docs.

### Real Device Channels
- OP‑XY “Track 1” listens on MIDI channel 0 (zero‑based). Track 2 → channel 1, …, Track 16 → channel 15.
- Use `midiChannel` per track accordingly when targeting specific tracks. Examples:
  - Track 1: `"midiChannel": 0` (common for synth/voiced tracks)
  - GM drums example: `"midiChannel": 9` (channel 10 one‑based) — use only when you intend to hit a drum engine listening there.
- Symptoms of wrong channel: device UI params don’t move; sound doesn’t react to CC. Fix by aligning `midiChannel` with the intended OP‑XY track.

### Developer Tips
- Prefer `dest: "name:<id>"` for CC lanes/LFOs (see CC map in docs) to avoid magic numbers.
- For real‑device smoke, ensure fixtures set `midiChannel` to the target track (e.g., `loop-cc-lfo-ch0.json` for Track 1).
- Define canonical formatting (ordering, whitespace) and hashing policy.
- Implement validator and canonicalizer; add fixtures under `conductor/tests/fixtures/*.json`.
- Document velocity semantics: Accent ≥105, normal 70–100, ghost 30–55. Guardrail: max ratchet density = 8/step.

## Milestone Handoff & Progress Pointers
- Update this file while working through milestones in `PROJECT_PLAN.md` to leave precise pickup instructions for the next agent.
- Add an entry at the top of the Progress Log with:
  - Milestone ID and title (e.g., `M2 – Engine Skeleton + Note Lifecycle`).
  - Completed: succinct bullet(s) of finished work.
  - Pickup: the next concrete step with file/function paths.
  - Verify: exact command(s)/tests to run; expected outcome; record pass/fail.
  - Context: related commits/checkpoints, `docVersion`, open questions.
- Keep latest entry first; timestamp each entry in ISO format.

### Example Entry
```
[2025-09-13T16:40:00Z] M2 – Engine Skeleton + Note Lifecycle
- Completed: active-notes ledger; demo-note passes with paired on/off ≤5ms tolerance.
- Pickup: implement bar-boundary reconciliation in `conductor/midi_engine.py::reconcile_overdue_offs` and wire panic to transport stop.
- Verify: `make test TESTS=conductor/tests/test_rt_sanity.py::test_orphan_off_guard` and `make demo-note`.
- Context: checkpoint tag `ckpt-m2a`, `docVersion=43`.
```

## Progress Log
- [2025-09-14T00:00:00Z] M3a – CC/LFO Runtime + External Transport (slice)
  - Completed: CC lanes + triangle LFO merge with clamp; name→CC map aligned to OP‑XY spec; channel‑0 real‑device fixture and Make targets; external clock ratio + SPP reposition unit tests; channel mapping/unit guard.
  - Verify: `make test` (10 tests green); device smoke `make play-cc-lfo-ch0 PORT='OP-XY' BPM=60` and confirm cutoff (CC32) ramps and resonance (CC33) wobbles; phase resets on Play/bar.
  - Pickup: add metrics counters and jitter aggregation; external transport behavior tests for Continue vs Start; basic rate guards for CC shed; begin Conductor WS skeleton for state/doc broadcast.
  - Context: branch `feat/m3-cc-lfo-external`, tag `ckpt-m3a`.
- [2025-09-14T00:25:00Z] M3b – Metrics + CC Rate Guard (slice)
  - Completed: Engine metrics counters (note_on/off, cc, shed_cc); per-tick CC rate guard with unit test ensuring CCs shed while notes play; `--metrics` printing in `play_local` and `make play-cc-lfo-ch0` passthrough.
  - Verify: `make test` (11 tests green); device smoke `make play-cc-lfo-ch0 PORT='OP-XY' BPM=60 METRICS=--metrics` and observe metrics printing once per second.
  - Pickup: external transport Continue semantics test; jitter aggregation in `InternalClock`; Conductor WS broadcaster skeleton for `state/doc/metrics`.
  - Context: merged into `main` via PR #5; continue M3 work on new PR.
- [2025-09-14T00:45:00Z] M3c – Jitter + WS Metrics (skeleton)
  - Completed: InternalClock jitter tracking with p95/p99; `clock.get_metrics()`; minimal WS broadcaster skeleton (`conductor/ws_server.py`) using `websockets` to stream metrics once per second; `play_local --ws` flag to enable.
  - Verify: `make test` still green; optional: `pip install websockets` then run `python -m conductor.play_local ... --ws --metrics` and connect to ws://127.0.0.1:8765 to observe metrics JSON.
  - Pickup: integrate broadcaster with Conductor process; add `state` and `doc` payloads; add CI check for optional deps; implement external Continue semantics tests.
  - Context: changes on `main`.
- [2025-09-13T17:20:00Z] M2.5 – Local OP‑XY Player (real device)
  - Completed: Added `conductor/play_local.py` (internal/external clock), `conductor/midi_out.py` (MIDI sink via mido), `conductor/clock.py`; Makefile `play-internal` / `play-external`; `requirements.txt` (mido + python-rtmidi).
  - Verify: With OP‑XY connected, `pip install -r requirements.txt`, then `make play-internal LOOP=conductor/tests/fixtures/loop-drum-accent.json PORT='OP-XY' BPM=120` (OP‑XY should follow and play drums). For external, set OP‑XY as master and run `make play-external ...` and press Play on device.
  - Pickup: Add CC/LFO runtime merge+clamp with phase reset and basic metrics broadcast; then external transport tests and SPP reposition assertions.
  - Context: Branch `feat/m2-local-play`; PR #4.
- [2025-09-13T17:05:00Z] M3 groundwork – DrumKit scheduling + tests
  - Completed: Engine schedules `drumKit` hits at step boundaries with `repeatBars`; GM fallback for `drumMap`; tests cover single-bar counts, repeats, and coexistence with `pattern.steps`.
  - Verify: `make test` (6 tests green).
  - Pickup: Extract `conductor/clock.py` with internal/external sources and a tick bus; add transport tests (Start/Stop/Continue, SPP reposition). Then wire Conductor JSON Patch gate and atomic writes.
  - Context: Branch `feat/m2-drumkit-and-tests`; PR #3.
- [2025-09-13T16:50:00Z] M2 (setup) – Engine Skeleton + Tests
  - Completed: Added `conductor/midi_engine.py`, unit tests in `conductor/tests/test_rt_sanity.py`, and `make test` / `make demo-note` targets.
  - Verify: `make test` passes (3 tests green); `make demo-note` prints on/off pair; `make validate-fixtures` prints `ok` for fixtures.
  - Pickup: Extract clock into `conductor/clock.py` with pluggable internal/external sources; wire engine to a tick bus; add drumKit scheduling tests.
  - Context: Branch `feat/m0-validator-fixtures`; PR #2.
- [2025-09-13T16:42:00Z] P1 – Clock Smoke Test
  - Completed: Added `conductor/clock_smoke.py` and `make clock-smoke` (24 PPQN jitter report over 5s).
  - Pickup: Move clock into a reusable `clock.py` with pluggable sources (internal/external) and message bus to engine; prepare harness hooks to inject synthetic external pulses.
  - Verify: `make clock-smoke` prints p95/p99 jitter; aim for p95 < 2ms on dev. Optimize later using OS timers.
  - Context: Branch `feat/m0-validator-fixtures`; PR #2.
- [2025-09-13T16:35:00Z] M0 – Spec, Fixtures, Canonicalizer
  - Completed: Added validator/canonicalizer (`conductor/validator.py`) with core checks (version, meta, tracks, pattern/steps, drumKit, ccLanes, lfos) and canonical sorting; added fixtures (`conductor/tests/fixtures/*.json`); Makefile targets `validate-fixtures` and `canonicalize-fixtures`.
  - Pickup: Add JSON Schema (`docs/opxyloop-1.0.schema.json`) aligned to spec §1–§10 and wire optional stricter validation behind a `--strict` flag; extend validator checks for chord/degree hints and CC point curves; document hash policy in `PROJECT_PLAN.md` Interfaces.
  - Verify: `make validate-fixtures` prints SHA-256 and `ok` for all fixtures; `make canonicalize-fixtures` rewrites fixtures in canonical format without diffs on second pass.
  - Context: Branch `main`; checkpoint via Git PR #1; Spec present at `docs/opxyloop-1.0.md`.
- (Add newest entries above this line.)

## Verification & DoD Policy
- No milestone or pickup task is “done” until tests are executed and passing locally and in PR CI.
- Always include `Verify:` commands in Progress Log entries and record the pass result (e.g., `make test`, specialized harness checks).
- If a test is flaky, treat it as failing; reduce flakiness (tolerances, fake time) or fix root cause before marking done.
- For runtime changes, include a minimal demo command (e.g., `make demo-note`) that proves behavior alongside unit tests.
