# Spec: UI — Chat Pane + Side Panel

Status: Draft
Depends on: 03-agent-behavior.spec.md

## 1. Layout
Two-pane layout:
- **Left**: chat pane — text input, message history (user questions + agent final answers).
- **Right**: side panel — live rendering of the agent's current investigation step, driven by the event stream from the backend (Spec 03 §6).

## 2. Event schema (backend → UI)
Each agent turn streams a sequence of events to the frontend:
```json
{"type": "narration", "text": "Checking payment-service latency around 14:00..."}
{"type": "metric_query", "service": "payment-service", "metric": "latency_p99_ms", "points": [...]}
{"type": "log_query", "service": "payment-service", "logs": [...]}
{"type": "trace_query", "traces": [...]}
{"type": "graph_view", "highlighted_services": ["payment-service", "inventory-service"]}
{"type": "final_answer", "text": "..."}
```

## 3. Side panel rendering rules
- `narration` → shown as a small status line above whatever visual is currently rendered.
- `metric_query` → simple line chart of `points`, x-axis time, y-axis value, with the incident window visually distinguishable if within range.
- `log_query` → scrollable monospace list of log lines, ERROR/WARN levels color-coded, matched `text_filter` terms highlighted.
- `trace_query` → horizontal waterfall: one row per service span, width proportional to `duration_ms`, red for `error`/`timeout` status.
- `graph_view` → the 4-service dependency graph (static layout) with `highlighted_services` visually emphasized (e.g. glow/border).
- Panel always shows the **most recent** event; do not stack multiple visuals at once — this is a single evolving view, not a log.

## 4. Chat pane rendering rules
- User messages: plain right-aligned bubbles.
- Agent final answer: left-aligned, rendered after all investigation events for that turn have streamed.
- While investigating, show a lightweight inline indicator in the chat pane (e.g. "investigating...") separate from the side panel detail.

## 5. Non-functional requirements
- Side panel updates must feel live — target <500ms from backend event to render, no batching until the end of the turn.
- No page reload/navigation between questions; single persistent session.
- Styling: minimal but intentional — spacing, one accent color, monospace for data/log content. Do not spend build time beyond this (see 5hrs-plan.md Hour 4 cut guidance).

## 6. Out of scope
- Mobile responsiveness.
- Multi-session/user support.
- Editing/deleting past questions.

## 7. Definition of done
- [ ] Chat pane sends a question to the backend and renders the streamed final answer.
- [ ] Side panel correctly renders at least one example of each event type (`metric_query`, `log_query`, `trace_query`, `graph_view`) using real data from a seeded incident.
- [ ] Full turn (question → investigation events → final answer) completes and renders without manual refresh.