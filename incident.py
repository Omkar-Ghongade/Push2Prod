
#!/usr/bin/env python3

"""
===============================================================
              OPENOBSERVE PRODUCTION INCIDENT LAB
===============================================================

Generates:

    Metrics : 1000/sec
    Logs    : 100/sec
    Traces  : 10/sec

Creates REAL OpenObserve alert rules using the existing:

    lab_webhook

Each metric has its own OpenObserve metrics stream.

Examples:

    http_latency_p99_ms
    cpu_usage_percent
    db_query_duration_ms
    redis_latency_ms
    kafka_consumer_lag
    error_rate_percent
    payment_failures_total
    inventory_timeouts_total

Alerts are configured with:

    creates_incident = True

Failure scenarios automatically rotate.

===============================================================
"""

import os
import sys
import time
import uuid
import random
import threading
from collections import defaultdict

import requests


# =============================================================
# CONFIGURATION
# =============================================================

OPENOBSERVE_URL = os.getenv(
    "OPENOBSERVE_URL",
    "http://localhost:5080"
).rstrip("/")

ORG = os.getenv(
    "OPENOBSERVE_ORG",
    "default"
)

USER = os.getenv(
    "OPENOBSERVE_USER"
)

PASSWORD = os.getenv(
    "OPENOBSERVE_PASSWORD"
)

DESTINATION = os.getenv(
    "OPENOBSERVE_DESTINATION",
    "lab_webhook"
)

METRICS_PER_SECOND = 100000
LOGS_PER_SECOND = 100000
TRACES_PER_SECOND = 100000


# =============================================================
# VALIDATE CONFIG
# =============================================================

if not USER or not PASSWORD:
    print()
    print("❌ Missing OpenObserve credentials.")
    print()
    print("Run:")
    print()
    print(
        "export OPENOBSERVE_USER='your-email'"
    )
    print(
        "export OPENOBSERVE_PASSWORD='your-password'"
    )
    print()
    sys.exit(1)


# =============================================================
# HTTP SESSION
# =============================================================

session = requests.Session()

session.auth = (
    USER,
    PASSWORD
)

session.headers.update({
    "Content-Type": "application/json"
})


# =============================================================
# ENDPOINTS
# =============================================================

METRICS_URL = (
    f"{OPENOBSERVE_URL}"
    f"/api/{ORG}"
    f"/ingest/metrics/_json"
)

LOGS_URL = (
    f"{OPENOBSERVE_URL}"
    f"/api/{ORG}"
    f"/application_logs/_json"
)

ALERTS_URL = (
    f"{OPENOBSERVE_URL}"
    f"/api/v2/{ORG}/alerts"
)

STREAMS_URL = (
    f"{OPENOBSERVE_URL}"
    f"/api/{ORG}/streams"
)


# =============================================================
# SERVICES
# =============================================================

SERVICES = [
    "api-gateway",
    "auth-service",
    "user-service",
    "order-service",
    "inventory-service",
    "payment-service",
    "notification-service",
    "recommendation-service",
    "search-service",
    "checkout-service",
]

REGIONS = [
    "ap-south-1",
    "us-east-1",
    "us-west-2",
    "eu-west-1",
]

INSTANCES = [
    "node-01",
    "node-02",
    "node-03",
    "node-04",
    "node-05",
    "node-06",
    "node-07",
    "node-08",
]

HTTP_METHODS = [
    "GET",
    "POST",
    "PUT",
    "DELETE",
]

HTTP_ROUTES = [
    "/api/users",
    "/api/orders",
    "/api/orders/{id}",
    "/api/payments",
    "/api/inventory",
    "/api/search",
    "/api/products",
    "/api/checkout",
]


# =============================================================
# GLOBAL STATE
# =============================================================

state_lock = threading.Lock()

state = {
    "scenario": "normal",

    "metrics": 0,
    "logs": 0,
    "traces": 0,

    "requests": 0,
    "orders": 0,
    "payments": 0,

    "failures": 0,

    "started_at": time.time(),
}


# =============================================================
# SCENARIOS
# =============================================================

SCENARIO_DURATION = {
    "normal": 45,

    "traffic_spike": 35,

    "payment_outage": 35,

    "database_outage": 35,

    "inventory_outage": 35,

    "redis_degradation": 35,

    "kafka_lag": 35,

    "cpu_exhaustion": 35,

    "multi_service_failure": 35,

    "recovery": 45,
}


