#!/usr/bin/env python3

import os
import time
import uuid
import random
import threading
import logging
from typing import Dict, List

import requests

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter


# ============================================================
# CONFIGURATION
# ============================================================

OPENOBSERVE_URL = os.getenv(
    "OPENOBSERVE_URL",
    "http://localhost:5080"
)

OPENOBSERVE_ORG = os.getenv(
    "OPENOBSERVE_ORG",
    "default"
)

OPENOBSERVE_USER = os.getenv(
    "OPENOBSERVE_USER"
)

OPENOBSERVE_PASSWORD = os.getenv(
    "OPENOBSERVE_PASSWORD"
)

METRICS_PER_SECOND = int(
    os.getenv("METRICS_PER_SECOND", "1000")
)

LOGS_PER_SECOND = int(
    os.getenv("LOGS_PER_SECOND", "150")
)

TRACES_PER_SECOND = int(
    os.getenv("TRACES_PER_SECOND", "20")
)

METRIC_STREAM = os.getenv(
    "METRIC_STREAM",
    "metrics"
)

LOG_STREAM = os.getenv(
    "LOG_STREAM",
    "application_logs"
)

TRACE_STREAM = os.getenv(
    "TRACE_STREAM",
    "default"
)


# ============================================================
# SERVICES
# ============================================================

SERVICES = [
    "api-gateway",
    "auth-service",
    "user-service",
    "order-service",
    "inventory-service",
    "payment-service",
    "notification-service",
    "recommendation-service",
]

REGIONS = [
    "us-east-1",
    "us-west-2",
    "eu-west-1",
    "ap-south-1",
]

HOSTS = [
    "node-01",
    "node-02",
    "node-03",
    "node-04",
    "node-05",
    "node-06",
]

ENDPOINTS = [
    "/api/orders",
    "/api/orders/{id}",
    "/api/payments",
    "/api/inventory",
    "/api/users",
    "/api/auth/login",
    "/api/products",
    "/api/recommendations",
]


# ============================================================
# HTTP CLIENT
# ============================================================

session = requests.Session()

session.auth = (
    OPENOBSERVE_USER,
    OPENOBSERVE_PASSWORD,
)

session.headers.update({
    "Content-Type": "application/json"
})


METRICS_URL = (
    f"{OPENOBSERVE_URL}/api/"
    f"{OPENOBSERVE_ORG}/ingest/metrics/_json"
)

LOGS_URL = (
    f"{OPENOBSERVE_URL}/api/"
    f"{OPENOBSERVE_ORG}/{LOG_STREAM}/_json"
)

TRACES_URL = (
    f"{OPENOBSERVE_URL}/api/"
    f"{OPENOBSERVE_ORG}/v1/traces"
)


# ============================================================
# GLOBAL STATE
# ============================================================

state_lock = threading.Lock()

state = {
    "scenario": "normal",
    "scenario_started": time.time(),

    "requests": 0,
    "errors": 0,

    "orders": 0,
    "payments": 0,
    "payment_failures": 0,

    "inventory_timeouts": 0,

    "redis_hits": 0,
    "redis_misses": 0,

    "queue_depth": 100,

    "db_connections": 25,

    "incident_count": 0,
}


# ============================================================
# SCENARIOS
# ============================================================

SCENARIOS = [
    "normal",
    "traffic_spike",
    "redis_degradation",
    "database_degradation",
    "inventory_outage",
    "payment_outage",
    "high_cpu",
    "kafka_lag",
    "recovery",
]


SCENARIO_DURATION = {
    "normal": (20, 50),
    "traffic_spike": (15, 30),
    "redis_degradation": (20, 40),
    "database_degradation": (20, 45),
    "inventory_outage": (20, 40),
    "payment_outage": (20, 40),
    "high_cpu": (15, 30),
    "kafka_lag": (20, 40),
    "recovery": (10, 20),
}


# ============================================================
# UTILITIES
# ============================================================

def now_ms():
    return int(time.time() * 1000)


def now_us():
    return int(time.time() * 1_000_000)


def random_service():
    return random.choice(SERVICES)


def random_region():
    return random.choice(REGIONS)


def random_host():
    return random.choice(HOSTS)


def random_endpoint():
    return random.choice(ENDPOINTS)


def generate_id():
    return uuid.uuid4().hex


