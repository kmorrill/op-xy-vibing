# OP‑XY Agents Overview

This repository defines two distinct agent roles that collaborate on the OP‑XY project. Each agent has a different focus, but they share a common foundation: **loop.json** is the single source of truth for the musical loop, and all edits must respect the concurrency model built into the system. This file provides a high‑level description of the two modes and captures a handful of general principles that apply to both.

## Modes

### Feature‑coding assistant

The feature‑coding assistant develops and tests the software stack that powers the OP‑XY, including the Conductor, playback engine, validator, web UI, and test harness. It writes Python and JavaScript, manipulates Git, runs automated tests, and interacts with developers via pull requests. Detailed guidance for this mode lives in [**feature-coding-assistant.md**](feature-coding-assistant.md). That document covers data model nuances, concurrency and scheduling rules, how to start and validate the Conductor, expectations for tests and metrics, and how to safely interact with real hardware.

### Musical‑coding assistant

The musical‑coding assistant is the creative partner that edits opxyloop-1.0 JSON to co‑author loops with a human. It proposes small, reversible changes; offers A/B comparisons; and asks concise questions to refine the user's intent. The details of this role live in [**musical-coding-assistant.md**](musical-coding-assistant.md), which includes playbooks, editing heuristics, objective templates, and patterns for human‑in‑the‑loop collaboration.

## General principles

The following rules apply to **both** assistants. Regardless of whether you are editing code or music, these principles keep the system stable and predictable:

* **Single source of truth:** The loop lives in loop.json (using the opxyloop-1.0 schema). Do not maintain parallel state; always read and write to this file via the appropriate APIs.

* **Concurrency via docVersion:** Each change to loop.json increments a docVersion. When sending a patch or full replacement, include the base docVersion to avoid clobbering more recent edits. If a patch is rejected because the version is stale, fetch the latest version, rebase your changes, and retry.

* **Minimal, reversible edits:** Prefer RFC 6902 JSON Patch operations that touch only the fields you intend to change. Avoid structural churn unless explicitly required. This applies equally to feature changes (e.g. adding a new LFO) and musical tweaks (e.g. adjusting swing).

* **Schema and range validation:** Always validate candidate JSON against the opxyloop-1.0 schema. Ensure MIDI note and CC values are within \[0, 127\], durations are non‑negative, LFO parameters are sane, and structural invariants hold. Reject and fix invalid documents before proceeding.

* **No look‑ahead scheduling:** The playback engine should only schedule events on the current tick; never rely on future information. Maintain an active‑notes ledger and always emit Note Off events for every Note On, even during hot‑swap or live editing.

* **LFO and CC semantics:** LFOs reset at play and bar boundaries by default, and CC values clamp into the MIDI range. Use conservative depths and rates unless a human requests experimentation.

* **Human in the loop:** For ambiguous or subjective choices—whether technical (server restart vs. rebase) or musical (brighter hats vs. warmer pad)—ask the user. Provide clear options and respect their selection before committing.

* **History and reproducibility:** Keep a log of what you changed and why. Persist seeds and randomization parameters so that edits can be reproduced. When the loop evolves, record a short rationale alongside the diff.

Refer to the dedicated assistant documents for mode‑specific rules, workflows and examples.

---

