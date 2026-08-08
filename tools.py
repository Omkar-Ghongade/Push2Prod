#!/usr/bin/env python3
"""Generic tool functions for querying OpenObserve.

No hardcoded streams or services — discovers and queries whatever data is in the instance.
"""

import base64
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

OO_BASE = os.environ.get("OO_BASE_URL", "http://localhost:5080")
OO_ORG = os.environ.get("OO_ORG", "default")
OO_USER = os.environ.get("ZO_ROOT_USER_EMAIL", "")
OO_PASS = os.environ.get("ZO_ROOT_USER_PASSWORD", "")
AUTH_HEADER = "Basic " + base64.b64encode(f"{OO_USER}:{OO_PASS}".encode()).decode() if OO_USER and OO_PASS else ""


def _iso_to_us(iso_str):
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1_000_000)


def _us_to_iso(us):
    return datetime.fromtimestamp(us / 1_000_000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_us():
    return int(time.time() * 1_000_000)


def _oo_search(sql, start_time_us=None, end_time_us=None, size=50):
    if not start_time_us:
        start_time_us = int((time.time() - 3600) * 1_000_000)  # default: last 1 hour
    if not end_time_us:
        end_time_us = _now_us()
    body = {
        "query": {
            "sql": sql,
            "start_time": start_time_us,
            "end_time": end_time_us,
            "from": 0,
            "size": size,
        }
    }
    url = f"{OO_BASE}/api/{OO_ORG}/_search"
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", AUTH_HEADER)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode())
            return result.get("hits", [])
    except Exception as e:
        return [{"error": str(e)}]


# ══════════════════════════════════════════════════════════════════════
# Tool 1: run_sql — arbitrary SQL query against OpenObserve
# ══════════════════════════════════════════════════════════════════════
def run_sql(sql, start_time=None, end_time=None, size=50):
    """Execute any SQL query against OpenObserve.

    Args:
        sql: SQL query (e.g. "SELECT * FROM application_logs WHERE level='ERROR' LIMIT 10")
        start_time: ISO8601 start (default: 1 hour ago)
        end_time: ISO8601 end (default: now)
        size: max rows (default 50, max 200)
    """
    s_us = _iso_to_us(start_time) if start_time else None
    e_us = _iso_to_us(end_time) if end_time else None
    size = min(size, 200)
    hits = _oo_search(sql, s_us, e_us, size=size)
    # If error, add hint about metric streams
    if hits and isinstance(hits[0], dict) and "error" in hits[0]:
        err = hits[0]["error"]
        if "400" in err or "Bad Request" in err:
            return {"results": [], "count": 0, "hint": "Query failed. Note: metric streams (db_query_duration_ms, http_latency_*, etc.) are not queryable via SQL. Use application_logs instead.", "error": err}
    return {"results": hits, "count": len(hits)}


# ══════════════════════════════════════════════════════════════════════
# Tool 2: list_streams — discover what data is available
# ══════════════════════════════════════════════════════════════════════
def list_streams():
    """List all streams in OpenObserve with their doc counts."""
    url = f"{OO_BASE}/api/{OO_ORG}/streams"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", AUTH_HEADER)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            streams = []
            for s in data.get("list", []):
                streams.append({
                    "name": s["name"],
                    "type": s.get("stream_type", "unknown"),
                    "doc_count": s.get("stats", {}).get("doc_num", 0),
                })
            streams.sort(key=lambda x: x["doc_count"], reverse=True)
            return {"streams": streams}
    except Exception as e:
        return {"error": str(e)}


# ══════════════════════════════════════════════════════════════════════
# Tool 3: search_logs — search logs by service, level, text
# ══════════════════════════════════════════════════════════════════════
def search_logs(service=None, level=None, text=None, start_time=None, end_time=None, size=50):
    where_parts = []
    if service:
        where_parts.append(f"service = '{service}'")
    if level:
        where_parts.append(f"level = '{level}'")
    if text:
        where_parts.append(f"str_match(message, '{text}')")
    where = " WHERE " + " AND ".join(where_parts) if where_parts else ""
    size = min(size, 100)

    sql = f"SELECT * FROM application_logs{where} ORDER BY _timestamp DESC"
    return run_sql(sql, start_time, end_time, size=size)


# ══════════════════════════════════════════════════════════════════════
# Tool 4: get_metrics — get time-series metric values
# ══════════════════════════════════════════════════════════════════════
def get_metrics(metric_stream, service=None, start_time=None, end_time=None, size=100):
    """Get metric values from a named metric stream.

    Args:
        metric_stream: stream name (e.g. "http_latency_p99_ms", "error_rate_percent")
        service: optional service filter
        start_time/end_time: ISO8601
    """
    where_parts = []
    if service:
        where_parts.append(f"service = '{service}'")
    where = " WHERE " + " AND ".join(where_parts) if where_parts else ""

    sql = f"SELECT _timestamp, service, value FROM \"{metric_stream}\"{where} ORDER BY _timestamp"
    return run_sql(sql, start_time, end_time, size=min(size, 200))


# ══════════════════════════════════════════════════════════════════════
# Tool 5: get_service_graph — static dependency graph (if applicable)
# ══════════════════════════════════════════════════════════════════════
def get_service_graph():
    """Return the service dependency graph. Returns discovered services if no static graph."""
    # Discover services from recent logs
    sql = "SELECT service, count(*) as cnt FROM application_logs GROUP BY service ORDER BY cnt DESC"
    hits = _oo_search(sql, size=20)
    services = [h.get("service", "unknown") for h in hits if h.get("service")]
    return {"services": services, "note": "Services discovered from logs. No static dependency graph available."}
