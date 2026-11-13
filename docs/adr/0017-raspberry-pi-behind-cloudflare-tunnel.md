# 0017. Run the site on a Raspberry Pi behind a Cloudflare Tunnel

- Status: Accepted (supersedes the hosting parts of 0001, 0002 and 0006)
- Date: 2026-11-13

## Context

The site was paused on 2026-11-02 to stop paying for EC2 (`t3.small`, its disks and
the Elastic IP), and its data was discarded. The owner has a Raspberry Pi 4 (4 GB,
arm64, Ubuntu 26.04) at home that is on all the time. Its home router forwards no
ports, and its firewall (ufw) admits only SSH from the home network. The AWS pieces
that cost nothing at this size (S3, SES, Parameter Store, SNS, ECR, IAM/OIDC) are
worth keeping, as is the delivery pipeline (ADR 0003) and the backups (ADR 0004).
The last EC2 configuration is kept as the git tag `aws-ec2-final`.

## Decision

- **Host**: the Pi runs the same `docker compose` stack (MySQL 8.4, the app,
  nginx, optional Alloy) from `deploy/compose.yaml`. MySQL is sized for 4 GB
  (256 MB buffer pool, performance_schema off). Data stays on the Pi's own disk
  under `/srv/motivetag`; network storage (a NAS) is for extra backup copies only.
- **Ingress**: a **Cloudflare Tunnel**. `cloudflared` runs as a compose service,
  dials out to Cloudflare and forwards to `http://nginx:8080` on the compose
  network. **No port is published on the host** and the firewall is not touched.
  Cloudflare terminates TLS, so the origin certificate and port 443 are gone. The
  tunnel token is a SecureString in Parameter Store (`/motivetag/cloudflare-tunnel-token`).
  nginx keeps rate limits and security headers and trusts `CF-Connecting-IP` from the
  compose network's fixed subnet only.
- **AWS access**: the Pi is an **SSM hybrid managed node** (activation in
  `infra/main/iam.tf`, role `motivetag-app` trusted by `ssm.amazonaws.com`). The SSM
  agent keeps short-lived credentials for that role in root's `~/.aws/credentials`
  and renews them; no long-lived AWS keys exist anywhere. Root's one-off jobs
  (deploy, backup, restore drill) mount that directory. The long-running app gets
  them through `deploy/aws_creds_relay.py`, a container that answers botocore's
  IMDSv2 calls (`AWS_EC2_METADATA_SERVICE_ENDPOINT`), so its boto3 clients refresh
  as they did on EC2.
- **Delivery**: unchanged in shape (ADR 0003). CI builds and tests an **arm64**
  image on GitHub's `ubuntu-24.04-arm` runners, pushes it to ECR and runs
  `deploy/deploy.sh` on the managed node (found by tag `Project=motivetag`) through
  SSM Run Command. Standard-tier hybrid nodes are free; Session Manager would need
  the advanced tier (about US$5/month), so shells use SSH on the home network.

## Consequences

- EC2, EBS and Elastic IP costs drop to zero; the remaining AWS bill is the free
  tiers plus a few cents (ECR storage, image pulls over the internet, S3).
- Availability is the home's power and internet: no automatic hardware recovery,
  and the CloudWatch EC2 alarms are gone. An outside uptime check on `/healthz` and
  the Grafana dashboard stand in for them; backups still go to S3 every day.
- An SD card wears out under MySQL writes; a USB SSD for `/srv/motivetag` is the
  first upgrade. Restore from S3 is drilled weekly either way.
- `cloudflared` restarts with the stack; a deploy that fails health checks rolls back
  to the previous image, tunnel included.

## Alternatives considered

- **Opening a port on the router**: exposes the home IP and needs a static address;
  the tunnel needs neither.
- **IAM user access keys on the Pi**: long-lived secrets on a home machine.
- **IAM Roles Anywhere**: short-lived too, but needs our own CA and certificates;
  SSM also keeps CI's Run Command deploys.
- **GitHub self-hosted runner on the Pi**: a public repository's pull requests could
  run code on the home network.
- **No containers (systemd + venv, MySQL from apt)**: slightly less memory, but the
  image is the release artifact that rollback, backups and the drill rely on.

## Revisit when

- The home connection or power proves unreliable (move back to a small cloud VM;
  `aws-ec2-final` has the Terraform).
- Memory on the Pi stays above ~80 % (move MySQL to an SSD-backed host or tune it).