SCENARIO_ORDER = [

    "normal",

    "traffic_spike",

    "payment_outage",

    "recovery",

    "database_outage",

    "recovery",

    "inventory_outage",

    "recovery",

    "redis_degradation",

    "recovery",

    "kafka_lag",

    "recovery",

    "cpu_exhaustion",

    "recovery",

    "multi_service_failure",

    "recovery",
]


def get_scenario():

    with state_lock:
        return state["scenario"]


def set_scenario(name):

    with state_lock:
        state["scenario"] = name

    print()
    print("=" * 72)
    print(f"🚨 SCENARIO: {name.upper()}")
    print("=" * 72)
    print()


def scenario_loop():

    index = 0

    while True:

        scenario = SCENARIO_ORDER[index]

        set_scenario(scenario)

        duration = SCENARIO_DURATION[
            scenario
        ]

        time.sleep(duration)

        index += 1

        if index >= len(SCENARIO_ORDER):
            index = 0


# =============================================================
# METRICS
# =============================================================

METRICS = [

    "http_requests_total",

    "http_latency_p50_ms",
    "http_latency_p95_ms",
    "http_latency_p99_ms",

    "http_2xx_total",
    "http_4xx_total",
    "http_5xx_total",

    "http_request_duration_ms",

    "cpu_usage_percent",
    "memory_usage_percent",
    "disk_usage_percent",

    "db_query_duration_ms",
    "db_connections_active",
    "db_connections_idle",
    "db_deadlocks_total",
    "db_slow_queries_total",

    "redis_latency_ms",
    "redis_hit_ratio",
    "redis_hits_total",
    "redis_misses_total",

    "kafka_consumer_lag",
    "kafka_messages_total",

    "orders_created_total",
    "orders_completed_total",

    "payments_total",
    "payment_failures_total",

    "inventory_reservations_total",
    "inventory_timeouts_total",

    "notifications_sent_total",
    "notifications_failed_total",

    "error_rate_percent",

    "request_rate",

    "network_rx_bytes",
    "network_tx_bytes",

    "queue_depth",

    "gc_pause_ms",
    "goroutines",
]


COUNTER_METRICS = {
    name
    for name in METRICS
    if name.endswith("_total")
}


# =============================================================
# METRIC GENERATOR
# =============================================================

