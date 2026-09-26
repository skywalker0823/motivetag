# 0001. Run everything on one EC2 instance with docker compose

- Status: Accepted
- Date: 2026-09-26

## Context

The 2022 version of motivetag ran on ECS behind an Application Load Balancer, with
RDS for MySQL and CloudFront for images. It worked, but the fixed monthly cost of
those managed pieces was more than a hobby project with a handful of users could
justify, and the site was taken offline for that reason.

Relaunching it needs a setup that is cheap enough to leave running indefinitely,
that one person can operate, and that is still built the way production systems
are: infrastructure as code, immutable images, automated deploys and rollbacks,
backups, monitoring.

Traffic is low and uneven; the app keeps chat presence in process memory
([0008](0008-single-gunicorn-worker.md)), so it cannot scale horizontally anyway
without a code change.

## Decision

- One `t3.small` Ubuntu 24.04 instance in the default VPC, in Taipei (`ap-east-2`,
  close to the users). Terraform in `infra/main/` creates it.
- The whole stack is one `docker compose` project (`deploy/compose.yaml`): nginx,
  the Flask app, MySQL 8.4. The compose file ships inside the app image, so a
  release is a single artifact.
- MySQL data sits on a separate encrypted EBS volume with `prevent_destroy`, so the
  instance can be rebuilt (`terraform apply -replace=aws_instance.app`) without
  touching the data.
- The instance keeps a fixed Elastic IP for the Cloudflare DNS record.
- A 2 GB swap file gives MySQL headroom on 2 GB of RAM.

## Consequences

- Cost is roughly one small instance, two EBS volumes and some S3, instead of
  instance + ALB + RDS + NAT/CloudFront.
- The server is a single point of failure. Mitigations: EC2 auto-recovery on a
  failed system status check, automatic reboot on a failed instance check
  ([0006](0006-monitoring-and-alerting.md)), a rebuildable instance with data on
  its own volume, and off-server backups ([0004](0004-mysql-backups-and-restore-drills.md)).
  A zone outage still means downtime until we restore elsewhere.
- Deploys restart containers on the same host, so there is a few seconds of
  downtime per release. Acceptable at this traffic.
- We own OS patching and MySQL operations that RDS would handle.

## Alternatives considered

- **ECS on Fargate + RDS + ALB** — what we had; the fixed cost is the problem.
- **EKS** — a control plane fee and far more moving parts than one service needs.
- **Lightsail** — cheaper still, but a weaker fit for IAM roles, SSM and Terraform.
- **Fly.io / Render / a PaaS** — less to operate, but less AWS and IaC practice,
  and managed MySQL is the expensive part there too.

## Revisit when

Sustained CPU or memory alarms, a need for zero-downtime deploys, or a second app
process (which first requires [0008](0008-single-gunicorn-worker.md) to change).
The next step up would be RDS for the database, then two instances behind an ALB.
