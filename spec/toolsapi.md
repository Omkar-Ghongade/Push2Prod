# Spec: Tools API

Status: Draft
Depends on: 01-data-model.spec.md

These are the only functions the agent may use to gather evidence. Each wraps a query to the local OpenObserve instance (org, streams, and auth per `01-data-model.spec.md` §7) — no local JSON/SQLite fallback. Each must be implemented and tested independently (via hardcoded calls against the real OpenObserve instance) before being exposed to the agent via Anthropic tool-use schema.

**Shared query mechanism**: all tools issue `POST /api/{org}/_search` against the local instance with a SQL query body:
```json
{
  "query": {
    "sql": "SELECT ... FROM tracetalk_logs WHERE ...",
    "start_time": 1754661300000000,
    "end_time": 1754661900000000,
    "from": 0,
    "size": 50
  }
}
```
Note OpenObserve expects `start_time`/`end_time` as **microsecond** unix timestamps — convert from the tool's ISO8601 input before building the query, and convert `_timestamp` values back to ISO8601 in tool output so the agent always sees consistent ISO8601 strings.

## 1. `query_metrics`
**Purpose**: retrieve time-series metric values for a service.

**Input**:
```json
{
  "service": "payment-service",
  "metric": "latency_p99_ms",
  "start_time": "2026-08-08T13:55:00Z",
  "end_time": "2026-08-08T14:10:00Z"
}
```
- `service`: one of the 4 fixed services, or omit for all services.
- `metric`: one of `request_rate | latency_p50_ms | latency_p95_ms | latency_p99_ms | error_rate`.
- `start_time`/`end_time`: ISO8601, must fall within the generated 2-hour window.

**Output**:
```json
{
  "service": "payment-service",
  "metric": "latency_p99_ms",
  "points": [
    {"timestamp": "2026-08-08T13:55:00Z", "value": 180},
    {"timestamp": "2026-08-08T13:56:00Z", "value": 175}
  ]
}
```

**Error cases**: unknown service → error object `{"error": "unknown_service", "valid_services": [...]}`; time range outside window → clamp to window bounds and note it in the response, do not error.

**Implementation**: `SELECT _timestamp, value FROM tracetalk_metrics WHERE __name__ = '{metric}'` + `AND service = '{service}'` if given, ordered by `_timestamp`, against the `tracetalk_metrics` stream.

## 2. `query_logs`
**Purpose**: retrieve matching log lines.

**Input**:
```json
{
  "service": "payment-service",
  "level": "ERROR",
  "start_time": "2026-08-08T14:00:00Z",
  "end_time": "2026-08-08T14:10:00Z",
  "text_filter": "timeout"
}
```
- All fields except `start_time`/`end_time` are optional filters.

**Output**: array of log objects (schema per Spec 01 §4), capped at 50 results, with a `truncated: true/false` flag.

**Implementation**: `SELECT * FROM tracetalk_logs WHERE [service = '{service}'] [AND level = '{level}'] [AND str_match(message, '{text_filter}')]`, `size: 50`; set `truncated: true` if the returned count equals the requested size (a likely-more-results signal).

## 3. `get_traces`
**Purpose**: retrieve trace spans matching criteria.

**Input**:
```json
{
  "request_id": "req_9f21ac",
  "service": "inventory-service",
  "start_time": "2026-08-08T14:00:00Z",
  "end_time": "2026-08-08T14:10:00Z",
  "min_duration_ms": 1000
}
```
- If `request_id` is given, all other filters are ignored and the single matching trace is returned.
- Otherwise filters narrow the set of traces returned.

**Output**: array of trace objects (schema per Spec 01 §5), capped at 10 traces, with a `truncated` flag.

**Implementation**: query `tracetalk_traces` (flattened span records per §7) by `request_id` if given, else by `service`/time range/`duration_ms >= min_duration_ms`; group returned spans back into trace objects by `request_id` in application code before returning to the agent (OpenObserve returns flat rows, not nested trace objects).

## 4. `get_service_graph`
**Purpose**: return the static dependency graph.

**Input**: none.

**Output**:
```json
{
  "edges": [
    {"from": "api-gateway", "to": "cart-service"},
    {"from": "cart-service", "to": "payment-service"},
    {"from": "payment-service", "to": "inventory-service"}
  ]
}
```

## 5. Shared rules
- All timestamps ISO8601 UTC in tool input/output (convert to/from OpenObserve's microsecond unix timestamps internally).
- All tools query the local OpenObserve instance only — no other external calls, no local JSON/SQLite fallback.
- Every tool result MUST be a compact, agent-readable JSON object — no HTML, no pretty-printing, no truncated-without-flag results (silent truncation is forbidden; always set `truncated`).
- Tool errors return a structured `{"error": "...", ...}` object, never throw an unhandled exception the agent loop can't parse — this includes OpenObserve being unreachable (`{"error": "openobserve_unavailable"}`) or returning a malformed/empty result.
- Latency budget: each tool call should return in well under 1 second against the local instance; if a query is slow, narrow the SQL (tighter time range, fewer columns) before adding caching — there's no time budget for a caching layer today.

## 6. Definition of done
- [ ] All 4 tools implemented as functions issuing real `_search` SQL queries against the local OpenObserve instance.
- [ ] Each tool independently tested with at least 2 hardcoded calls (one hit, one edge case) against real ingested data, confirming correct output shape.
- [ ] Confirmed the local OpenObserve instance is reachable and the `tracetalk_logs`/`tracetalk_metrics`/`tracetalk_traces` streams contain the expected row counts (per `01-data-model.spec.md` §7 verification step) before wiring these into the agent loop.
- [ ] Tool schemas written in Anthropic tool-use JSON schema format, ready to pass into the agent loop (Spec 03).