def scenario():
    with state_lock:
        return state["scenario"]


def set_scenario(name):
    with state_lock:
        state["scenario"] = name
        state["scenario_started"] = time.time()
        state["incident_count"] += 1

    print(f"\n🚨 SCENARIO STARTED: {name}\n")


# ============================================================
# SCENARIO ENGINE
# ============================================================

def scenario_engine():

    current = "normal"
    set_scenario(current)

    while True:

        duration_min, duration_max = SCENARIO_DURATION[current]

        duration = random.uniform(
            duration_min,
            duration_max
        )

        time.sleep(duration)

        if current == "normal":
            next_scenarios = [
                "traffic_spike",
                "redis_degradation",
                "database_degradation",
                "inventory_outage",
                "payment_outage",
                "high_cpu",
                "kafka_lag",
            ]

            current = random.choice(next_scenarios)

        elif current in [
            "traffic_spike",
            "redis_degradation",
            "database_degradation",
            "inventory_outage",
            "payment_outage",
            "high_cpu",
            "kafka_lag",
        ]:
            current = "recovery"

        else:
            current = "normal"

        set_scenario(current)


# ============================================================
# METRIC GENERATION
# ============================================================

def metric(
    name,
    metric_type,
    value,
    service=None,
    endpoint=None,
    region=None,
    host=None,
    extra=None,
):
    record = {
        "__name__": name,
        "__type__": metric_type,
        "_timestamp": now_ms(),
        "value": float(value),
    }

    if service:
        record["service"] = service

    if endpoint:
        record["endpoint"] = endpoint

    if region:
        record["region"] = region

    if host:
        record["host"] = host

    if extra:
        record.update(extra)

    return record


