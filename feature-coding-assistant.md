# Feature‑Coding Assistant

This document guides the agent responsible for building and testing the OP‑XY software stack. It distills the extensive technical specification found in the original **AGENTS.md** into actionable guidance. The goal of this assistant is to deliver a robust, testable system that manages the loop JSON, schedules MIDI in real time, exposes a web‑based editor, and provides hooks for development and deployment.

## Purpose and scope

The feature‑coding assistant:

* Develops and maintains services such as the **Conductor**, **Playback Engine**, **Validator**, **Web UI**, and supporting tools.

* Ensures all components interact correctly with loop.json (the single source of truth for musical state) and maintain concurrency via docVersion.

* Writes code, configures services, and writes tests. It interacts with the developer via Git and the terminal, not via the audio interface.

* Follows runbooks to start, restart, and validate servers, and provides clear commands for the user to execute when required.

## Data model and concurrency

The core data model is defined in docs/opxyloop-1.0.md. It specifies loop.json as a document containing tracks, steps, CC lanes, LFOs, and meta fields (tempo, length, etc.). Key points:

* **Single source of truth:** loop.json must always reflect the current musical loop. Edits are applied via JSON Patch or full replacement; the assistant must not hold hidden state.

* **docVersion:** Each write increments docVersion. Every patch or replacement must include the baseVersion it was derived from. If the Conductor rejects a patch due to a version mismatch, fetch the latest document, reapply your changes, and resend the patch.

* **Structural vs. non‑structural edits:** Edits that change the tempo, length, track definitions, or other structural aspects are scheduled for the next bar by default. Parameter tweaks (step velocity, CC point, etc.) are applied at the next tick. Use the applyNow override only when necessary.

* **Invariants:**

* **No look‑ahead:** Schedule events based only on the current tick. Do not assume future steps when emitting MIDI. Maintain an active‑notes ledger and always send a Note Off for each Note On.

* **Note‑off guarantee:** The system must never leave hanging notes. Hot‑swaps, resets, or transport changes must emit All Notes Off.

* **LFO phase resets:** LFOs reset on Play and bar boundaries by default. Free‑running LFOs are future work.

* **Rate guards:** Shed CC bursts that exceed \~2.5k messages/s globally or \~800 per track; prioritise audible events.

## System components and responsibilities

Below is a high‑level summary of the major components. Full implementation details live in the codebase, but this guide captures the key responsibilities and interactions.

### Conductor (watcher, patch gate, broadcaster, metrics)

* **Purpose:** Manages the canonical loop.json. Watches the file for changes, validates patches, schedules structural edits, and broadcasts updated documents and metrics over WebSocket.

* **Responsibilities:**

* Validate incoming patches against the schema and invariants.

* Apply patches atomically: write to a temp file, rename on success, and increment docVersion.

* Schedule structural changes at bar boundaries by default; allow applyNow overrides.

* Broadcast state, doc, and metrics messages over WebSocket to subscribed clients.

* Maintain metrics such as message throughput, jitter, and doc hash.

* **Failure and recovery:** On stale patch, reject and instruct the client to rebase. On validation error, emit an error with details. Recover from crashes using the last good loop.json or latest Git commit.

### Playback engine (real‑time MIDI)

* **Purpose:** Converts loop.json into real‑time MIDI events without look‑ahead, guaranteeing note lifecycles.

* **Responsibilities:**

* Track the current tick and bar position from the clock (internal or external 24 PPQN).

* Schedule Note On and Note Off events from step definitions and active LFOs/CC lanes.

* Merge base CC values with LFO offsets and clamp to 0–127.

* Emit All Notes Off on stop, hot‑swap, or disconnect.

* **Inputs:** Clock ticks, loop.json snapshots, transport commands (Play/Stop/Continue), and optional Song Position Pointer (SPP).

* **Outputs:** MIDI Note, CC, and Clock messages; panic messages on error.

### Validator / Schema agent

* **Purpose:** Enforces the opxyloop-1.0 JSON schema and supplies actionable fix‑it hints.

* **Responsibilities:**

* Validate each proposed patch or replacement before the Conductor commits it.

* Normalise and canonicalise JSON to maintain stable formatting and hash consistency.

* Provide clear error messages with JSON pointer paths and suggestions for repair.

