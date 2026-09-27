# MotiveTag: notes for Claude sessions

A tag-based social network, live at https://motivetag.com. One owner maintains it and
uses it as a portfolio project for interviews. Read this first, then `README.md`,
`infra/README.md` (operations) and `docs/adr/` (why things are the way they are).

## Working with the owner

- **Reply in Traditional Chinese (繁體中文)**, even when they paste English.
  Code, comments, commit messages and repo docs stay in English.
- **Give complete, copy-paste commands** for everything they must run themselves
  (git, terraform, AWS, server shell), in order, with what the output should look like.
  They often work from a phone; say when something can be done from the GitHub app.
- **No new costs.** Anything that adds to the AWS/Cloudflare bill needs their OK first,
  with the monthly amount. Free tiers are fine.
- They merge PRs themselves. Work on the branch the session names; if its PR is
  already merged, restart the branch from `origin/main`. GitHub deletes merged
  branches, so a plain `git push -u` (not `--force-with-lease`) recreates it.
- They verify on the live site, so be precise about what was tested and what was not.

## Architecture (see README.md for the diagram)

- **Hosting:** one EC2 `t3.small` in Taipei (`ap-east-2`), Ubuntu, `docker compose`
  with nginx (TLS with a Cloudflare origin cert), the Flask app (gunicorn + gevent,
  one worker: chat presence is in memory, ADR 0008) and MySQL 8.4 on its own EBS volume.
- **Edge:** Cloudflare Full (strict). The security group only admits Cloudflare's
  ranges on 443. **The owner geo-blocks visitors in Cloudflare** (Taiwan only at
  first; US traffic allowed since 2026-09-27), so checks from other regions may get
  403; deploy.sh checks the site from the server itself.
- **Deploy:** push to `main` → CI (ruff, pytest against MySQL, Alembic up/down/up,
  terraform validate, pip-audit, Trivy, JS parse + import check, image smoke test) →
  image to ECR (tag = git SHA) → SSM Run Command runs `deploy/deploy.sh` from that
  image → compose up, rollback on failure → Cloudflare cache purge. GitHub uses OIDC,
  no AWS keys.
- **Infra:** Terraform in `infra/` (state in S3 `motivetag-tfstate-766995240060`,
  region `ap-east-2`). The owner runs it from their home Mac with the `motivetag`
  AWS SSO profile, or from AWS CloudShell (instructions were given in chat; the
  `terraform.tfvars` there needs `region` and `alert_email`).
- **Backups:** daily mysqldump to S3 + weekly automated restore drill (systemd timers
  installed by deploy.sh, ADR 0004). Failures e-mail through SNS.
- **Monitoring ($0):** EC2 status/CPU alarms, script alerts, Sentry (only if a DSN is
  set). There is no outside uptime check (ADR 0006).
- **Secrets:** SSM Parameter Store under `/motivetag/`, read at deploy time.

## Code map

- `api/blueprints/` older endpoints under `/api/...` (errors often HTTP 200 +
  `{"error": ...}`); `api/v1/` new endpoints: real status codes,
  `{"error": {"code", "message"}}` (ADR 0010). New or reworked endpoints go to v1.
- `data/data.py` all SQL (PyMySQL + DBUtils pool; one connection per request via
  `flask.g`, never a shared connection: gevent interleaves requests).
- `module/rules.py` input limits; `module/clock.py` server timestamps;
  `module/tag_filter.py` hashtag rule (`#` + letters/digits/_, ends at punctuation;
  the browser uses the same regex in `static/js/pages/member/post.js`).
- `api/assets.py` versioned static URLs (`?v=<hash>`, cached a year), import map and
  `modulepreload`; templates include `templates/_head.html`.
- Frontend: plain HTML/CSS + native ES modules, no build step (ADR 0009).
  `static/css/base.css` tokens and components; `static/js/lib/` framework-free helpers
  (api, dom `h()`, icons, time, toast, upload, confirm, lightbox, socket, tour);
  `static/js/pages/` one folder per page. Socket.IO client is vendored in `static/vendor/`.