def generate_metric():

    s = scenario()

    service = random_service()
    endpoint = random_endpoint()
    region = random_region()
    host = random_host()

    # --------------------------------------------------------
    # Base values
    # --------------------------------------------------------

    latency = random.uniform(10, 180)
    cpu = random.uniform(20, 65)
    memory = random.uniform(30, 75)

    error_rate = random.uniform(0, 2)

    db_latency = random.uniform(2, 50)
    redis_latency = random.uniform(1, 10)

    queue = random.randint(20, 200)

    # --------------------------------------------------------
    # Scenario modifications
    # --------------------------------------------------------

    if s == "traffic_spike":

        latency *= random.uniform(2, 5)
        cpu = random.uniform(75, 98)
        queue = random.randint(500, 3000)
        error_rate = random.uniform(3, 10)

    elif s == "redis_degradation":

        redis_latency = random.uniform(100, 800)

        latency *= random.uniform(2, 4)

        error_rate = random.uniform(2, 8)

    elif s == "database_degradation":

        db_latency = random.uniform(500, 5000)

        latency *= random.uniform(3, 8)

        cpu = random.uniform(70, 95)

        error_rate = random.uniform(4, 15)

    elif s == "inventory_outage":

        if service == "inventory-service":

            latency = random.uniform(2000, 10000)
            error_rate = random.uniform(30, 80)

        elif service == "order-service":

            latency = random.uniform(1000, 5000)
            error_rate = random.uniform(10, 30)

    elif s == "payment_outage":

        if service == "payment-service":

            latency = random.uniform(1000, 8000)
            error_rate = random.uniform(25, 70)

        elif service == "order-service":

            error_rate = random.uniform(10, 30)

    elif s == "high_cpu":

        cpu = random.uniform(90, 100)

        latency *= random.uniform(2, 5)

        error_rate = random.uniform(3, 15)

    elif s == "kafka_lag":

        queue = random.randint(5000, 50000)

        latency *= random.uniform(2, 4)

    elif s == "recovery":

        latency *= random.uniform(1, 2)

        cpu = random.uniform(30, 70)

        error_rate = random.uniform(0, 2)

    # --------------------------------------------------------
    # Choose metric
    # --------------------------------------------------------

    metric_name = random.choice([
        "http_requests_total",
        "http_request_duration_ms",
        "http_latency_p50_ms",
        "http_latency_p95_ms",
        "http_latency_p99_ms",

        "http_5xx_total",
        "http_4xx_total",

        "active_requests",
        "request_rate",

        "cpu_usage_percent",
        "memory_usage_percent",
        "disk_usage_percent",

        "network_rx_bytes",
        "network_tx_bytes",

        "gc_pause_ms",
        "goroutines",

        "db_connections_active",
        "db_connections_idle",
        "db_query_duration_ms",
        "db_slow_queries_total",
        "db_deadlocks_total",

        "redis_latency_ms",
        "redis_hit_ratio",
        "redis_hits_total",
        "redis_misses_total",

        "queue_depth",
        "kafka_consumer_lag",
        "kafka_messages_total",

        "orders_created_total",
        "orders_completed_total",

        "payments_total",
        "payment_failures_total",
        "refunds_total",

        "inventory_reservations_total",
        "inventory_timeouts_total",

        "notifications_sent_total",
        "notifications_failed_total",

        "error_rate_percent",
    ])

    # --------------------------------------------------------
    # Values
    # --------------------------------------------------------

    values = {
        "http_requests_total":
            random.randint(100, 10000),

        "http_request_duration_ms":
            latency,

        "http_latency_p50_ms":
            latency * 0.35,

        "http_latency_p95_ms":
            latency * 1.7,

        "http_latency_p99_ms":
            latency * 2.8,

        "http_5xx_total":
            int(error_rate * random.uniform(1, 20)),

        "http_4xx_total":
            random.randint(0, 30),

        "active_requests":
            random.randint(5, 500),

        "request_rate":
            random.randint(50, 3000),

        "cpu_usage_percent":
            cpu,

        "memory_usage_percent":
            memory,

        "disk_usage_percent":
            random.uniform(20, 85),

        "network_rx_bytes":
            random.randint(10000, 5000000),

        "network_tx_bytes":
            random.randint(10000, 5000000),

        "gc_pause_ms":
            random.uniform(0.1, 50),

        "goroutines":
            random.randint(50, 5000),

        "db_connections_active":
            random.randint(10, 90),

        "db_connections_idle":
            random.randint(5, 50),

        "db_query_duration_ms":
            db_latency,

        "db_slow_queries_total":
            random.randint(0, 20),

        "db_deadlocks_total":
            random.randint(0, 3),

        "redis_latency_ms":
            redis_latency,

        "redis_hit_ratio":
            random.uniform(0.65, 0.99),

        "redis_hits_total":
            random.randint(100, 5000),

        "redis_misses_total":
            random.randint(10, 1000),

        "queue_depth":
            queue,

        "kafka_consumer_lag":
            queue * random.randint(1, 10),

        "kafka_messages_total":
            random.randint(1000, 50000),

        "orders_created_total":
            random.randint(50, 1000),

        "orders_completed_total":
            random.randint(50, 950),

        "payments_total":
            random.randint(50, 1000),

        "payment_failures_total":
            int(error_rate * random.uniform(1, 10)),

        "refunds_total":
            random.randint(0, 50),

        "inventory_reservations_total":
            random.randint(50, 1000),

        "inventory_timeouts_total":
            random.randint(0, 10),

        "notifications_sent_total":
            random.randint(50, 1000),

        "notifications_failed_total":
            random.randint(0, 20),

        "error_rate_percent":
            error_rate,
    }

    return metric(
        metric_name,
        "counter"
        if metric_name.endswith("_total")
        else "gauge",
        values[metric_name],
        service=service,
        endpoint=endpoint,
        region=region,
        host=host,
        extra={
            "environment": "local",
            "cluster": "production-simulator",
        },
    )


# ============================================================
# METRICS LOOP
# ============================================================

def metrics_loop():

    print(
        f"📊 Metrics generator: "
        f"{METRICS_PER_SECOND}/second"
    )

    while True:

        start = time.monotonic()

        records = [
            generate_metric()
            for _ in range(METRICS_PER_SECOND)
        ]

        try:

            response = session.post(
                METRICS_URL,
                json=records,
                timeout=15,
            )

            if response.status_code >= 300:

                print(
                    "❌ Metrics error:",
                    response.status_code,
                    response.text[:300],
                )

            else:

                print(
                    f"📊 {len(records)} metrics "
                    f"→ OpenObserve"
                )

        except Exception as e:

            print(
                f"❌ Metrics exception: {e}"
            )

        elapsed = time.monotonic() - start

        time.sleep(
            max(0, 1.0 - elapsed)
        )


# ============================================================
# LOG GENERATION
# ============================================================

