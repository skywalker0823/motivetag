# 0006. Monitoring: outside-in uptime, CloudWatch alarms and Sentry

- Status: Accepted
- Date: 2026-09-26

## Context

With one server ([0001](0001-single-ec2-with-docker-compose.md)) the questions that
matter are: is the site reachable for users, is the server about to fall over
(disk, memory, CPU), did last night's backup happen, and is the code throwing
errors. Alerts should go to a person without running a monitoring stack of our own.

## Decision

All alarms e-mail through SNS (`infra/main/monitoring.tf`, `alert_email`).

| Signal | Source | Alarm |
|---|---|---|
| Site reachable | **Route 53 health check** on `https://motivetag.com/healthz` through Cloudflare, from several AWS regions every 30 s | 2 failed minutes |
| Host health | EC2 status checks | system check → **auto-recover**; instance check → **reboot** |
| CPU | EC2 `CPUUtilization` | > 80 % for 15 min |
| Disk | CloudWatch agent `disk_used_percent` for `/` and `/srv/motivetag` | > 85 %, or no data |
| Memory | CloudWatch agent `mem_used_percent` | > 90 % for 15 min |
| Backups | `BackupSuccess` / `RestoreDrillSuccess` from [0004](0004-mysql-backups-and-restore-drills.md) | no success in 24 h / any failure |
| App errors | **Sentry** (`sentry-sdk[flask]`), tagged with the git SHA as release | Sentry's own alert rules |

- The CloudWatch agent is installed and configured by **SSM State Manager
  associations**, from a config in Parameter Store, so no change to the server's
  bootstrap script and no manual install.
- The health check checks the path users take (DNS → Cloudflare → nginx → Flask),
  not just the instance.
- Sentry is enabled only when `SENTRY_DSN` is set; errors only, no tracing, no PII.

## Consequences

- A few dollars a month (health check, custom metrics, alarms); Sentry's free tier.
- Route 53 health check metrics exist only in `us-east-1`, so that alarm and its
  SNS topic live there: two SNS subscriptions to confirm.
- If Cloudflare Bot Fight Mode challenges the health checkers, the check fails
  while the site is fine; allow their user agent in a WAF skip rule.
- No log aggregation yet: logs are `docker compose logs` and `journalctl` on the
  server.

## Alternatives considered

- **Prometheus + Grafana (Cloud)** — used in the 2022 version; more to run than one
  server needs.
- **CloudWatch Synthetics** — a real browser check, but priced per run.
- **UptimeRobot / Better Stack** — free and good, but outside Terraform.

## Revisit when

We need latency or traffic dashboards, log search (ship container logs to
CloudWatch Logs), or paging instead of e-mail.
