#!/usr/bin/env python3
"""Generate deterministic synthetic telemetry for TraceTalk — OpenObserve edition.

Timestamps are relative to "now" so data always falls within OpenObserve's
5-hour ingestion window. Incidents are ~1h ago and ~10min ago.

Spec: spec/datamodel.md
Run:  python3 generate_data.py
Ingests into: tracetalk_logs, tracetalk_metrics, tracetalk_traces
Auth: reads ZO_ROOT_USER_EMAIL and ZO_ROOT_USER_PASSWORD from environment.
"""

import base64
import json
import os
import random
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ── Config ─────────────────────────────────────────────────────────────
OO_BASE = os.environ.get("OO_BASE_URL", "http://localhost:5080")
OO_ORG = os.environ.get("OO_ORG", "default")
OO_USER = os.environ.get("ZO_ROOT_USER_EMAIL", "")
OO_PASS = os.environ.get("ZO_ROOT_USER_PASSWORD", "")

if not OO_USER or not OO_PASS:
    print("ERROR: Set ZO_ROOT_USER_EMAIL and ZO_ROOT_USER_PASSWORD environment variables.")
    sys.exit(1)

AUTH_HEADER = "Basic " + base64.b64encode(f"{OO_USER}:{OO_PASS}".encode()).decode()

# ── Time window (relative to now) ────────────────────────────────────
random.seed(42)

NOW = int(time.time())
START_DT = NOW - 2 * 3600  # 2 hours ago
MINUTES = 120              # 2-hour window, minute-level

# Incident offsets from START_DT (in minutes)
INCIDENT_A_START = 50   # ~1h10m ago → ~1h ago (10 min window)
INCIDENT_A_END = 60
INCIDENT_B_START = 110  # ~10m ago → ~2m ago (8 min window)
INCIDENT_B_END = 118
DEPLOY_MINUTE = 109     # 1 minute before Incident B

