# 0006. Monitoring that costs nothing: EC2 alarms, script alerts, a GitHub uptime check

- Status: Accepted
- Date: 2026-09-27

## Context

With one server ([0001](0001-single-ec2-with-docker-compose.md)) the questions that
matter are: is the site reachable, is the server healthy, is a disk filling up, did
the backups work, and is the code throwing errors. The project has no budget for
monitoring, so everything here must stay at **$0 a month**.

## Decision

Alerts are e-mailed through one SNS topic (`infra/main/monitoring.tf`,
`alert_email`); GitHub e-mails workflow failures on its own.

| Signal | Source | Alert |
|---|---|---|
| Site reachable | Scheduled GitHub Actions workflow (`.github/workflows/uptime.yml`) curls `https://motivetag.com/healthz` through Cloudflare every 30 min | GitHub's failed-run e-mail |
| Host health | EC2 status checks (free basic metrics) | system check → **auto-recover**; instance check → **reboot**; e-mail both |
| CPU | EC2 `CPUUtilization` | > 80 % for 15 min |
| Disk | `df` in the daily backup job | e-mail when `/` or `/srv/motivetag` is > 85 % full |
| Backups | `deploy/backup.sh`, `deploy/restore_drill.sh` ([0004](0004-mysql-backups-and-restore-drills.md)) | e-mail with the job's last log lines on any failure; the weekly drill also fails if the newest backup is > 26 h old |
| App errors | Sentry free tier, only when `SENTRY_DSN` is set; errors only, no tracing, no PII | Sentry's own alerts |

## Consequences

- Stays inside free tiers: three CloudWatch alarms (10 are free), no custom
  metrics, SNS e-mail (1,000 free a month), GitHub Actions minutes are free for a
  public repository.
- The uptime check is coarse: an outage can go unnoticed for up to ~30 minutes, and
  GitHub may start scheduled runs late. GitHub also pauses schedules in a public
  repository after 60 days without commits; re-enable it in the Actions tab.
- A missed backup (the timer never ran) is only caught by the weekly drill, not
  within a day.
- Memory is not watched; an out-of-memory hang shows up as a failed instance check.
- No log aggregation: logs are `docker compose logs` and `journalctl` on the server.

## Alternatives considered (all paid)

- **Route 53 health check** from several regions — a few dollars a month for an
  HTTPS endpoint outside AWS, and its metrics live only in `us-east-1`.
- **CloudWatch agent** for disk and memory — each metric is a paid custom metric.
- **CloudWatch Synthetics** — priced per run.
- **Prometheus + Grafana (Cloud)** — used in the 2022 version; more to run.

## Revisit when

There is budget or real users: switch uptime to a Route 53 health check, add the
CloudWatch agent for disk and memory, and ship container logs to CloudWatch Logs.
