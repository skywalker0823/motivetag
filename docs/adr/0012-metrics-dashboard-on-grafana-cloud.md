# 0012. A metrics dashboard on Grafana Cloud's free tier, fed by Grafana Alloy

- Status: Accepted
- Date: 2026-09-28

## Context

[0006](0006-monitoring-and-alerting.md) alerts on a dead server, high CPU, full
disks and failed backups, but there was no way to *see* how the site is doing:
memory (not watched at all), request volume, error rate, latency, or sign-in
failures that may mean someone is guessing passwords. The owner wanted a dashboard
without new costs. The server is a t3.small (2 GB) already running MySQL, the app
and nginx.

## Decision

- The app exposes Prometheus metrics at `/metrics` (`api/metrics.py`): requests by
  **route pattern** (never the raw URL, to bound the number of series), method and
  status; a latency histogram per route; sign-in/sign-up events; members online;
  plus the client library's process metrics. nginx returns 404 for `/metrics`, and
  the app refuses it when `X-Forwarded-For` is present.
- **Grafana Alloy** (`deploy/alloy.alloy`, container in `deploy/compose.yaml`) reads
  the host's CPU, memory, disk, network and load through read-only `/proc`, `/sys`
  and `/` mounts, scrapes the app, and remote-writes to **Grafana Cloud** once a
  minute. No Docker socket, no privileged mode, 256 MB memory limit.
- It runs only when `/motivetag/grafana-prom-url`, `-prom-user` and
  `-cloud-token` exist (compose profile `monitoring`, set by deploy.sh).
- The dashboard is code: `deploy/grafana/motivetag-overview.json`, imported once.

## Consequences

- $0: about 400–1,500 active series at one sample a minute, against the free tier's
  10,000 (14-day retention). Alloy itself used about 40 MB in testing.
- Memory, request rate, 5xx rate, p95 latency and failed sign-ins are visible, and
  Grafana Cloud alerting can be added on any panel.
- nginx's own rate-limit refusals (429 before the app) are not counted; neither
  are Socket.IO connections beyond the online-members gauge.
- No logs are shipped yet: that would need either the Docker socket or log files
  on disk; kept for a later, security-focused step.

## Alternatives considered

- **Self-hosted Prometheus + Grafana (+ Loki) on the server** — about 1 GB of RAM;
  would need a t3.medium (≈ US$15–20 a month more).
- **CloudWatch agent + dashboards** — custom metrics cost money beyond the free 10.
- **cAdvisor for per-container figures** — needs a privileged container; host and
  app process metrics are enough for now.

## Revisit when

The free tier's series or retention limits get close, logs are needed for
investigating abuse, or a second server appears.
