# 0003. Deploy with GitHub OIDC, ECR and SSM Run Command

- Status: Accepted
- Date: 2026-09-26

## Context

Deploys should happen on every merge to `main`, without long-lived AWS keys in
GitHub, without SSH, and with a way back when a release is broken.

## Decision

- **CI gates** (`.github/workflows/ci.yml`): ruff, integration tests against a real
  MySQL, Alembic up/down/up, `terraform validate`, `pip-audit`, a Trivy scan and a
  smoke test of the production image. The `deploy` job needs all of them.
- **Authentication**: GitHub Actions gets short-lived AWS credentials through
  **OIDC**. The IAM role trusts only `repo:skywalker0823/motivetag:ref:refs/heads/main`
  and can only push to one ECR repository and run `AWS-RunShellScript` on instances
  tagged `Project=motivetag`.
- **Artifact**: the image is pushed to ECR tagged with the **git SHA**; the
  repository is **immutable**, so a tag always means the same bytes. The last 20
  images are kept for rollbacks.
- **Rollout**: CI calls **SSM Run Command** on the instance, which pulls the image
  and runs `deploy/deploy.sh` taken from that same image. The script writes the
  config, runs `docker compose up --wait`, and if the new containers do not become
  healthy within 5 minutes it **rolls back to the previous image** and fails the job.
- Migrations run on container start; they must be backwards compatible because a
  rollback does not undo them.
- After the rollout, CI checks `https://motivetag.com/healthz` through Cloudflare.

## Consequences

- No AWS secrets in GitHub; a leaked workflow on another branch cannot deploy.
- The deploy logic is versioned with the code it deploys.
- Rollback is automatic for "doesn't start"; a release that starts but is wrong
  needs a revert on `main` (or re-running an older workflow).
- Migrations constrain how schema changes are written (expand, then contract).

## Alternatives considered

- **Static access keys in GitHub secrets** — long-lived credentials to rotate and leak.
- **SSH from CI** — needs an open port and a private key in GitHub.
- **ECS/CodeDeploy** — would bring blue/green, but only with the ECS setup
  [0001](0001-single-ec2-with-docker-compose.md) moved away from.
- **Watchtower / polling the registry** — no clear link between a commit and a
  deploy result, and no gate on CI.

## Revisit when

Deploy downtime becomes noticeable, or there is more than one server.