def generate_metric():

    scenario = get_scenario()

    metric = random.choice(
        METRICS
    )

    service = random.choice(
        SERVICES
    )

    region = random.choice(
        REGIONS
    )

    instance = random.choice(
        INSTANCES
    )

    # ---------------------------------------------------------
    # NORMAL BASELINE
    # ---------------------------------------------------------

    values = {

        "http_requests_total":
            random.randint(
                1000,
                10000
            ),

        "http_latency_p50_ms":
            random.uniform(
                30,
                100
            ),

        "http_latency_p95_ms":
            random.uniform(
                100,
                300
            ),

        "http_latency_p99_ms":
            random.uniform(
                150,
                400
            ),

        "http_2xx_total":
            random.randint(
                500,
                9000
            ),

        "http_4xx_total":
            random.randint(
                0,
                100
            ),

        "http_5xx_total":
            random.randint(
                0,
                5
            ),

        "http_request_duration_ms":
            random.uniform(
                50,
                400
            ),

        "cpu_usage_percent":
            random.uniform(
                25,
                65
            ),

        "memory_usage_percent":
            random.uniform(
                35,
                75
            ),

        "disk_usage_percent":
            random.uniform(
                30,
                70
            ),

        "db_query_duration_ms":
            random.uniform(
                10,
                100
            ),

        "db_connections_active":
            random.randint(
                10,
                80
            ),

        "db_connections_idle":
            random.randint(
                10,
                100
            ),

        "db_deadlocks_total":
            random.randint(
                0,
                2
            ),

        "db_slow_queries_total":
            random.randint(
                0,
                5
            ),

        "redis_latency_ms":
            random.uniform(
                2,
                25
            ),

        "redis_hit_ratio":
            random.uniform(
                0.90,
                0.995
            ),

        "redis_hits_total":
            random.randint(
                100,
                1000
            ),

        "redis_misses_total":
            random.randint(
                1,
                50
            ),

        "kafka_consumer_lag":
            random.randint(
                10,
                500
            ),

        "kafka_messages_total":
            random.randint(
                100,
                5000
            ),

        "orders_created_total":
            random.randint(
                100,
                1000
            ),

        "orders_completed_total":
            random.randint(
                80,
                950
            ),

        "payments_total":
            random.randint(
                100,
                1000
            ),

        "payment_failures_total":
            random.randint(
                0,
                5
            ),

        "inventory_reservations_total":
            random.randint(
                100,
                1000
            ),

        "inventory_timeouts_total":
            random.randint(
                0,
                2
            ),

        "notifications_sent_total":
            random.randint(
                100,
                1000
            ),

        "notifications_failed_total":
            random.randint(
                0,
                5
            ),

        "error_rate_percent":
            random.uniform(
                0,
                1
            ),

        "request_rate":
            random.randint(
                500,
                5000
            ),

        "network_rx_bytes":
            random.randint(
                100000,
                10000000
            ),

        "network_tx_bytes":
            random.randint(
                100000,
                10000000
            ),

        "queue_depth":
            random.randint(
                10,
                500
            ),

        "gc_pause_ms":
            random.uniform(
                1,
                30
            ),

        "goroutines":
            random.randint(
                100,
                1000
            ),
    }

    # ---------------------------------------------------------
    # FAILURE MODIFIERS
    # ---------------------------------------------------------

    if scenario == "traffic_spike":

        values[
            "http_latency_p99_ms"
        ] = random.uniform(
            1500,
            5000
        )

        values[
            "http_latency_p95_ms"
        ] = random.uniform(
            800,
            2500
        )

        values[
            "cpu_usage_percent"
        ] = random.uniform(
            85,
            99
        )

        values[
            "request_rate"
        ] = random.randint(
            10000,
            30000
        )

        values[
            "error_rate_percent"
        ] = random.uniform(
            3,
            15
        )

    elif scenario == "payment_outage":

        if service in (
            "payment-service",
            "checkout-service",
            "order-service",
        ):

            values[
                "http_latency_p99_ms"
            ] = random.uniform(
                2000,
                7000
            )

            values[
                "payment_failures_total"
            ] = random.randint(
                30,
                100
            )

            values[
                "error_rate_percent"
            ] = random.uniform(
                20,
                80
            )

    elif scenario == "database_outage":

        values[
            "db_query_duration_ms"
        ] = random.uniform(
            2000,
            8000
        )

        values[
            "db_deadlocks_total"
        ] = random.randint(
            20,
            100
        )

        values[
            "db_slow_queries_total"
        ] = random.randint(
            50,
            200
        )

        values[
            "http_latency_p99_ms"
        ] = random.uniform(
            2000,
            6000
        )

        values[
            "error_rate_percent"
        ] = random.uniform(
            10,
            50
        )

    elif scenario == "inventory_outage":

        if service in (
            "inventory-service",
            "order-service",
            "checkout-service",
        ):

            values[
                "inventory_timeouts_total"
            ] = random.randint(
                20,
                100
            )

            values[
                "http_latency_p99_ms"
            ] = random.uniform(
                2000,
                7000
            )

            values[
                "error_rate_percent"
            ] = random.uniform(
                15,
                60
            )

    elif scenario == "redis_degradation":

        values[
            "redis_latency_ms"
        ] = random.uniform(
            700,
            2500
        )

        values[
            "redis_hit_ratio"
        ] = random.uniform(
            0.40,
            0.75
        )

        values[
            "http_latency_p99_ms"
        ] = random.uniform(
            1000,
            4000
        )

    elif scenario == "kafka_lag":

        values[
            "kafka_consumer_lag"
        ] = random.randint(
            15000,
            50000
        )

        values[
            "queue_depth"
        ] = random.randint(
            10000,
            50000
        )

        values[
            "http_latency_p99_ms"
        ] = random.uniform(
            1000,
            4000
        )

    elif scenario == "cpu_exhaustion":

        values[
            "cpu_usage_percent"
        ] = random.uniform(
            92,
            100
        )

        values[
            "goroutines"
        ] = random.randint(
            3000,
            10000
        )

        values[
            "gc_pause_ms"
        ] = random.uniform(
            100,
            1000
        )

        values[
            "http_latency_p99_ms"
        ] = random.uniform(
            1500,
            5000
        )

        values[
            "error_rate_percent"
        ] = random.uniform(
            5,
            25
        )

    elif scenario == "multi_service_failure":

        values[
            "http_latency_p99_ms"
        ] = random.uniform(
            3000,
            9000
        )

        values[
            "cpu_usage_percent"
        ] = random.uniform(
            90,
            100
        )

        values[
            "db_query_duration_ms"
        ] = random.uniform(
            2000,
            8000
        )

        values[
            "redis_latency_ms"
        ] = random.uniform(
            500,
            2000
        )

        values[
            "kafka_consumer_lag"
        ] = random.randint(
            10000,
            50000
        )

        values[
            "error_rate_percent"
        ] = random.uniform(
            20,
            80
        )

        values[
            "payment_failures_total"
        ] = random.randint(
            30,
            150
        )

        values[
            "inventory_timeouts_total"
        ] = random.randint(
            20,
            100
        )

    elif scenario == "recovery":

        values[
            "http_latency_p99_ms"
        ] = random.uniform(
            100,
            350
        )

        values[
            "cpu_usage_percent"
        ] = random.uniform(
            25,
            60
        )

        values[
            "db_query_duration_ms"
        ] = random.uniform(
            10,
            80
        )

        values[
            "redis_latency_ms"
        ] = random.uniform(
            2,
            25
        )

        values[
            "kafka_consumer_lag"
        ] = random.randint(
            10,
            500
        )

        values[
            "error_rate_percent"
        ] = random.uniform(
            0,
            1
        )

    # ---------------------------------------------------------
    # METRIC DOCUMENT
    # ---------------------------------------------------------

    return {

        "__name__":
            metric,

        "__type__":
            (
                "counter"
                if metric in COUNTER_METRICS
                else "gauge"
            ),

        "service":
            service,

        "environment":
            "production",

        "region":
            region,

        "instance":
            instance,

        "cluster":
            "ecommerce-prod",

        "scenario":
            scenario,

        "_timestamp":
            int(
                time.time() * 1000
            ),

        "value":
            float(
                values[metric]
            ),
    }