LOG_MESSAGES = {

    "INFO": [
        "Request completed successfully",
        "Payment authorized",
        "Order created",
        "Inventory reserved",
        "User authenticated",
        "Cache lookup completed",
        "Notification sent",
        "Kafka message published",
        "Database query completed",
    ],

    "WARN": [
        "High request latency detected",
        "Redis latency elevated",
        "Database connection pool nearing capacity",
        "Kafka consumer lag increasing",
        "Retrying downstream request",
        "Circuit breaker approaching threshold",
        "Slow database query detected",
    ],

    "ERROR": [
        "Database timeout",
        "Inventory service timeout",
        "Payment provider returned 503",
        "Redis connection failed",
        "Kafka publish failed",
        "Request failed with HTTP 500",
        "Downstream service unavailable",
        "Connection pool exhausted",
    ],

    "FATAL": [
        "Circuit breaker opened",
        "Payment provider unavailable",
        "Database unavailable",
        "Critical dependency failure",
    ],
}


def generate_log():

    s = scenario()

    service = random_service()

    trace_id = generate_id()
    span_id = generate_id()[:16]
    request_id = "req_" + generate_id()[:12]

    level = "INFO"

    probability = random.random()

    if s == "normal":

        if probability < 0.90:
            level = "INFO"
        elif probability < 0.98:
            level = "WARN"
        else:
            level = "ERROR"

    else:

        if probability < 0.55:
            level = "INFO"
        elif probability < 0.75:
            level = "WARN"
        elif probability < 0.97:
            level = "ERROR"
        else:
            level = "FATAL"

    if s == "inventory_outage":
        service = random.choice([
            "inventory-service",
            "order-service",
        ])

        level = random.choice([
            "ERROR",
            "ERROR",
            "WARN",
        ])

    elif s == "payment_outage":
        service = random.choice([
            "payment-service",
            "order-service",
        ])

        level = random.choice([
            "ERROR",
            "ERROR",
            "FATAL",
        ])

    elif s == "database_degradation":

        level = random.choice([
            "WARN",
            "WARN",
            "ERROR",
        ])

    elif s == "redis_degradation":

        level = random.choice([
            "WARN",
            "ERROR",
        ])

    message = random.choice(
        LOG_MESSAGES[level]
    )

    return {
        "_timestamp": now_us(),

        "timestamp": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime()
        ),

        "level": level,

        "message": message,

        "service": service,

        "environment": "production",

        "region": random_region(),

        "host": random_host(),

        "trace_id": trace_id,

        "span_id": span_id,

        "request_id": request_id,

        "endpoint": random_endpoint(),

        "scenario": s,

        "http_status_code": (
            random.choice([500, 502, 503, 504])
            if level in ["ERROR", "FATAL"]
            else 200
        ),

        "duration_ms": random.uniform(
            5,
            5000 if level in ["ERROR", "FATAL"]
            else 300
        ),
    }


# ============================================================
# ALERT GENERATION
# ============================================================

def generate_alert_log():

    s = scenario()

    alerts = {

        "traffic_spike": (
            "High traffic detected: "
            "request rate exceeded threshold"
        ),

        "redis_degradation": (
            "Redis latency exceeded 500ms"
        ),

        "database_degradation": (
            "Database query latency exceeded 2 seconds"
        ),

        "inventory_outage": (
            "Inventory service availability "
            "below SLO threshold"
        ),

        "payment_outage": (
            "Payment failure rate exceeded 20%"
        ),

        "high_cpu": (
            "CPU utilization exceeded 90%"
        ),

        "kafka_lag": (
            "Kafka consumer lag exceeded threshold"
        ),

        "recovery": (
            "Incident recovery detected"
        ),
    }

    if s not in alerts:
        return None

    return {
        "_timestamp": now_us(),

        "timestamp": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ",
            time.gmtime()
        ),

        "level": "ERROR"
        if s != "recovery"
        else "INFO",

        "message": alerts[s],

        "event_type": "alert",

        "alert_name": (
            s.upper() + "_ALERT"
        ),

        "severity": (
            "critical"
            if s in [
                "inventory_outage",
                "payment_outage",
                "database_degradation",
            ]
            else "warning"
        ),

        "status": (
            "resolved"
            if s == "recovery"
            else "firing"
        ),

        "service": random_service(),

        "environment": "production",

        "region": random_region(),

        "scenario": s,

        "alert_source": "observability-simulator",
    }


