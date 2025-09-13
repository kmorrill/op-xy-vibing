# PR #1 — Bootstrap Docs and Plan

## Title
docs: add normative `opxyloop-1.0` spec; author AGENTS.md and PROJECT_PLAN.md; add milestone handoff protocol

## Summary
- Added `docs/opxyloop-1.0.md` as the authoritative JSON loop spec (persisted from provided attachment).
- Authored `AGENTS.md` with clear roles for all agents (Vibe Coding Agent, Conductor, Playback Engine, Web UI, Validator, Git Historian, Test Harness) including responsibilities, invariants, APIs, failure modes, KPIs, and runbooks.
- Authored `PROJECT_PLAN.md` with detailed milestones (M0–M9), early proof points (P0–P3), a robust real‑time playback engine strategy (no look‑ahead, active‑notes ledger, reconciliation, panic), and a rich test harness spec.
- Added a Progress Log + Handoff protocol to `AGENTS.md` so agents leave precise pickup pointers tied to PROJECT_PLAN milestones.

## Motivation
Establish a shared, unambiguous foundation that the Conductor, Playback Engine, and UI will align to, minimizing ambiguity and preventing regressions (stuck notes, timing drift) via plan‑first + test‑first approach.

## Scope
- Docs and plan only. No runtime code changes in this PR.

## Verification
- `docs/opxyloop-1.0.md` exists and is referenced unconditionally.
- Cross‑references in `AGENTS.md` and `PROJECT_PLAN.md` point to the spec and to each other (milestones, handoff).
- Early proof points are enumerated and actionable (fixtures, clock smoke, demo note) for follow‑up PRs.

## Out of Scope / Follow‑ups
- Scaffold validator/canonicalizer and fixtures (M0).
- Implement clock smoke tests and demo note (P1/P2).
- Conductor + Playback Engine skeletons with test harness wiring (M1–M3).

## Checklist
- [x] References to `docs/opxyloop-1.0.md`
- [x] Invariants captured (no look‑ahead, note‑off guarantee, external clock priority)
- [x] WebSocket types captured (inbound/outbound)
- [x] Milestones with measurable DoD
- [x] Handoff/Progress Log guidance for agents

