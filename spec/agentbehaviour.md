# Spec: Agent Behavior

Status: Draft
Depends on: 02-tools-api.spec.md

## 1. Role
The agent acts as an SRE investigating a live incident. It is given a user question about system behavior and must investigate using only the tools in Spec 02, then answer with evidence.

## 2. System prompt requirements
The system prompt MUST instruct the agent to:
- Never state a causal or factual claim about system behavior without a preceding tool call that supports it.
- Prefer narrow, targeted tool calls over broad ones (e.g. query a specific service + tight time range, not "all services, all time").
- Emit a brief one-line narration before or after each tool call describing what it's checking and why (this narration drives the UI side panel per Spec 04) — e.g. `"Checking payment-service latency around 14:00..."`.
- Use `get_service_graph` when reasoning about upstream/downstream causality, not just when explicitly asked about dependencies.
- Stop investigating once it has sufficient evidence for a confident answer — do not exhaust the tool-call budget unnecessarily.
- If evidence is inconclusive after the tool-call budget, say so explicitly rather than guessing.

## 3. Tool-use loop
1. Receive user question.
2. Claude proposes a tool call (or gives a final answer if no investigation is needed).
3. Backend executes the tool call against Spec 02 functions, returns the result as `tool_result`.
4. Repeat from step 2.
5. Hard cap: **5 tool calls per question**. On reaching the cap, the agent must produce a final answer using whatever evidence it has gathered, explicitly noting if it's incomplete.

## 4. Grounding / citation requirement
- The final answer MUST reference specific values or log lines retrieved via tool calls (e.g. "p99 latency jumped from 180ms to 3100ms at 14:02", not "there was a latency spike").
- If asked a question the data cannot answer (e.g. about a service outside the fixed 4, or a time outside the window), the agent must say so rather than fabricating an answer.

## 5. Multi-hop reasoning requirement
For questions like "what changed right before errors started, and which service caused it," the agent must chain tool calls: e.g. `query_metrics` on the symptomatic service → `get_service_graph` to find upstream/downstream → `query_metrics`/`query_logs` on the dependency → `get_traces` to confirm causality. This chaining behavior is the core capability being demonstrated and should be tested explicitly (see Spec 05).

## 6. Output format for the backend
Each agent turn should produce, in order:
- Zero or more `(narration_text, tool_call)` pairs.
- A final `answer_text` once investigation is complete.

This structure is what Spec 04's UI consumes to drive the side panel.

## 7. Definition of done
- [ ] System prompt drafted and tested against both seeded incidents (Spec 01 §6) via direct script/terminal calls (no UI).
- [ ] Agent correctly identifies root cause for Incident A and Incident B independently.
- [ ] Agent successfully performs the multi-hop reasoning case (Section 5) at least once, verified manually.
- [ ] Tool-call cap enforced and tested (simulate a case where it would exceed 5 calls, confirm graceful degradation).