# Print the actual times for reference
def fmt_unix(sec):
    return datetime.fromtimestamp(sec, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

print(f"Window: {fmt_unix(START_DT)} → {fmt_unix(START_DT + MINUTES*60)}")
print(f"Incident A: {fmt_unix(START_DT + INCIDENT_A_START*60)} → {fmt_unix(START_DT + INCIDENT_A_END*60)}")
print(f"DEPLOY log: {fmt_unix(START_DT + DEPLOY_MINUTE*60 + 50)}")
print(f"Incident B: {fmt_unix(START_DT + INCIDENT_B_START*60)} → {fmt_unix(START_DT + INCIDENT_B_END*60)}")

# ── Constants ──────────────────────────────────────────────────────────
SERVICES = ["api-gateway", "cart-service", "payment-service", "inventory-service"]

SERVICE_BASELINES = {
    "api-gateway":       {"request_rate": (80,120), "latency_p50_ms": (20,40),  "latency_p95_ms": (50,90),   "latency_p99_ms": (80,150),  "error_rate": (0.005,0.015)},
    "cart-service":      {"request_rate": (70,110), "latency_p50_ms": (15,35),  "latency_p95_ms": (40,80),   "latency_p99_ms": (60,120),  "error_rate": (0.005,0.01)},
    "payment-service":   {"request_rate": (40,80),  "latency_p50_ms": (30,60),  "latency_p95_ms": (80,150),  "latency_p99_ms": (150,250), "error_rate": (0.005,0.015)},
    "inventory-service": {"request_rate": (30,60),  "latency_p50_ms": (10,25),  "latency_p95_ms": (30,60),   "latency_p99_ms": (50,100),  "error_rate": (0.003,0.01)},
}

METRIC_NAMES = ["request_rate", "latency_p50_ms", "latency_p95_ms", "latency_p99_ms", "error_rate"]


def rand_between(lo, hi):
    return random.uniform(lo, hi)


def fmt_ts(dt_seconds):
    return datetime.fromtimestamp(dt_seconds, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_us(dt_seconds):
    return int(dt_seconds * 1_000_000)


# ── HTTP helpers ───────────────────────────────────────────────────────
def oo_request(method, path, body=None):
    url = f"{OO_BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", AUTH_HEADER)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        print(f"  HTTP {e.code}: {body_text[:200]}")
        return None


def delete_stream(name):
    oo_request("DELETE", f"/api/{OO_ORG}/streams/{name}")


def ingest_json(stream, docs):
    return oo_request("POST", f"/api/{OO_ORG}/{stream}/_json", body=docs)


def ingest_metrics(docs):
    return oo_request("POST", f"/api/{OO_ORG}/ingest/metrics/_json", body=docs)


def count_stream(stream):
    body = {
        "query": {
            "sql": f"SELECT COUNT(*) as cnt FROM {stream}",
            "start_time": to_us(START_DT),
            "end_time": to_us(NOW + 300),
            "from": 0,
            "size": 1,
        }
    }
    resp = oo_request("POST", f"/api/{OO_ORG}/_search", body=body)
    if resp and isinstance(resp.get("hits"), list) and resp["hits"]:
        return resp["hits"][0].get("cnt", 0)
    return None


# ── Data generation ───────────────────────────────────────────────────
def generate_metrics_docs():
    docs = []
    for svc in SERVICES:
        bl = SERVICE_BASELINES[svc]
        for m in range(MINUTES):
            ts_sec = START_DT + m * 60
            ts_us = to_us(ts_sec)

            rr = round(rand_between(*bl["request_rate"]), 1)
            p50 = round(rand_between(*bl["latency_p50_ms"]))
            p95 = round(rand_between(*bl["latency_p95_ms"]))
            p99 = round(rand_between(*bl["latency_p99_ms"]))
            er = round(rand_between(*bl["error_rate"]), 4)

            # Incident A: payment-service p99 spike
            if svc == "payment-service" and INCIDENT_A_START <= m <= INCIDENT_A_END:
                p99 = round(rand_between(2000, 3500))
                p95 = round(rand_between(800, 1500))
                p50 = round(rand_between(200, 500))
                er = round(rand_between(0.05, 0.12), 4)

            # Incident A secondary: inventory-service elevated latency
            if svc == "inventory-service" and INCIDENT_A_START <= m <= INCIDENT_A_END:
                p99 = round(rand_between(2500, 3500))
                p95 = round(rand_between(1000, 2000))
                p50 = round(rand_between(300, 800))

            # Incident B: cart-service error_rate jump
            if svc == "cart-service" and INCIDENT_B_START <= m <= INCIDENT_B_END:
                er = round(rand_between(0.15, 0.25), 4)
                p99 = round(rand_between(200, 450))
                p95 = round(rand_between(100, 250))

            values = {"request_rate": rr, "latency_p50_ms": p50, "latency_p95_ms": p95, "latency_p99_ms": p99, "error_rate": er}
            for name in METRIC_NAMES:
                docs.append({
                    "__name__": name,
                    "__type__": "gauge",
                    "service": svc,
                    "_timestamp": ts_us,
                    "value": float(values[name]),
                })
    return docs


def generate_log_docs():
    docs = []
    counter = [0]
    def rid():
        counter[0] += 1
        return f"req_{counter[0]:06d}"

    for m in range(MINUTES):
        ts_sec = START_DT + m * 60
        for svc in SERVICES:
            for _ in range(random.randint(1, 3)):
                docs.append({"timestamp": fmt_ts(ts_sec + random.randint(0, 59)), "service": svc, "level": "INFO", "message": "request processed successfully", "request_id": rid()})
            if random.random() < 0.2:
                docs.append({"timestamp": fmt_ts(ts_sec + random.randint(0, 59)), "service": svc, "level": "WARN", "message": "elevated response time detected", "request_id": rid()})

    # Incident A: payment-service timeout ERROR logs
    for m in range(INCIDENT_A_START, INCIDENT_A_END + 1):
        ts_sec = START_DT + m * 60
        for _ in range(random.randint(3, 8)):
            docs.append({"timestamp": fmt_ts(ts_sec + random.randint(0, 59)), "service": "payment-service", "level": "ERROR", "message": "timeout calling inventory-service after 3000ms", "request_id": rid()})

    # Incident B: DEPLOY at 14:59:50, then cart-service errors
    deploy_sec = START_DT + DEPLOY_MINUTE * 60 + 50
    docs.append({"timestamp": fmt_ts(deploy_sec), "service": "cart-service", "level": "DEPLOY", "message": "deployed cart-service v1.4.2", "request_id": rid()})

    for m in range(INCIDENT_B_START, INCIDENT_B_END + 1):
        ts_sec = START_DT + m * 60
        for _ in range(random.randint(5, 15)):
            docs.append({"timestamp": fmt_ts(ts_sec + random.randint(0, 59)), "service": "cart-service", "level": "ERROR", "message": "null pointer exception in checkout handler", "request_id": rid()})

    docs.sort(key=lambda x: x["timestamp"])
    return docs


def generate_trace_docs():
    docs = []
    counter = [0]
    def rid():
        counter[0] += 1
        return f"req_{counter[0]:06d}"

    for m in range(MINUTES):
        ts_sec = START_DT + m * 60
        for _ in range(random.randint(2, 4)):
            r = rid()
            base = random.randint(20, 60)
            span_ts = ts_sec + random.randint(0, 59)
            for svc, offset, dur, status in [
                ("api-gateway", 0, base + random.randint(5, 20), "ok"),
                ("cart-service", random.randint(5, 15), base + random.randint(10, 30), "ok"),
                ("payment-service", random.randint(15, 30), base + random.randint(20, 50), "ok"),
                ("inventory-service", random.randint(25, 45), base + random.randint(10, 40), "ok"),
            ]:
                docs.append({"request_id": r, "service": svc, "start_offset_ms": offset, "duration_ms": dur, "status": status, "timestamp": fmt_ts(span_ts)})

    # Incident A traces
    for m in range(INCIDENT_A_START, INCIDENT_A_END + 1):
        ts_sec = START_DT + m * 60
        for _ in range(random.randint(2, 4)):
            r = rid()
            span_ts = ts_sec + random.randint(0, 59)
            inv_dur = random.randint(2500, 3500)
            pay_dur = inv_dur + random.randint(50, 200)
            cart_dur = pay_dur + random.randint(20, 50)
            gw_dur = cart_dur + random.randint(10, 30)
            for svc, offset, dur, status in [
                ("api-gateway", 0, gw_dur, "error"),
                ("cart-service", 10, cart_dur, "error"),
                ("payment-service", 30, pay_dur, "error"),
                ("inventory-service", 50, inv_dur, "timeout"),
            ]:
                docs.append({"request_id": r, "service": svc, "start_offset_ms": offset, "duration_ms": dur, "status": status, "timestamp": fmt_ts(span_ts)})

    # Incident B traces
    for m in range(INCIDENT_B_START, INCIDENT_B_END + 1):
        ts_sec = START_DT + m * 60
        for _ in range(random.randint(2, 4)):
            r = rid()
            span_ts = ts_sec + random.randint(0, 59)
            cart_dur = random.randint(150, 400)
            gw_dur = cart_dur + random.randint(20, 60)
            for svc, offset, dur, status in [
                ("api-gateway", 0, gw_dur, "error"),
                ("cart-service", 10, cart_dur, "error"),
            ]:
                docs.append({"request_id": r, "service": svc, "start_offset_ms": offset, "duration_ms": dur, "status": status, "timestamp": fmt_ts(span_ts)})

    docs.sort(key=lambda x: x["timestamp"])
    return docs


# ── Batch ingestion ────────────────────────────────────────────────────
def batch_ingest(stream, docs, batch_size=500):
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i+batch_size]
        resp = ingest_json(stream, batch)
        if resp is None:
            print(f"  FAILED at batch {i//batch_size + 1}")
            return False
    return True


