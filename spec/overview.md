# Spec: TraceTalk — Overview

Status: Draft
Owner: Omkar (solo build)

## Purpose
This is the entry point for spec-driven development of TraceTalk. Each module below has its own spec file with explicit requirements, contracts, and acceptance criteria. Build against these specs, not from memory of the PRD — if a spec is ambiguous, fix the spec before writing code.

## Spec index
1. `01-data-model.spec.md` — synthetic telemetry schema (logs, metrics, traces, service graph) and the two seeded incidents.
2. `02-tools-api.spec.md` — contract for the four query tools the agent calls (inputs, outputs, error cases).
3. `03-agent-behavior.spec.md` — system prompt requirements, tool-use loop rules, grounding/citation requirements.
4. `04-ui.spec.md` — chat pane + side panel component contract and event schema.
5. `05-acceptance-criteria.spec.md` — end-to-end scenarios that must pass before demo, including the exact demo question(s).

## Build order
Follow the spec index order — each spec depends on the one before it (data model → tools → agent → UI → acceptance tests). Do not start a spec's implementation until the prior spec's "Definition of done" is met.

## Non-negotiable constraints (apply across all specs)
- No hallucinated answers: every claim the agent makes must trace back to a tool result. This is enforced in `03-agent-behavior.spec.md` and verified in `05-acceptance-criteria.spec.md`.
- No external service auth (no real Splunk/Datadog) — all data is synthetic and local, per `01-data-model.spec.md`.
- Cap tool calls per question at 5 (defined in `03-agent-behavior.spec.md`) to keep demo latency predictable.