# ============================================================
# LOG LOOP
# ============================================================

def logs_loop():

    print(
        f"📝 Log generator: "
        f"{LOGS_PER_SECOND}/second"
    )

    interval = 1.0 / LOGS_PER_SECOND

    while True:

        start = time.monotonic()

        records = []

        for _ in range(LOGS_PER_SECOND):

            records.append(
                generate_log()
            )

        alert = generate_alert_log()

        if alert:
            records.append(alert)

        try:

            response = session.post(
                LOGS_URL,
                json=records,
                timeout=15,
            )

            if response.status_code >= 300:

                print(
                    "❌ Logs error:",
                    response.status_code,
                    response.text[:300],
                )

        except Exception as e:

            print(
                f"❌ Logs exception: {e}"
            )

        elapsed = time.monotonic() - start

        time.sleep(
            max(0, 1.0 - elapsed)
        )


# ============================================================
# OPENTELEMETRY TRACING
# ============================================================

def create_tracer(service_name):

    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": "production",
        "service.namespace": "ecommerce",
    })

    provider = TracerProvider(
        resource=resource
    )

    exporter = OTLPSpanExporter(
        endpoint=TRACES_URL,
        headers={
            "Authorization":
                _authorization_header(),
            "stream-name":
                TRACE_STREAM,
        },
    )

    processor = SimpleSpanProcessor(
        exporter
    )

    provider.add_span_processor(
        processor
    )

    return provider.get_tracer(
        service_name
    )


def _authorization_header():

    import base64

    credentials = (
        f"{OPENOBSERVE_USER}:"
        f"{OPENOBSERVE_PASSWORD}"
    )

    encoded = base64.b64encode(
        credentials.encode()
    ).decode()

    return f"Basic {encoded}"


TRACERS = {
    service: create_tracer(service)
    for service in SERVICES
}


# ============================================================
# DISTRIBUTED TRACE
# ============================================================

def create_trace():

    s = scenario()

    trace_id = generate_id()

    endpoint = random_endpoint()

    # --------------------------------------------------------
    # API Gateway
    # --------------------------------------------------------

    gateway = TRACERS["api-gateway"]

    with gateway.start_as_current_span(
        f"HTTP {endpoint}"
    ) as root:

        root.set_attribute(
            "http.method",
            random.choice([
                "GET",
                "POST",
                "PUT",
            ])
        )

        root.set_attribute(
            "http.route",
            endpoint
        )

        root.set_attribute(
            "deployment.environment",
            "production"
        )

        # ----------------------------------------------------
        # Authentication
        # ----------------------------------------------------

        with TRACERS["auth-service"].start_as_current_span(
            "authenticate-user"
        ) as span:

            span.set_attribute(
                "service.name",
                "auth-service"
            )

            time.sleep(
                random.uniform(
                    0.001,
                    0.015
                )
            )

        # ----------------------------------------------------
        # Inventory
        # ----------------------------------------------------

        with TRACERS["inventory-service"].start_as_current_span(
            "inventory.reserve"
        ) as span:

            latency = random.uniform(
                0.005,
                0.08
            )

            if s == "inventory_outage":

                latency = random.uniform(
                    2,
                    6
                )

                span.set_status(
                    trace.Status(
                        trace.StatusCode.ERROR,
                        "inventory timeout"
                    )
                )

                span.set_attribute(
                    "error.type",
                    "TimeoutError"
                )

            time.sleep(latency)

        # ----------------------------------------------------
        # Payment
        # ----------------------------------------------------

        with TRACERS["payment-service"].start_as_current_span(
            "payment.charge"
        ) as span:

            latency = random.uniform(
                0.02,
                0.15
            )

            if s == "payment_outage":

                latency = random.uniform(
                    1,
                    5
                )

                span.set_status(
                    trace.Status(
                        trace.StatusCode.ERROR,
                        "payment provider timeout"
                    )
                )

                span.set_attribute(
                    "error.type",
                    "PaymentProviderError"
                )

            time.sleep(latency)

        # ----------------------------------------------------
        # Database
        # ----------------------------------------------------

        with TRACERS["order-service"].start_as_current_span(
            "postgres.insert_order"
        ) as span:

            latency = random.uniform(
                0.003,
                0.08
            )

            if s == "database_degradation":

                latency = random.uniform(
                    0.5,
                    4
                )

                span.set_status(
                    trace.Status(
                        trace.StatusCode.ERROR,
                        "database timeout"
                    )
                )

            time.sleep(latency)

        # ----------------------------------------------------
        # Notification
        # ----------------------------------------------------

        with TRACERS["notification-service"].start_as_current_span(
            "kafka.publish"
        ):

            time.sleep(
                random.uniform(
                    0.002,
                    0.03
                )
            )

        # ----------------------------------------------------
        # Root span status
        # ----------------------------------------------------

        if s in [
            "inventory_outage",
            "payment_outage",
            "database_degradation",
        ]:

            root.set_status(
                trace.Status(
                    trace.StatusCode.ERROR,
                    s
                )
            )


