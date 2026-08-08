# Spec: Acceptance Criteria

Status: Draft
Depends on: 01, 02, 03, 04 (all prior specs)

These are the scenarios that must pass, end-to-end through the real UI, before the project is considered demo-ready.

## Scenario 1 — Incident A (downstream timeout)
**Question**: "Why did payment-service latency spike around 2pm?"

**Must show**:
- Side panel: metric_query on `payment-service` `latency_p99_ms` showing the spike at 14:00.
- Side panel: log_query or trace_query surfacing the `"timeout calling inventory-service"` evidence.
- Final answer names `inventory-service` as root cause and cites specific values (e.g. "p99 went from ~180ms to ~3100ms starting 14:00, traces show timeouts calling inventory-service").

**Pass condition**: correct root cause identified, with cited evidence, in under 6 tool calls, end-to-end through the UI.

## Scenario 2 — Incident B (deploy-triggered errors)
**Question**: "What caused the error spike in cart-service around 3pm?"

**Must show**:
- Side panel: metric_query showing `cart-service` `error_rate` jump at 15:00.
- Side panel: log_query surfacing the `DEPLOY` log line at 14:59:50 and the subsequent ERROR logs.
- Final answer connects the deploy event to the error spike with a plausible causal statement, citing the deploy timestamp and log content.

**Pass condition**: correct root cause identified, with cited evidence, in under 6 tool calls.

## Scenario 3 — Multi-hop (the demo "wow" question)
**Question**: "What changed right before things went wrong, and which service is responsible?"
(Ambiguous by design — no service/time named, forces the agent to search broadly then narrow.)

**Must show**:
- Agent uses `get_service_graph` and/or scans multiple services' metrics to locate the anomaly before drilling in.
- At least 3 distinct tool call types used in one turn (e.g. metrics → graph → logs, or metrics → traces → logs).
- Correctly identifies whichever incident window is closest to "now" in the demo framing, or asks a clarifying narrowing question if genuinely ambiguous — this behavior must be decided and tested, not left to chance.

**Pass condition**: agent reaches a correct, evidence-grounded answer without being told which service or time window to look at.

## Scenario 4 — Out-of-scope question (negative test)
**Question**: "Why is checkout slow in the EU region?" (no region data exists in the synthetic model)

**Must show**: agent states the data doesn't support region-level breakdown rather than fabricating an answer.

**Pass condition**: no hallucinated claim; agent explicitly flags the limitation.

## Scenario 5 — Latency / demo timing
**Must show**: Scenarios 1 and 2 each complete (question submitted → final answer rendered) in under ~15 seconds.

**Pass condition**: timed manually at least 3 times per scenario for consistency; if inconsistent, revisit Spec 03 §3 tool-call cap or Spec 02 response sizes.

## Final demo readiness checklist
- [ ] Scenario 1 passes reliably (3/3 runs).
- [ ] Scenario 2 passes reliably (3/3 runs).
- [ ] Scenario 3 (multi-hop) passes at least once, ideally reliably — this is the differentiator, worth extra iteration time.
- [ ] Scenario 4 (negative test) passes — no hallucination under pressure.
- [ ] Scenario 5 timing consistently under 15s.
- [ ] Primary demo question selected and rehearsed; backup question identified per `5hrs-plan.md`.