# 5-Hour Build Plan: TraceTalk

Solo build. Optimize for one flawless demo question over broad coverage.

## Hour 1 — Synthetic data + seeded incident
- [ ] Define 4 services: `frontend`, `cart`, `payments`, `inventory`
- [ ] Write `generate_data.py` (or `.js`) producing `logs.json`, `metrics.json`, `traces.json`
- [ ] Bake in the incident: `payments` config change at 14:02 → latency spike → `cart` timeouts → `frontend` errors at 14:04
- [ ] Add one red herring (unrelated `inventory` blip at 14:01)
- [ ] Sanity check: manually read the JSON and confirm the story is traceable by a human first

**Checkpoint:** you can look at the raw data and answer "what caused the frontend errors" yourself.

## Hour 2 — Tool functions (no agent yet)
- [ ] Implement `query_logs()`, `query_metrics()`, `get_traces()` as plain functions over the JSON
- [ ] Test each with hardcoded calls — confirm correct filtering by service/time/level
- [ ] Wrap them behind a simple API layer (even just local function calls if backend+agent are in one process)

**Checkpoint:** you can call all 3 tools manually and get correct, sensible results.

## Hour 3 — Agent loop
- [ ] Define the 3 tools in Anthropic tool-use schema
- [ ] Write the loop: send question → handle `tool_use` → execute → return `tool_result` → repeat → final answer
- [ ] Cap at 5 tool calls; log every call to console for debugging
- [ ] Test with your one target question end-to-end via console/curl (no UI yet)

**Checkpoint:** the agent correctly identifies `payments` as root cause via tool calls, not a hallucinated guess.

## Hour 4 — Chat UI + side panel wiring
- [ ] Minimal chat UI: input box + message list
- [ ] Stream/display each tool call as it happens (name + params + result summary) in a side panel
- [ ] Connect UI to the agent loop from Hour 3
- [ ] Style just enough to look intentional (spacing, monospace for data, one accent color)

**Checkpoint:** asking the question in the UI produces visible tool calls in the panel and a final answer in chat.

## Hour 5 — Polish + rehearse the demo
- [ ] Run the exact demo question 3+ times to confirm consistency
- [ ] Fix any flaky tool-call sequencing or panel rendering glitches
- [ ] Add a short intro screen/message framing the problem (10 seconds of context before the live question)
- [ ] Prepare 1 backup question in case the primary one glitches live
- [ ] Cut anything not needed for the demo path — do not add new features in the last 30 minutes

**Checkpoint:** you can run the full demo, live, without touching code.

## Guardrails throughout
- If a step is taking 2x its allotted time, cut scope (fewer services, simpler panel) rather than pushing the whole plan back
- Real API calls only for the agent loop — everything else is synthetic/local, so no external auth to debug under time pressure
- Keep one working end-to-end version at all times; branch/copy before risky changes