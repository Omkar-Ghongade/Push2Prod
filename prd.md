# PRD — Conversational Interface for Infrastructure Observability

## 1. Problem
Debugging distributed systems today means hand-writing queries across disconnected tools (Splunk, Datadog, Grafana, log greps) and manually stitching together logs, metrics, and traces to find root cause. This is slow, requires deep tool-specific query knowledge, and doesn't scale to on-call engineers who aren't experts in every service.

## 2. Vision
Replace the query-builder UI with a conversation. An engineer asks a plain-language question about system behavior ("why did checkout latency spike at 2pm?") and an agent investigates live — issuing real queries against logs/metrics/traces, following the evidence across services, and showing its reasoning trail alongside the answer. Not a chatbot that summarizes an alert; an agent that debugs *with* you, transparently.

## 3. Target user
On-call engineers / SREs during an active investigation, and engineers doing post-incident root-cause analysis.

## 4. Core user story
> "As an on-call engineer, when I see a latency spike, I want to ask what caused it in plain English and see the agent trace through logs, metrics, and service dependencies to find the root cause — so I don't have to manually correlate three different tools under pressure."

## 5. Scope for hackathon (1 day)

### In scope
- Synthetic microservices system (e.g. e-commerce checkout: `api-gateway → cart-service → payment-service → inventory-service`) with generated logs, metrics, and traces.
- 2–3 seeded "incidents" baked into the synthetic data (e.g. latency spike from a downstream timeout, error burst from a bad deploy, cascading failure from a dependency outage).
- Chat interface where the user asks questions in natural language.
- Agent with tool access to query the synthetic data (`query_logs`, `query_metrics`, `get_traces`, `get_service_graph`).
- Live side panel that visually renders what the agent is querying as it investigates (timeline, log excerpt, service graph highlight) — this is the demo "wow" moment.
- Agent answer is grounded in retrieved data, not hallucinated — must cite which logs/metrics led to its conclusion.

### Explicitly out of scope (for the day)
- Real Splunk/Datadog/Prometheus integration (auth + setup overhead not worth it for a 1-day demo).
- Write actions / auto-remediation (this version is read-only investigation, not an acting agent).
- Multi-tenant, auth, persistence across sessions.
- Handling arbitrary real-world infra — one synthetic system is enough to prove the concept.

## 6. Success criteria (demo day)
- Live, unscripted question asked on stage gets a correct, evidence-backed answer within ~10–15 seconds.
- Side panel visibly shows the agent's investigation steps (not just a spinner then an answer).
- At least one multi-hop question works end-to-end (e.g. "what changed right before errors started, and which service caused it?") — this is what separates it from a search bar.

## 7. Why this clears "audacious"
- **New interface**: conversational, evidence-grounded investigation replaces query languages (PromQL/SPL) and static dashboards.
- **Redefines a category**: today's AI-observability tools summarize alerts after the fact; this investigates live, interactively, like a colleague debugging with you.

## 8. Risks
- Synthetic data must feel realistic enough that the demo doesn't look canned — invest early time here.
- Tool-calling loop must be fast enough (few seconds per hop) to feel conversational, not laggy.
- Multi-hop reasoning is the hardest part to get right — budget the most time here, not on UI polish.