# =============================================================
# METRICS LOOP
# =============================================================

def metrics_loop():

    print(
        f"📊 Metrics: "
        f"{METRICS_PER_SECOND}/sec"
    )

    while True:

        started = time.monotonic()

        batch = [
            generate_metric()
            for _ in range(
                METRICS_PER_SECOND
            )
        ]

        try:

            response = session.post(
                METRICS_URL,
                json=batch,
                timeout=30
            )

            if response.status_code >= 300:

                print(
                    "❌ Metrics:",
                    response.status_code,
                    response.text[:500]
                )

            else:

                with state_lock:
                    state["metrics"] += len(
                        batch
                    )

        except Exception as exc:

            print(
                "❌ Metrics error:",
                exc
            )

        elapsed = (
            time.monotonic()
            - started
        )

        time.sleep(
            max(
                0,
                1 - elapsed
            )
        )


# =============================================================
# LOG GENERATOR
# =============================================================

INFO_MESSAGES = [
    "Request completed successfully",
    "Order created",
    "Payment authorized",
    "Inventory reserved",
    "User authenticated",
    "Kafka message published",
    "Database query completed",
    "Cache lookup completed",
    "Notification sent",
]

WARN_MESSAGES = [
    "Request latency elevated",
    "Database connection pool nearing capacity",
    "Redis latency elevated",
    "Kafka consumer lag increasing",
    "Retrying downstream request",
    "CPU utilization elevated",
    "Connection pool nearing exhaustion",
]

ERROR_MESSAGES = [
    "Database connection timeout",
    "Payment provider unavailable",
    "Inventory service timeout",
    "Redis connection timeout",
    "Kafka consumer lag exceeded threshold",
    "Downstream service returned HTTP 503",
    "Circuit breaker opened",
    "Connection pool exhausted",
    "Request timed out",
]


def generate_log():

    scenario = get_scenario()

    service = random.choice(
        SERVICES
    )

    # ---------------------------------------------------------
    # Error probability
    # ---------------------------------------------------------

    if scenario == "normal":
        error_probability = 0.01
        warning_probability = 0.06

    elif scenario == "recovery":
        error_probability = 0.03
        warning_probability = 0.10

    else:
        error_probability = 0.35
        warning_probability = 0.35

    random_value = random.random()

    if random_value < error_probability:

        level = "ERROR"

        message = random.choice(
            ERROR_MESSAGES
        )

        status = random.choice([
            500,
            502,
            503,
            504,
        ])

        with state_lock:
            state["failures"] += 1

    elif random_value < (
        error_probability +
        warning_probability
    ):

        level = "WARN"

        message = random.choice(
            WARN_MESSAGES
        )

        status = 200

    else:

        level = "INFO"

        message = random.choice(
            INFO_MESSAGES
        )

        status = 200

    request_id = (
        "req_"
        + uuid.uuid4().hex[:16]
    )

    trace_id = (
        uuid.uuid4().hex
    )

    return {

        "_timestamp":
            int(
                time.time() * 1000
            ),

        "level":
            level,

        "message":
            message,

        "service":
            service,

        "environment":
            "production",

        "region":
            random.choice(
                REGIONS
            ),

        "instance":
            random.choice(
                INSTANCES
            ),

        "request_id":
            request_id,

        "trace_id":
            trace_id,

        "span_id":
            uuid.uuid4().hex[:16],

        "http_method":
            random.choice(
                HTTP_METHODS
            ),

        "http_route":
            random.choice(
                HTTP_ROUTES
            ),

        "http_status":
            status,

        "scenario":
            scenario,
    }