### Web UI (grid editor)

* **Purpose:** Offers a browser‑based grid editor for editing steps, velocities, CC points, and LFO curves. It never seeks; it only edits the canonical JSON.

* **Responsibilities:**

* Render the current loop.json and allow step toggling, velocity editing, CC drawing, and LFO editing.

* Send JSON Patch messages (applyPatch) or full replacements (replaceJSON) to the Conductor via WebSocket.

* Display transport status, clock source, and metrics; reflect external tempo changes but do not send transport commands.

### Git Historian and PR workflow

* **Purpose:** Provide durable history, checkpoints, and proper collaboration via Git and GitHub PRs.

* **Guidelines:**

* Work on feature branches. Keep pull requests small and vertical, with explicit Verify steps describing how to test the change.

* Commit batched changes every few seconds or on explicit checkpoint. Include the docVersion in commit messages for traceability.

* Use gh to create, review, and merge PRs. Do not merge with failing CI.

* Run unit tests and integration tests before raising a PR. Document test results in your commit or PR description.

## Starting and validating services

* **Server startup:** Servers (Conductor and playback engine) are user‑started. The agent first attempts to start them locally. If sandbox restrictions prevent direct execution, it should output a single, copy‑pasteable command for the user. After the user runs it, the agent validates health via HTTP (curl) and optional WebSocket checks.

* **Health checks:** Use curl to fetch /api/doc or / and confirm the server responds. For WebSocket servers, send a minimal subscribe message and expect a doc/state pair.

* **Restart commands:** Provide one‑liner commands that stop any prior processes (e.g. pkill) and start a fresh instance with the proper flags (\--loop, \--port, \--clock-source, \--ws-port, etc.).

* **Runbook:** Always panic the real device (send All Notes Off) before starting or stopping a service. Free the WS port (8765) if needed. Then run the new command.

## Testing and metrics

The feature‑coding assistant is responsible for implementing and maintaining a **test harness** that provides deterministic verification of timing, ordering, and invariants.

* **Virtual MIDI tests:** Use a virtual MIDI destination and synthetic clocks to exercise Note On/Off ordering, CC merges, rate guards, and structural scheduling. A DSL can be used to specify expected sequences and tolerances.

* **Integration tests:** Use a Python WebSocket client to subscribe to metrics and doc/state broadcasts. Assert that metrics (e.g. jitter p95) remain within budget and that doc versions increment correctly.

* **Smoke tests on real devices:** Provide make targets such as make play-cc-lfo-ch0 that run a short loop through the OP‑XY via the playback engine. Listen for expected audio patterns (e.g. alternating loud/quiet notes) and confirm there are no stuck notes.

* **Metrics:** Track and expose metrics such as messages per second, jitter percentiles, dropped events, and clock source. Use these to tune performance and detect regressions.

## Real‑device safety

When working with a physical OP‑XY or another MIDI device:

* Always stop all running processes before starting a new test. Send a panic (Sustain Off, All Sound Off, All Notes Off) to the device.

* Ensure the correct MIDI channel is used for each track. Track 1 uses channel 0 (zero‑based). Use channel 9 only for GM‑style drum engines.

* If nothing happens when editing CCs, verify that the midiChannel in the JSON matches the track you’re controlling.

## Progress log and handoff

Maintaining a clear progress log is crucial when multiple agents collaborate. Each milestone entry should include:

* The date and time (ISO 8601).

* A succinct description of the completed work.

* The next concrete step (pickup task), including file paths and function names where appropriate.

* Commands to verify the work (unit tests, make targets, or device smoke tests) and expected outcomes.

* References to related commits or checkpoint tags and any open questions.

The newest entry belongs at the top of the log.

## Verification and definition of done

Nothing is “done” until tests pass locally and in CI. Always include Verify: commands in your task descriptions and confirm that they pass. If a test is flaky, treat it as failing; fix the root cause or adjust tolerances appropriately. For runtime changes, include a short demo (e.g. make demo-note) that proves the behaviour alongside unit tests.

---

This guide is intended to help the feature‑coding assistant work effectively within the OP‑XY project. It focuses on software correctness, timing determinism, developer workflow, and safe interaction with real devices. For musical collaboration and loop creation, refer instead to [musical-coding-assistant.md](http://musical-coding-assistant.md).

---

