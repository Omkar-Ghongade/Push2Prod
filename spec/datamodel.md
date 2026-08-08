# Spec: Data Model — Synthetic Telemetry

Status: Draft
Depends on: none (first spec to implement)

## 1. Services
Fixed set of 4 services forming a checkout flow:
- `api-gateway`
- `cart-service`
- `payment-service`
- `inventory-service`

Dependency edges (for `get_service_graph`):
```
api-gateway -> cart-service
cart-service -> payment-service
payment-service -> inventory-service
```

## 2. Time window
- Simulated window: 2 hours, minute-level granularity (120 data points per metric per service).
- Fixed start timestamp (e.g. `2026-08-08T13:00:00Z`) so the dataset is deterministic across runs.
- Random seed MUST be fixed in `generate_data.py` — reruns produce identical output.

## 3. Metrics schema
Per service, per minute:
```json
{
  "service": "payment-service",
  "timestamp": "2026-08-08T14:02:00Z",
  "request_rate": 42.0,
  "latency_p50_ms": 80,
  "latency_p95_ms": 210,
  "latency_p99_ms": 340,
  "error_rate": 0.01
}
```
Baseline values are randomized within realistic bounds per service; incidents (Section 5) override values in specific windows.

## 4. Logs schema
```json
{
  "timestamp": "2026-08-08T14:02:03Z",
  "service": "payment-service",
  "level": "ERROR",
  "message": "timeout calling inventory-service after 3000ms",
  "request_id": "req_9f21ac"
}
```
- Baseline log volume: a small trickle of INFO logs per service per minute, plus occasional WARN.
- Incident logs (Section 5) are inserted at specific timestamps and MUST be distinguishable by message content and level.
- One `DEPLOY` level log line is inserted for the deploy-triggered incident (Section 5.2), e.g. `"deployed cart-service v1.4.2"`.

## 5. Traces schema
Each simulated request produces a trace: an ordered list of spans across the services it touched.
```json
{
  "request_id": "req_9f21ac",
  "spans": [
    {"service": "api-gateway", "start_offset_ms": 0, "duration_ms": 3400, "status": "error"},
    {"service": "cart-service", "start_offset_ms": 10, "duration_ms": 3380, "status": "error"},
    {"service": "payment-service", "start_offset_ms": 30, "duration_ms": 3340, "status": "error"},
    {"service": "inventory-service", "start_offset_ms": 50, "duration_ms": 3300, "status": "timeout"}
  ],
  "timestamp": "2026-08-08T14:02:03Z"
}
```
- Baseline traces: normal request volume with realistic per-hop durations and `status: "ok"`.
- Incident traces: elevated duration and `status: "error"`/`"timeout"` on the relevant service(s), consistent with the metrics and logs for the same window.

## 6. Seeded incidents (exact — implementation must match)

### 6.1 Incident A — downstream timeout latency spike
- Window: `14:00`–`14:10`.
- Trigger: `inventory-service` begins responding slowly (simulate a degraded dependency, no root-cause log needed there — just elevated latency).
- Effect: `payment-service` p99 latency jumps from baseline (~150–250ms) to 2000–3500ms starting `14:00`, due to synchronous calls to `inventory-service` timing out.
- Logs: `payment-service` ERROR logs starting `14:00` with message containing `"timeout calling inventory-service"`.
- Traces: spans for requests in this window show `inventory-service` span duration elevated (>2500ms) and `status: "timeout"`.

### 6.2 Incident B — deploy-triggered error burst
- Window: `15:00`–`15:08`.
- Trigger: a `DEPLOY` log line for `cart-service` at `14:59:50`.
- Effect: `cart-service` error_rate jumps from baseline (~0.5–1%) to 15–25% starting `15:00`.
- Logs: `cart-service` ERROR logs starting `15:00` with message containing `"null pointer"` or similar deploy-shaped bug signature.
- Traces: requests touching `cart-service` in this window show `status: "error"` at the `cart-service` span; upstream `api-gateway` span also shows `status: "error"` (propagated failure), downstream services not reached.

## 7. Storage — OpenObserve (local instance)
Data is generated as before (Sections 3–6, deterministic, fixed seed) but ingested into a locally running OpenObserve instance instead of written to local JSON files.

- **Instance**: `http://localhost:5080`, org `default` (or a dedicated org, e.g. `tracetalk`, created via the UI first if isolation from other local data is wanted).
- **Auth**: HTTP Basic, `base64(ZO_ROOT_USER_EMAIL:ZO_ROOT_USER_PASSWORD)` — same credentials the local instance was started with.
- **Streams** (OpenObserve's term for a table/index):
  - `tracetalk_logs` — one JSON doc per log line (schema per Section 4), ingested via `POST /api/{org}/tracetalk_logs/_json` (bulk array body).
  - `tracetalk_metrics` — one JSON doc per metric point per service per minute, ingested via `POST /api/{org}/ingest/metrics/_json`, using OpenObserve's metrics JSON shape: `{"__name__": "<metric_name>", "__type__": "gauge", "service": "<service>", "_timestamp": <unix_ms>, "value": <float>}`. Emit one stream of docs per metric name (`request_rate`, `latency_p50_ms`, etc.).
  - `tracetalk_traces` — spans ingested via OTLP (`POST /api/{org}/v1/traces`) if the generator can emit OTLP-shaped payloads, OR as a `_json` stream of flattened span records (one doc per span, with `request_id`, `service`, `start_offset_ms`, `duration_ms`, `status`, `timestamp`) if OTLP formatting isn't worth the time — implementer's choice, but pick the JSON-stream route first; it's simpler and sufficient for SQL querying in Spec 02.
- **Service graph**: static, small (4 edges) — keep this as a local constant/JSON in the app rather than ingesting it into OpenObserve; it isn't time-series data and doesn't benefit from being queried via SQL.
- **Generator script**: `generate_data.py`, deterministic (fixed seed), pushes all records to the three streams above via HTTP calls to the local instance. Must be idempotent-safe to rerun (either clear the streams first via the Stream API, or use a fresh org per run) so reruns don't double-count incidents.
- **Verification**: after running the generator, confirm ingestion by querying each stream's count via the OpenObserve UI or a simple `SELECT COUNT(*) FROM tracetalk_logs` through `_search` before moving to Spec 02.

## 8. Definition of done
- [ ] Running `generate_data.py` twice produces byte-identical output.
- [ ] A human can manually inspect the data and correctly identify both incidents and their root causes without using the agent.
- [ ] Data volume is small enough that `02-tools-api.spec.md` queries return in milliseconds (no need for indexing/optimization).