# =============================================================
# LOG LOOP
# =============================================================

def logs_loop():

    print(
        f"📝 Logs: "
        f"{LOGS_PER_SECOND}/sec"
    )

    while True:

        started = time.monotonic()

        batch = [
            generate_log()
            for _ in range(
                LOGS_PER_SECOND
            )
        ]

        try:

            response = session.post(
                LOGS_URL,
                json=batch,
                timeout=30
            )

            if response.status_code >= 300:

                print(
                    "❌ Logs:",
                    response.status_code,
                    response.text[:500]
                )

            else:

                with state_lock:
                    state["logs"] += len(
                        batch
                    )

        except Exception as exc:

            print(
                "❌ Logs error:",
                exc
            )

        elapsed = (
            time.monotonic()
            - started
        )

        time.sleep(
            max(
                0,
                1 - elapsed
            )
        )


# =============================================================
# TRACE GENERATOR
#
# Uses OpenTelemetry if installed.
# Falls back gracefully if the package isn't available.
# =============================================================

try:

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import (
        TracerProvider
    )
    from opentelemetry.sdk.trace.export import (
        SimpleSpanProcessor
    )
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter
    )

    OTEL_AVAILABLE = True

except ImportError:

    OTEL_AVAILABLE = False


TRACERS = {}


def setup_tracers():

    if not OTEL_AVAILABLE:

        print(
            "⚠️ OpenTelemetry packages not "
            "installed. Traces will be skipped."
        )

        return

    trace_endpoint = (
        f"{OPENOBSERVE_URL}"
        f"/api/{ORG}"
        f"/v1/traces"
    )

    auth = (
        f"{USER}:{PASSWORD}"
    )

    import base64

    encoded = base64.b64encode(
        auth.encode()
    ).decode()

    for service in SERVICES:

        resource = Resource.create({

            "service.name":
                service,

            "service.version":
                "1.0.0",

            "deployment.environment":
                "production",

        })

        provider = TracerProvider(
            resource=resource
        )

        exporter = OTLPSpanExporter(

            endpoint=trace_endpoint,

            headers={
                "Authorization":
                    f"Basic {encoded}"
            },
        )

        provider.add_span_processor(
            SimpleSpanProcessor(
                exporter
            )
        )

        TRACERS[service] = (
            provider.get_tracer(
                service
            )
        )


def generate_trace():

    if not OTEL_AVAILABLE:
        return

    scenario = get_scenario()

    request_id = (
        "req_"
        + uuid.uuid4().hex[:16]
    )

    # ---------------------------------------------------------
    # API GATEWAY
    # ---------------------------------------------------------

    gateway = TRACERS[
        "api-gateway"
    ]

    with gateway.start_as_current_span(
        "POST /api/orders"
    ) as root:

        root.set_attribute(
            "http.method",
            "POST"
        )

        root.set_attribute(
            "http.route",
            "/api/orders"
        )

        root.set_attribute(
            "http.request_id",
            request_id
        )

        # -----------------------------------------------------
        # AUTH
        # -----------------------------------------------------

        with TRACERS[
            "auth-service"
        ].start_as_current_span(
            "authenticate"
        ):

            time.sleep(
                random.uniform(
                    0.002,
                    0.015
                )
            )

        # -----------------------------------------------------
        # INVENTORY
        # -----------------------------------------------------

        with TRACERS[
            "inventory-service"
        ].start_as_current_span(
            "inventory.reserve"
        ) as span:

            if scenario in (
                "inventory_outage",
                "multi_service_failure",
            ):

                span.set_attribute(
                    "error",
                    True
                )

                time.sleep(
                    random.uniform(
                        1.0,
                        3.0
                    )
                )

            else:

                time.sleep(
                    random.uniform(
                        0.005,
                        0.04
                    )
                )

        # -----------------------------------------------------
        # PAYMENT
        # -----------------------------------------------------

        with TRACERS[
            "payment-service"
        ].start_as_current_span(
            "payment.charge"
        ) as span:

            if scenario in (
                "payment_outage",
                "multi_service_failure",
            ):

                span.set_attribute(
                    "error",
                    True
                )

                time.sleep(
                    random.uniform(
                        1.0,
                        3.0
                    )
                )

            else:

                time.sleep(
                    random.uniform(
                        0.005,
                        0.05
                    )
                )

        # -----------------------------------------------------
        # DATABASE
        # -----------------------------------------------------

        with TRACERS[
            "order-service"
        ].start_as_current_span(
            "postgres.insert_order"
        ) as span:

            if scenario in (
                "database_outage",
                "multi_service_failure",
            ):

                span.set_attribute(
                    "error",
                    True
                )

                time.sleep(
                    random.uniform(
                        1.0,
                        3.0
                    )
                )

            else:

                time.sleep(
                    random.uniform(
                        0.005,
                        0.05
                    )
                )

        # -----------------------------------------------------
        # REDIS
        # -----------------------------------------------------

        with TRACERS[
            "user-service"
        ].start_as_current_span(
            "redis.get"
        ) as span:

            if scenario in (
                "redis_degradation",
                "multi_service_failure",
            ):

                span.set_attribute(
                    "error",
                    True
                )

                time.sleep(
                    random.uniform(
                        0.5,
                        1.5
                    )
                )

            else:

                time.sleep(
                    random.uniform(
                        0.002,
                        0.02
                    )
                )

        # -----------------------------------------------------
        # KAFKA
        # -----------------------------------------------------

        with TRACERS[
            "notification-service"
        ].start_as_current_span(
            "kafka.publish"
        ) as span:

            if scenario in (
                "kafka_lag",
                "multi_service_failure",
            ):

                span.set_attribute(
                    "messaging.kafka.consumer_lag",
                    random.randint(
                        10000,
                        50000
                    )
                )

                time.sleep(
                    random.uniform(
                        0.5,
                        1.5
                    )
                )

            else:

                time.sleep(
                    random.uniform(
                        0.002,
                        0.02
                    )
                )

        if scenario not in (
            "normal",
            "recovery",
        ):

            root.set_attribute(
                "incident.scenario",
                scenario
            )


