# 0002. Cloudflare Full (strict) in front; no SSH

- Status: Accepted
- Date: 2026-09-26

## Context

A single public server ([0001](0001-single-ec2-with-docker-compose.md)) needs TLS,
some protection from the open internet, and a way for admins to get a shell.
Running an ALB or managing Let's Encrypt renewals just for TLS adds cost or moving
parts; an open SSH port adds keys to manage and an attack surface.

## Decision

- DNS for `motivetag.com` is proxied by Cloudflare (orange cloud) with SSL mode
  **Full (strict)**: browsers talk TLS to Cloudflare, Cloudflare talks TLS to the
  origin and verifies its certificate.
- nginx on the server terminates TLS with a 15-year **Cloudflare Origin CA
  certificate**. The certificate and key live in Parameter Store and are written to
  disk by the deploy, which validates them (PEM, matching pair) before touching the
  running stack.
- The security group allows **only TCP 443, only from Cloudflare's published IPv4
  ranges** (fetched by Terraform at plan time). Port 80 is closed; Cloudflare's
  "Always Use HTTPS" handles redirects at the edge.
- **No SSH** and no key pairs. Shell access is AWS Systems Manager Session
  Manager, authorised by IAM and logged by CloudTrail.
- nginx answers unknown host names with 444 and redirects `www` to the apex.
- IMDSv2 is required on the instance.

## Consequences

- No certificate renewals to run, and the origin cannot be reached around
  Cloudflare by IP address.
- Cloudflare is in the request path; an outage there takes the site down, and the
  origin trusts whatever Cloudflare forwards.
- Cloudflare's IP list is read at `terraform plan`; if it changes, a new apply
  picks it up.
- Admin access requires the AWS CLI with the Session Manager plugin.

## Alternatives considered

- **ALB + ACM certificate** — managed TLS, but a fixed monthly cost for one target.
- **Let's Encrypt on the instance** — needs port 80 open or DNS challenges, and a
  renewal job to watch.
- **Authenticated origin pulls (mTLS from Cloudflare)** — a sensible next hardening
  step on top of the IP allow-list.

## Revisit when

Adding IPv6 at the origin, adding a second origin, or needing to verify that
requests really came from our Cloudflare zone (authenticated origin pulls).