# ============================================================
# TRACE LOOP
# ============================================================

def traces_loop():

    print(
        f"🔗 Trace generator: "
        f"{TRACES_PER_SECOND}/second"
    )

    interval = (
        1.0 / TRACES_PER_SECOND
    )

    while True:

        start = time.monotonic()

        try:

            create_trace()

        except Exception as e:

            print(
                f"❌ Trace exception: {e}"
            )

        elapsed = (
            time.monotonic() - start
        )

        time.sleep(
            max(
                0,
                interval - elapsed
            )
        )


# ============================================================
# BUSINESS EVENTS
# ============================================================

def business_loop():

    while True:

        s = scenario()

        with state_lock:

            state["requests"] += random.randint(
                100,
                500
            )

            state["orders"] += random.randint(
                10,
                100
            )

            state["payments"] += random.randint(
                10,
                100
            )

            if s == "payment_outage":

                state["payment_failures"] += random.randint(
                    20,
                    80
                )

            if s == "inventory_outage":

                state["inventory_timeouts"] += random.randint(
                    10,
                    50
                )

        time.sleep(1)


# ============================================================
# STATUS REPORTER
# ============================================================

def status_loop():

    while True:

        time.sleep(10)

        with state_lock:

            print(
                "\n"
                "================================================\n"
                " OBSERVABILITY SIMULATOR\n"
                "================================================\n"
                f" Scenario:          {state['scenario']}\n"
                f" Requests:          {state['requests']}\n"
                f" Orders:            {state['orders']}\n"
                f" Payments:          {state['payments']}\n"
                f" Payment failures:  {state['payment_failures']}\n"
                f" Inventory timeout: {state['inventory_timeouts']}\n"
                f" Incidents:         {state['incident_count']}\n"
                "================================================\n"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    if not OPENOBSERVE_USER:
        raise RuntimeError(
            "OPENOBSERVE_USER is not set"
        )

    if not OPENOBSERVE_PASSWORD:
        raise RuntimeError(
            "OPENOBSERVE_PASSWORD is not set"
        )

    print()
    print("=" * 60)
    print("        OPENOBSERVE OBSERVABILITY SIMULATOR")
    print("=" * 60)
    print()
    print(
        f"OpenObserve: {OPENOBSERVE_URL}"
    )
    print(
        f"Organization: {OPENOBSERVE_ORG}"
    )
    print(
        f"Metrics:     {METRICS_PER_SECOND}/sec"
    )
    print(
        f"Logs:        {LOGS_PER_SECOND}/sec"
    )
    print(
        f"Traces:      {TRACES_PER_SECOND}/sec"
    )
    print()
    print(
        "Press Ctrl+C to stop."
    )
    print()

    threads = [

        threading.Thread(
            target=scenario_engine,
            daemon=True,
        ),

        threading.Thread(
            target=metrics_loop,
            daemon=True,
        ),

        threading.Thread(
            target=logs_loop,
            daemon=True,
        ),

        threading.Thread(
            target=traces_loop,
            daemon=True,
        ),

        threading.Thread(
            target=business_loop,
            daemon=True,
        ),

        threading.Thread(
            target=status_loop,
            daemon=True,
        ),
    ]

    for thread in threads:
        thread.start()

    try:

        while True:
            time.sleep(1)

    except KeyboardInterrupt:

        print(
            "\n\n🛑 Simulator stopped."
        )


if __name__ == "__main__":
    main()