# =============================================================
# TRACE LOOP
# =============================================================

def traces_loop():

    print(
        f"🔗 Traces: "
        f"{TRACES_PER_SECOND}/sec"
    )

    while True:

        started = time.monotonic()

        for _ in range(
            TRACES_PER_SECOND
        ):

            try:

                generate_trace()

                with state_lock:
                    state["traces"] += 1

            except Exception as exc:

                print(
                    "❌ Trace error:",
                    exc
                )

        elapsed = (
            time.monotonic()
            - started
        )

        time.sleep(
            max(
                0,
                1 - elapsed
            )
        )


# =============================================================
# REAL OPENOBSERVE ALERT DEFINITIONS
# =============================================================

ALERTS = [

    {
        "name":
            "lab_critical_p99_latency",

        "metric":
            "http_latency_p99_ms",

        "threshold":
            1000,

        "severity":
            "P1",

        "description":
            "Production HTTP P99 latency exceeded 1000ms.",
    },

    {
        "name":
            "lab_critical_cpu",

        "metric":
            "cpu_usage_percent",

        "threshold":
            90,

        "severity":
            "P1",

        "description":
            "Production CPU utilization exceeded 90%.",
    },

    {
        "name":
            "lab_database_latency",

        "metric":
            "db_query_duration_ms",

        "threshold":
            1000,

        "severity":
            "P1",

        "description":
            "Production database query latency exceeded 1000ms.",
    },

    {
        "name":
            "lab_redis_latency",

        "metric":
            "redis_latency_ms",

        "threshold":
            500,

        "severity":
            "P2",

        "description":
            "Production Redis latency exceeded 500ms.",
    },

    {
        "name":
            "lab_kafka_lag",

        "metric":
            "kafka_consumer_lag",

        "threshold":
            10000,

        "severity":
            "P1",

        "description":
            "Kafka consumer lag exceeded 10000 messages.",
    },

    {
        "name":
            "lab_error_rate",

        "metric":
            "error_rate_percent",

        "threshold":
            5,

        "severity":
            "P1",

        "description":
            "Production application error rate exceeded 5%.",
    },

    {
        "name":
            "lab_payment_failures",

        "metric":
            "payment_failures_total",

        "threshold":
            20,

        "severity":
            "P1",

        "description":
            "Payment failures exceeded 20.",
    },

    {
        "name":
            "lab_inventory_timeouts",

        "metric":
            "inventory_timeouts_total",

        "threshold":
            10,

        "severity":
            "P1",

        "description":
            "Inventory service timeouts exceeded 10.",
    },
]


# =============================================================
# STREAM CHECK
# =============================================================

