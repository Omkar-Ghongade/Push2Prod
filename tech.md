# Technical Design — Conversational Infra/Observability Interface

## 1. High-level architecture

```
┌──────────────┐      ┌───────────────────┐      ┌──────────────────────┐
│  Chat UI      │ <--> │  Agent Loop        │ <--> │  Synthetic Data Store │
│ (chat + panel)│      │ (Claude + tools)   │      │ (logs/metrics/traces) │
└──────────────┘      └───────────────────┘      └──────────────────────┘
```

- **Chat UI**: user-facing conversation pane + a live side panel that renders whatever the agent is currently querying (timeline, log lines, service graph).
- **Agent loop**: Claude with tool-use, given a fixed set of query tools. Each user question triggers a multi-step tool-calling loop until the agent has enough evidence to answer.
- **Synthetic data store**: pre-generated logs, metrics, and traces for a small fake microservices system, held in memory or a lightweight local DB (SQLite/JSON is enough for a day).

## 2. Synthetic system design

Model a simple checkout flow with 4 services:
- `api-gateway`
- `cart-service`
- `payment-service`
- `inventory-service`

Generate for each service, over a simulated time window (e.g. a 2-hour window with minute-level granularity):
- **Metrics**: request rate, p50/p95/p99 latency, error rate.
- **Logs**: structured log lines with timestamp, service, level, message, request_id.
- **Traces**: request_id → ordered list of (service, start_time, duration, status).

Bake in 2–3 incidents by perturbing the generated data at specific timestamps, e.g.:
- `payment-service` p99 latency spikes at 14:00 due to a downstream timeout to `inventory-service`.
- `cart-service` error rate spikes at 15:00 following a simulated bad deploy (add a deploy-event log line just before).
- Cascading failure: `inventory-service` degrades → `payment-service` errors → `api-gateway` 5xxs, all within a tight window.

Keep the generator as a standalone script (`generate_data.py`) so the dataset is reproducible and easy to re-seed if you want to add an incident live during the demo.

## 3. Tool definitions (agent's interface to data)

Define these as function-calling tools passed to Claude:

- `query_metrics(service, metric, start_time, end_time)` → time series values.
- `query_logs(service=None, level=None, start_time, end_time, text_filter=None)` → matching log lines.
- `get_traces(request_id=None, service=None, start_time, end_time, min_duration=None)` → trace spans.
- `get_service_graph()` → static dependency graph (which service calls which) — lets the agent reason about "downstream/upstream."

Keep tool outputs compact (cap rows returned, summarize where needed) so the agent doesn't drown in tokens per hop.

## 4. Agent loop

- System prompt instructs the agent: it is an SRE investigating a live system; it must ground every claim in tool results; it should narrate its investigation step briefly before/after each tool call (this narration drives the side panel).
- Loop: user question → Claude decides tool call → tool executes against synthetic store → result returned to Claude → Claude decides next call or gives final answer.
- Cap at ~5–6 tool calls per question to keep latency reasonable for a live demo.
- Final answer must reference specific evidence ("payment-service p99 jumped from 120ms to 2.1s at 14:02, traces show timeouts calling inventory-service, which had a error spike starting 14:00").

## 5. Side panel rendering

- Each tool call result is also pushed to the UI as a structured event (type: `metric_query`, `log_query`, `trace_query`, `graph_view`).
- UI renders the most recent event type appropriately:
  - metrics → small line chart of the queried window.
  - logs → scrollable log excerpt with the matched lines highlighted.
  - traces → simple horizontal waterfall of spans.
  - graph → service graph with the relevant service(s) highlighted.
- This is what makes the demo feel like "watching it investigate" rather than "waiting for an answer."

## 6. Stack suggestion (optimized for 1-day build)

- **Frontend**: single-page React app (or plain HTML/JS) — chat pane + side panel, kept simple.
- **Backend**: lightweight Node/Python server that holds the synthetic dataset and exposes the tool functions; orchestrates the Claude tool-use loop server-side (keeps API key off the client).
- **Data store**: in-memory / SQLite — no need for a real time-series DB today.
- **Model**: Claude with tool use (function calling), moderate `max_tokens`, tools defined per section 3.

## 7. Build sequencing (see 5hrs-plan.md for time-boxed detail)
1. Synthetic data generator first — everything else depends on it.
2. Tool functions against that data.
3. Agent loop wired to tools (test in a terminal/script before building UI).
4. Chat UI + side panel.
5. Rehearse the 1–2 demo questions end-to-end.

## 8. Key technical risks & mitigations
- **Latency of multi-hop tool calls** → cap tool calls, keep tool responses small, stream narration text so it doesn't feel frozen.
- **Ungrounded answers (hallucination)** → system prompt hard rule: never state a conclusion without a preceding tool call result to back it; consider a final "cite your evidence" pass.
- **Demo fragility** → rehearse the exact 1–2 questions you'll ask live; have the synthetic data deterministic/seeded so results are reproducible.