STREAM_LOGS = "tl_logs"
STREAM_METRICS = "tl_metrics"
STREAM_TRACES = "tl_traces"


# ── Main ───────────────────────────────────────────────────────────────
def main():
    print("TraceTalk — OpenObserve data generator")
    print(f"Instance: {OO_BASE} | Org: {OO_ORG}\n")

    print(f"Streams: {STREAM_LOGS}, {STREAM_METRICS}, {STREAM_TRACES}\n")

    # Generate
    print("Generating data...")
    metrics_docs = generate_metrics_docs()
    log_docs = generate_log_docs()
    trace_docs = generate_trace_docs()
    print(f"  metrics: {len(metrics_docs)} docs")
    print(f"  logs:    {len(log_docs)} docs")
    print(f"  traces:  {len(trace_docs)} docs (flattened spans)")

    # Ingest
    print("\nIngesting into OpenObserve...")

    print(f"  {STREAM_LOGS} ({len(log_docs)} docs)...", end=" ", flush=True)
    if batch_ingest(STREAM_LOGS, log_docs):
        print("OK")

    print(f"  {STREAM_METRICS} ({len(metrics_docs)} docs)...", end=" ", flush=True)
    if batch_ingest(STREAM_METRICS, metrics_docs):
        print("OK")

    print(f"  {STREAM_TRACES} ({len(trace_docs)} docs)...", end=" ", flush=True)
    if batch_ingest(STREAM_TRACES, trace_docs):
        print("OK")

    # Verify
    print("\nVerifying ingestion (waiting 3s for indexing)...")
    time.sleep(3)
    for stream in [STREAM_LOGS, STREAM_METRICS, STREAM_TRACES]:
        cnt = count_stream(stream)
        print(f"  {stream}: {cnt} rows")


if __name__ == "__main__":
    main()