def get_streams():

    try:

        response = session.get(
            STREAMS_URL,
            timeout=15
        )

        if response.status_code != 200:

            print(
                "⚠️ Could not list streams:",
                response.status_code,
                response.text[:500]
            )

            return set()

        data = response.json()

        return {
            item["name"]
            for item in data.get(
                "list",
                []
            )
            if item.get(
                "stream_type"
            ) == "metrics"
        }

    except Exception as exc:

        print(
            "⚠️ Stream discovery error:",
            exc
        )

        return set()


def wait_for_metric_streams():

    required = {
        alert["metric"]
        for alert in ALERTS
    }

    print()
    print(
        "🔎 Checking OpenObserve metric streams..."
    )

    for attempt in range(20):

        existing = get_streams()

        missing = (
            required
            - existing
        )

        if not missing:

            print(
                "✅ All required metric streams exist."
            )

            return True

        print(
            f"   Waiting for streams... "
            f"missing {len(missing)}"
        )

        time.sleep(2)

    print()
    print(
        "⚠️ Some metric streams were not found:"
    )

    for stream in sorted(
        missing
    ):
        print(
            f"   - {stream}"
        )

    return False


# =============================================================
# EXISTING ALERTS
# =============================================================

def get_existing_alerts():

    try:

        response = session.get(
            ALERTS_URL,
            timeout=15
        )

        if response.status_code != 200:

            print(
                "⚠️ Could not list alerts:",
                response.status_code,
                response.text[:500]
            )

            return {}

        data = response.json()

        alerts = (
            data.get("list", [])
            if isinstance(
                data,
                dict
            )
            else []
        )

        result = {}

        for alert in alerts:

            name = alert.get(
                "name"
            )

            if name:
                result[name] = alert

        return result

    except Exception as exc:

        print(
            "⚠️ Alert discovery error:",
            exc
        )

        return {}


# =============================================================
# CREATE REAL ALERT
# =============================================================

def create_alert(alert):

    stream = alert["metric"]

    # ---------------------------------------------------------
    # IMPORTANT
    #
    # OpenObserve creates one metric stream per metric name.
    #
    # Therefore:
    #
    #     stream_name = http_latency_p99_ms
    #
    # NOT:
    #
    #     stream_name = metrics
    # ---------------------------------------------------------

    sql = (
        f'SELECT avg(value) AS alert_value '
        f'FROM "{stream}"'
    )

    payload = {

        "name":
            alert["name"],

        "stream_type":
            "metrics",

        "stream_name":
            stream,

        "is_real_time":
            False,

        "query_condition": {

            "type":
                "sql",

            "sql":
                sql,
        },

        "trigger_condition": {

            "period":
                5,

            "operator":
                ">=",

            "threshold":
                alert["threshold"],

            "frequency":
                1,

            "frequency_type":
                "minutes",

            "silence":
                10,
        },

        "destinations": [
            DESTINATION
        ],

        "enabled":
            True,

        "creates_incident":
            True,

        "description":
            alert["description"],

        "context_attributes": {

            "severity":
                alert["severity"],

            "service":
                "ecommerce-platform",

            "environment":
                "production",

            "team":
                "platform",

            "managed_by":
                "openobserve-incident-lab",
        },
    }

    try:

        response = session.post(
            ALERTS_URL,
            json=payload,
            timeout=20
        )

        if response.status_code in (
            200,
            201
        ):

            print(
                f"  ✅ {alert['name']}"
                f" → {stream}"
                f" [{alert['severity']}]"
            )

            return True

        if response.status_code == 409:

            print(
                f"  ℹ️ {alert['name']}"
                f" already exists"
            )

            return True

        print(
            f"  ❌ {alert['name']}: "
            f"HTTP {response.status_code}"
        )

        print(
            response.text[:2000]
        )

        return False

    except Exception as exc:

        print(
            f"  ❌ {alert['name']}: "
            f"{exc}"
        )

        return False


# =============================================================
# ALERT SETUP
# =============================================================

def setup_alerts():

    print()
    print("=" * 72)
    print(
        "🔔 CONFIGURING REAL OPENOBSERVE ALERTS"
    )
    print("=" * 72)
    print()

    existing = get_existing_alerts()

    successful = 0

    for alert in ALERTS:

        # -----------------------------------------------------
        # Don't recreate existing alerts.
        # -----------------------------------------------------

        if alert["name"] in existing:

            print(
                f"  ℹ️ {alert['name']} "
                f"already exists"
            )

            successful += 1

            continue

        if create_alert(alert):

            successful += 1

    print()
    print(
        f"✅ {successful}/{len(ALERTS)} "
        f"alerts configured"
    )
    print()


# =============================================================
# STATUS DISPLAY
# =============================================================

