"""Prometheus metrics for the Grafana dashboard (infra/README.md, "Monitoring").

Grafana Alloy scrapes /metrics over the Docker network; nginx refuses the path from
outside, and the view itself refuses anything that came through nginx. One gunicorn
worker (ADR 0008) means the default in-process registry sees every request.
"""

import time

from flask import abort, g, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    disable_created_metrics,
    generate_latest,
)

# The *_created series double the count (and the free tier is counted in series)
# without telling the dashboard anything.
disable_created_metrics()

REQUESTS = Counter(
    "motivetag_http_requests_total",
    "HTTP requests by route pattern (never the raw URL), method and status code.",
    ["endpoint", "method", "status"],
)
LATENCY = Histogram(
    "motivetag_http_request_duration_seconds",
    "Time spent answering HTTP requests, by route pattern.",
    ["endpoint"],
    buckets=(0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)
AUTH = Counter(
    "motivetag_auth_events_total",
    "Sign-ins and sign-ups: login_ok, login_failed, login_suspended, signup_ok, signup_refused,"
    " signup_invited.",
    ["event"],
)
REPORTS = Counter(
    "motivetag_reports_total",
    "Reports members filed, by what they reported: post, comment, message, member.",
    ["type"],
)
ONLINE = Gauge("motivetag_online_members", "Members with an open chat connection.")

# Long-lived Socket.IO connections would swamp the latency figures; ONLINE covers them.
SKIP = ("/socket.io", "/metrics")


def auth_event(event):
    AUTH.labels(event).inc()


def init_metrics(app):
    @app.before_request
    def start_timer():
        g.metrics_start = time.perf_counter()

    @app.after_request
    def record(response):
        start = g.pop("metrics_start", None)
        if start is None or request.path.startswith(SKIP):
            return response
        # The route pattern (/tag/<tag_name>) keeps the number of series small.
        endpoint = request.url_rule.rule if request.url_rule else "unmatched"
        REQUESTS.labels(endpoint, request.method, str(response.status_code)).inc()
        LATENCY.labels(endpoint).observe(time.perf_counter() - start)
        return response

    @app.route("/metrics")
    def metrics():
        # nginx always adds this header, so its presence means the request came from outside.
        if "X-Forwarded-For" in request.headers:
            abort(404)
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}