- `migrations/versions/` Alembic, applied on container start. Migrations must keep the
  previous release working (a rollback does not undo them).
- `scripts/demo_data.py` demo members and activity (`seed` / `remove`), run in
  production through the **Demo data** GitHub Actions workflow.

## Gotchas already paid for

- `.gitignore` entries for Python packaging are anchored to the root (`/lib/`); an
  unanchored `lib/` once kept `static/js/lib/` out of git and broke production. After
  adding files, check `git ls-files --others --ignored --exclude-standard static templates`.
- The database stores **Taipei wall-clock** times and Flask serialises them with a
  misleading "GMT" suffix; `static/js/lib/time.js` `fromServer()` corrects for it.
  Moving to UTC is phase 0 of ADR 0010.
- MySQL must be connected as `utf8mb4` (emoji).
- Playwright's `route()` turns the browser HTTP cache off; block external hosts with
  `--host-resolver-rules` when measuring caching.

## Local development and checks

```bash
docker run -d --name motivetag-mysql -p 3306:3306 -e MYSQL_ROOT_PASSWORD=testpw -e MYSQL_DATABASE=motivetag mysql:8.4
export AWS_motivetag_DB=127.0.0.1 DB_PASSWORD=testpw
uv run alembic upgrade head
uv run ruff check && uv run ruff format --check
uv run pytest
for f in $(git ls-files 'static/js/*.js'); do node --check "$f"; done && node .github/scripts/check-js-imports.mjs
FLASK_CONFIG=dev uv run python app.py            # http://localhost:3000
FLASK_CONFIG=dev uv run python scripts/demo_data.py seed   # demo content locally
```

In the Claude Code cloud sandbox: start `dockerd` yourself; the Terraform registry is
blocked (install providers from releases.hashicorp.com into a filesystem mirror);
Docker Hub may rate-limit image builds; cdnjs is blocked for browsers.

## Status and next steps (as of 2026-09-27)

Everything above is merged and deployed except where noted.

**Waiting on the owner**
- `terraform apply` in `infra/main` for PR #23: adds `s3:DeleteObject` to the app
  role so account deletion also removes images (plan: 0 add, 1 change, 0 destroy).
  Until then deletion works but leaves image files in S3.
- Run the **Demo data** workflow (`seed`) once, if they want the site to look active.

**Done in PR #26:** photos shrunk to WebP in the browser; `/images/<key>` reuses its
presigned URL for 30 min; presence, calls and notifications pushed over Socket.IO
(polls are 30 s / 60 s fallbacks); feed pages of 10. Redis reviewed and deliberately
not added yet (see ADR 0008). CloudFront judged unnecessary behind Cloudflare.

**Done in PR #27:** feed tabs 我的動態 / 探索 (`GET /api/v1/posts/explore`); empty
feed offers trending tags in one tap; first-visit guided tour (`static/js/lib/tour.js`,
steps in `static/js/pages/member/tour.js`, "?" button replays it); landing page opens
on 註冊 for new browsers.

**On branch `claude/sharp-bohr-bhm8n5` (not merged yet)**
- Secret posts' images are private (`/images/block_<id>` checks `Block.visible`).
- Search icon centred in the top bar; shorter placeholder on phones.

**Roadmap (ADR 0010, phase 1 next)**
1. Report content and block members (App Store Guideline 1.2).
2. Privacy policy and terms pages (mention backups keep deleted data up to 35 days).
3. Optional: a small "示範" badge on demo accounts, or remove them once real people join.
4. Then phase 0/2/3: UTC timestamps, OpenAPI + shared TypeScript core, React + Vite
   (`apps/web`), token auth, cursor paging, Redis presence; phase 4 Expo app.

**Other ideas offered, not started**
- Run Terraform from GitHub Actions (plan on PRs, apply with approval) so infra
  changes work from a phone.
- A free external uptime monitor (UptimeRobot / Better Stack) needs a Cloudflare
  exception because of the Taiwan-only rule.
- Undecided: whether member cards should show birthdays.