def status_loop():

    while True:

        time.sleep(10)

        with state_lock:

            runtime = int(
                time.time()
                - state["started_at"]
            )

            print()
            print(
                "┌"
                + "─" * 70
                + "┐"
            )

            print(
                f"│ Scenario : "
                f"{state['scenario']:<58}│"
            )

            print(
                f"│ Metrics  : "
                f"{state['metrics']:<58}│"
            )

            print(
                f"│ Logs     : "
                f"{state['logs']:<58}│"
            )

            print(
                f"│ Traces   : "
                f"{state['traces']:<58}│"
            )

            print(
                f"│ Requests : "
                f"{state['requests']:<58}│"
            )

            print(
                f"│ Orders   : "
                f"{state['orders']:<58}│"
            )

            print(
                f"│ Payments : "
                f"{state['payments']:<58}│"
            )

            print(
                f"│ Failures : "
                f"{state['failures']:<58}│"
            )

            print(
                f"│ Runtime  : "
                f"{runtime}s"
                + " " * (
                    58
                    - len(
                        str(runtime)
                    )
                    - 1
                )
                + "│"
            )

            print(
                "└"
                + "─" * 70
                + "┘"
            )


# =============================================================
# BUSINESS COUNTER LOOP
# =============================================================

def business_state_loop():

    while True:

        scenario = get_scenario()

        with state_lock:

            if scenario == "normal":

                state["requests"] += random.randint(
                    2000,
                    5000
                )

                state["orders"] += random.randint(
                    100,
                    500
                )

                state["payments"] += random.randint(
                    100,
                    500
                )

            elif scenario == "traffic_spike":

                state["requests"] += random.randint(
                    8000,
                    20000
                )

                state["orders"] += random.randint(
                    500,
                    1500
                )

                state["payments"] += random.randint(
                    500,
                    1500
                )

            else:

                state["requests"] += random.randint(
                    1000,
                    4000
                )

                state["orders"] += random.randint(
                    50,
                    400
                )

                state["payments"] += random.randint(
                    50,
                    400
                )

        time.sleep(1)


# =============================================================
# MAIN
# =============================================================

def main():

    print()
    print("=" * 72)
    print(
        "              OPENOBSERVE INCIDENT LAB"
    )
    print("=" * 72)
    print()

    print(
        f"OpenObserve : {OPENOBSERVE_URL}"
    )

    print(
        f"Organization: {ORG}"
    )

    print(
        f"Metrics     : {METRICS_PER_SECOND}/sec"
    )

    print(
        f"Logs        : {LOGS_PER_SECOND}/sec"
    )

    print(
        f"Traces      : {TRACES_PER_SECOND}/sec"
    )

    print(
        f"Destination : {DESTINATION}"
    )

    print()

    # ---------------------------------------------------------
    # Start metric ingestion FIRST.
    #
    # OpenObserve creates metric streams from __name__.
    # ---------------------------------------------------------

    metric_thread = threading.Thread(
        target=metrics_loop,
        daemon=True
    )

    metric_thread.start()

    # ---------------------------------------------------------
    # Wait for the actual metric streams.
    # ---------------------------------------------------------

    wait_for_metric_streams()

    # ---------------------------------------------------------
    # Configure real alerts.
    # ---------------------------------------------------------

    setup_alerts()

    # ---------------------------------------------------------
    # Setup tracing.
    # ---------------------------------------------------------

    setup_tracers()

    # ---------------------------------------------------------
    # Start remaining workers.
    # ---------------------------------------------------------

    workers = [

        scenario_loop,

        logs_loop,

        traces_loop,

        status_loop,

        business_state_loop,

    ]

    for worker in workers:

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    print()
    print("=" * 72)
    print(
        "🚀 EVERYTHING IS RUNNING"
    )
    print("=" * 72)
    print()

    print(
        "The lab will automatically create:"
    )

    print(
        "  📊 Metrics"
    )

    print(
        "  📝 Logs"
    )

    print(
        "  🔗 Distributed traces"
    )

    print(
        "  🔔 Real OpenObserve alerts"
    )

    print(
        "  🚨 Native incidents "
        "(when enabled by your OpenObserve edition)"
    )

    print()

    print(
        "Failure scenarios are automatic."
    )

    print(
        "Press Ctrl+C to stop."
    )

    print()

    try:

        while True:

            time.sleep(1)

    except KeyboardInterrupt:

        print()
        print("=" * 72)
        print(
            "🛑 OPENOBSERVE INCIDENT LAB STOPPED"
        )
        print("=" * 72)
        print()


if __name__ == "__main__":

    main()

