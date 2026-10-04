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
  set). There is no outside uptime check (ADR 0006). Dashboard on Grafana Cloud's
  free tier (ADR 0012): Grafana Alloy (`deploy/alloy.alloy`, compose profile
  `monitoring`, on only with the three `/motivetag/grafana-*` parameters) ships host
  metrics and the app's `/metrics` (`api/metrics.py`); dashboard JSON in
  `deploy/grafana/`.
- **Secrets:** SSM Parameter Store under `/motivetag/`, read at deploy time.

## Code map

- `api/blueprints/` older endpoints under `/api/...` (errors often HTTP 200 +
  `{"error": ...}`); `api/v1/` new endpoints: real status codes,
  `{"error": {"code", "message"}}` (ADR 0010). New or reworked endpoints go to v1.
- `data/data.py` all SQL (PyMySQL + DBUtils pool; one connection per request via
  `flask.g`, never a shared connection: gevent interleaves requests).
- `module/levels.py` exp rewards, daily caps and level unlocks (mirrored in
  `static/js/lib/levels.js`); `module/admin.py` who may open `/admin`.
- `module/rules.py` input limits; `module/clock.py` server timestamps;
  `module/tag_filter.py` hashtag rule (`#` + letters/digits/_, ends at punctuation;
  the browser uses the same regex in `static/js/pages/member/post.js`).
- `api/assets.py` versioned static URLs (`?v=<hash>`, cached a year), import map and
  `modulepreload`; templates include `templates/_head.html`.
- Frontend: plain HTML/CSS + native ES modules, no build step (ADR 0009).
  `static/css/base.css` tokens and components; `static/js/lib/` framework-free helpers
  (api, dom `h()`, icons, time, toast, upload, confirm, lightbox, socket, tour,
  pull-refresh, collapsible, levels, report, emoji);
  `static/js/pages/` one folder per page. `module/urls.py` `public_base_url()` for
  absolute links (e-mail, invites, og tags). Socket.IO client is vendored in `static/vendor/`.
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
- SSM `GetParameters` takes at most 10 names; `deploy/fetch_params.py` batches them
  (a deploy failed at 12). Values in Parameter Store are sourced as shell by
  deploy.sh, so they must not contain spaces or quotes.
- nginx resolves `app` once at start and compose does not restart a running nginx:
  a recreated app on a new address gave 502s (2026-09-28, when Alloy took the old
  address). deploy.sh now runs `nginx -t && nginx -s reload` after every `up`,
  which also applies a changed `nginx.conf`.
- Trivy fails CI (and so skips the deploy) when the python base image ships a Debian
  package with a fixed HIGH/CRITICAL CVE (2026-10-04, libpcre2: PR #43 did not deploy
  until fixed). The Dockerfile runs `apt-get upgrade`, rebuilt weekly through the
  `SECURITY_REFRESH` build argument (ISO week). The sandbox proxy blocks
  deb.debian.org, so that layer cannot be checked locally; CI shows it.
- The app counts days in Taiwan time, MySQL's `CURDATE()` is UTC: tests must build
  dates with `taipei_datetime()`, or they fail between 00:00 and 08:00 Taiwan time
  (main's CI after PR #48 failed at 00:04 on the streak test).
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
# Try e-mail verification locally: the e-mail (with its link) goes to the log.
EMAIL_FROM=no-reply@motivetag.com MAIL_SUPPRESS=1 FLASK_CONFIG=dev uv run python app.py
```

In the Claude Code cloud sandbox: start `dockerd` yourself; the Terraform registry is
blocked (install providers from releases.hashicorp.com into a filesystem mirror);
Docker Hub may rate-limit image builds; cdnjs and challenges.cloudflare.com
(Turnstile) are blocked, so stub Turnstile's script with Playwright `route()`.
`dockerd` does not survive between turns: restart it and `docker start motivetag-mysql`.

## Status and next steps (as of 2026-10-04)

Everything above is merged and deployed except where noted.

**Waiting on the owner**
- Web Push: `/motivetag/contact-email` is set (2026-10-04); the two
  `/motivetag/vapid-*` keys were being created in CloudShell, then Run workflow
  (`infra/README.md`, "Phone notifications"). Confirm a push arrives on the phone.
  Never ask them to paste the VAPID private key into chat.
- Put their account name in `/motivetag/admin-accounts`
  and Run workflow (`infra/README.md`, "Reviewing reports"), so `/admin` opens.
- Run the **Demo data** workflow (`seed`) once, if they want the site to look active.
- Grafana Cloud dashboard setup (`infra/README.md`, "Dashboard on Grafana Cloud"):
  sign up, three parameters, Run workflow, import the dashboard JSON.
- SES production access: the owner replied to AWS's request for details
  (case 179058323800303); after approval, `email_enabled = true` + apply + Run
  workflow.
- Sign-up protection setup (`infra/README.md`, "Sign-up protection"). Done
  2026-09-28: SES `terraform apply` (identity in ap-northeast-1; this also applied
  PR #23's `s3:DeleteObject`). Still to do: the 3 DKIM CNAMEs + `_dmarc` TXT in
  Cloudflare (done; identity verified), SES production access (pending), then
  `email_enabled = true` + apply; Turnstile keys into Parameter Store. Each part is
  off until done.

**Done in PR #26:** photos shrunk to WebP in the browser; `/images/<key>` reuses its
presigned URL for 30 min; presence, calls and notifications pushed over Socket.IO
(polls are 30 s / 60 s fallbacks); feed pages of 10. Redis reviewed and deliberately
not added yet (see ADR 0008). CloudFront judged unnecessary behind Cloudflare.

**Done in PR #27:** feed tabs 我的動態 / 探索 (`GET /api/v1/posts/explore`); empty
feed offers trending tags in one tap; first-visit guided tour (`static/js/lib/tour.js`,
steps in `static/js/pages/member/tour.js`, "?" button replays it); landing page opens
on 註冊 for new browsers.

**Done in PR #28:** secret posts' images are private (`/images/block_<id>` checks
`Block.visible`); search icon centred.

**Done in PR #29:** pull-to-refresh (`static/js/lib/pull-refresh.js`), "有新貼文"
pill, phone top bar hides on scroll, one-line composer on phones, double-tap image
to like.

**Done in PR #30:** "可能合得來的人" suggestions (`GET /api/v1/members/suggested`), shared
tags and age (never the birthday) on member cards, 18+ sign-up. The owner is
considering an adults-only dating direction; report/block and dealing with the demo
accounts were recommended first.

**Done in PR #31** (ADR 0011):
- E-mail verification: link e-mailed at sign-up (`module/email_verification.py`,
  `email_token` table, migration 0003; existing members count as verified).
  Unverified members can read but not post, comment, invite, open topics or chat
  (`verified_required`). Limits: 1/minute and 5/day per member, 500/day site-wide.
- SES via `infra/main/ses.tf` (Tokyo, `ses_region`); `/motivetag/email-from` only
  exists when `email_enabled = true`, and it switches verification on.
- Cloudflare Turnstile on sign-up (`module/turnstile.py`, fails closed; on only with
  both `/motivetag/turnstile-site-key` and `-secret`); disposable domains refused
  (`module/disposable.py`, CC0 list in `module/disposable_domains.txt`).
- CI gained **Run workflow** (workflow_dispatch) on `main` to redeploy after a
  Parameter Store change.

**Done in PR #32:** a re-run on `main` deploys the commit's existing ECR image
instead of failing on the immutable tag.

**Done in PR #33:** `fetch_params.py` reads SSM in batches of 10 (PR #31's deploy
had failed on 12 names; production stayed on PR #30 until then).

**Done in PR #34** (ADR 0012; Grafana Cloud stack `humblesturgeon2584`, data flowing):
- `/metrics` (prometheus-client): requests by route pattern/method/status, latency
  histogram, auth events, online members; nginx and the app refuse it from outside.
- Grafana Alloy container + `deploy/alloy.alloy`; deploy.sh sets
  `COMPOSE_PROFILES=monitoring` when the Grafana settings exist.
- Dashboard `deploy/grafana/motivetag-overview.json` (26 panels), verified locally
  with Alloy → Prometheus → Grafana 12.1 (images via `mirror.gcr.io`, Docker Hub
  rate-limits this sandbox; Playwright needs `locale: "zh-TW"` for Grafana).
- Owner asked next for security monitoring: audit log of sign-ins, lockout after
  failed logins, "recent logins" for members, admin page, maybe logs to Loki.

**Done in PR #35:** deploy.sh reloads nginx after `compose up` (see Gotchas).

**Cloudflare (set by hand, 2026-09-28):** custom rules `deny !tw&US` (country not TW/US →
block) and `Block scanners` (`/wp-`, `.php`, `/.env`, `/.git`, `/phpmyadmin`);
rate-limiting rule `API flood guard` (`/api/`, 60 requests / 10 s per IP → block 10 s).

**Done in PR #36** (promotion):
- Open Graph / Twitter tags on the landing page, preview image `static/img/og.png`
  (1200×630, rendered from HTML with Playwright).
- Invite links (`module/invites.py`: member id signed with SECRET_KEY, salt
  "invite"): `/?invite=<token>`; the landing page names the inviter (also in
  og:title); signing up with it makes both friends (`Friend.connect`) and notifies
  the inviter; metric event `signup_invited`. "邀請朋友" card uses the Web Share API
  or copies the link (`static/js/pages/member/invite.js`).
- The country rule blocks link-preview crawlers outside TW/US (LINE's are in Japan);
  the owner was given an exception expression for `/` and `/img/og.png`.

**Done in PR #37:**
- Collapsible side cards (`static/js/lib/collapsible.js`, `data-collapse-key` on
  tags, trend, invite, suggested, friends; remembered in localStorage). Folded cards
  still show `setCardBadge` (friends: requests + unread chats) and `setCardNote`
  (online friends, suggestion and tag counts). The tour unfolds cards it points at.
- The friends list reloads on a pushed "notification" (new requests appeared only
  after a refresh before).

**Done in PR #38** (ADR 0013)
- Chat rebuilt Messenger-style. The old one was a "call": in-memory rooms keyed by
  socket id, both sides online, the callee had to notice "想跟你聊天" and click;
  a second tab or a reconnect (new sid) split people into different rooms, and
  messages were never stored. Now messages live in `direct_message` (migration
  0004), are sent over HTTP (`/api/v1/chats...`) and pushed as `chat:message` to
  every tab of both members; `chat:read` (已讀) and `chat:typing` (正在輸入).
  Friends only, 1000 chars, 30 messages/minute per member.
- `online` is now `{account: {sids}}`: offline only when the last tab goes.
- UI: topbar 聊天 button (unread badge, conversation list, online friends row),
  docked windows with history, day separators, receipts, retry on failure; full
  screen on phones; unread counts on the friends list and in the page title.

**Done in PR #39:**
- Blocking and reporting (ADR 0014; ADR 0010 phase 1 done except privacy/terms):
  `member_block`, `report`, `block.hidden` (migration 0005); `/api/v1/blocks`,
  `POST /api/v1/reports` (post, comment, received message, member; 20/day). Blocking
  ends friendship, hides their posts/comments from me, stops chat, typing, invites,
  notifications and suggestions both ways. Reported things leave the reporter's view;
  posts with report weight ≥ 3 hidden until reviewed (Lv 10 reports weigh 2). Owner
  reviews on `/admin` (`ADMIN_ACCOUNTS` from Parameter Store, 404 for others); new
  reports ring the admins' bell; metric `motivetag_reports_total`. UI: flag on posts,
  comments, tapping a received chat bubble; 檢舉/封鎖 on member cards; block list in
  帳號設定. No account suspension yet.
- Levels reworked (ADR 0015, migration 0006 converts exp so no level changes):
  curve 50·(n−1)²; daily-capped rewards in `exp_daily` (visit +10, 7-day streak +50,
  post +20×3, comment +5×10, like given +1×20; authors +5 per like, +3 per comment,
  +3 per comment like); boos, chat and self-interaction earn nothing. Below Lv 3:
  10 posts/day, no tag topics; Lv 5 avatar frame; Lv 10 double-weight reports.
  Badges on posts/comments/chat/cards (never anonymous posts); `exp` socket push
  moves the bar and toasts level-ups. Demo members start at Lv 3–8.

**Done in PR #40:**
- 讚/爛 are exclusive and a second tap takes them back: `PUT /api/v1/posts/<id>/reaction`
  (`like` | `dislike` | null) and `PUT /api/v1/comments/<id>/like` (`liked`); counts
  are recounted from `goods`/`bads`/`c_goods`. A like earns exp once per post (or
  comment) a day (`levels.once_today`, key `like:<id>` in `exp_daily`), so toggling
  earns nothing. The old `PATCH`/`PUT /api/blocks` also keep one reaction.

**Done in PR #41:**
- Emoji picker (`static/js/lib/emoji.js`, no library: emoji are text in the system
  font) on the post composer, comments, chat and tag-topic replies; "最近" tab kept in
  localStorage; bottom sheet on phones. Outside-click check uses `composedPath()`
  because switching tabs re-renders the clicked button away.

**Done in PR #43** (deployed only after the Trivy fix below):
- Photos in chat (ADR 0013 addendum, migration 0007 `direct_message.image`):
  `POST /api/v1/chats/<account>/images` → presigned POST for `dm_<sender>_<hex32>`
  (20 per 10 min in memory), browser uploads (shrunk to WebP by `upload.js`), then
  `POST …/messages {image, content?}`. `/images/dm_…` only for sender, recipient or
  admin; reports keep the key in the snapshot and `/admin` shows the photo; account
  deletion removes photos both ways. UI: photo button, paste and drag-and-drop,
  preview while uploading, tap to enlarge, "📷 照片" in lists and toasts.
  Note: `from api.blueprints import api_images` is the Blueprint, not the module;
  import names from `api.blueprints.api_images`.

**Done in PR #44:** Dockerfile `apt-get upgrade` + weekly `SECURITY_REFRESH` so Trivy
passes (see Gotchas); main went green and deployed.

**Done in PR #45:**
- Personal cards and site look (`api/v1/profile.py`, `member_profile`, migration 0008):
  card colours for everyone (accent, cover gradient from/to, name colour; `#rrggbb`
  only), cover photo from Lv 5 (`levels.COVER_LEVEL`; upload type `cover` → key
  `cover_<id>`, `/images/cover_<id>?v=<updated_at>`). Shown on my profile card, the
  settings preview and others' member cards (`get_user_sp` returns `card`;
  `static/js/pages/member/card.js` sets CSS variables). Look in 帳號設定 → 外觀:
  mode dark/light/black, accent sky/violet/green/pink/orange/gold, text normal/large;
  saved with the account (`PUT /api/v1/me/ui`), set on `<html data-mode/accent/text>`
  by the member page template and, on other pages, by an inline script in
  `_head.html` from a localStorage copy. Light-mode and accent tokens in `base.css`;
  `--accent-soft`, `--focus` and the bar backgrounds are `color-mix()` of the tokens.

**Done in PR #46** (owner wants the App Store; the installed PWA works on their iPhone)
- Gender icon next to names (`member_profile.gender`, migration 0009; male / female /
  nonbinary / none; `PUT /api/v1/me/gender`; `static/js/lib/gender.js`): posts,
  comments, member cards, chat header, my profile; never on anonymous posts.
- `/privacy` and `/terms` (`templates/legal.html` + `privacy.html`, `terms.html`),
  linked from sign-up and settings; `CONTACT_EMAIL` from `/motivetag/contact-email`.
- PWA + Web Push (ADR 0016): `/manifest.webmanifest` and `/sw.js` have explicit routes
  (the `/<account>` route would take them); icons `static/img/icon-*.png`;
  `module/push.py` (pywebpush, VAPID raw keys from `/motivetag/vapid-*`, sent in a
  background task, only to members not online, 404/410 forgets the subscription);
  `api/v1/push.py`; `push_subscription` table; pushes on chat messages and bell
  notifications; tapping a chat push opens `/<me>?chat=<them>`. `Vapid.from_raw`
  takes the base64url string, not bytes.

**Done in PR #47:** installed-app top bar kept below the iPhone status bar
(`--safe-top: env(safe-area-inset-top)` in `base.css`, used by `.topbar`, `.page-bar`,
`.lightbox__close`). Deployed 2026-10-04; the owner's Run workflow for the VAPID keys
also succeeded that day (push on the phone not yet confirmed).

**Done in PR #48**: first step of the
App Store road (owner, 2026-10-04: move towards the Apple app step by step):
- Account suspension (`module/suspension.py`, migration 0010 `member.suspended_until`
  / `suspended_reason`; for good = 9999-12-31). A suspended member cannot sign in (the
  sign-in error says until when and why); an open session ends on its next request
  (`before_request` in `api/__init__.py`: 401 `suspended` for `/api/`, redirect for
  pages) and its sockets are disconnected (`end_sessions`; the member page goes to `/`).
  State cached 30 s in memory, cleared on change (one worker). `/admin`: "停權帳號" on
  report cards (1/3/7/30 days or for good, reason), tab 停權中 with lift and a form
  to suspend by account name; admins cannot be suspended; suspending resolves the
  open reports about the account. Posts and comments stay. Metric event
  `login_suspended`.

**Done in PR #49:** streak test uses Taiwan dates (see Gotchas).

**Done in PR #50**: admin tools and
sign-in protection (owner asked whether /admin is safe and for "god mode" tools):
- `/admin` is now sections 總覽 / 檢舉 / 會員 / 公告 / 紀錄 (`static/js/pages/admin.js`
  + `static/js/pages/admin/`). 總覽 (`GET /api/v1/admin/stats`): members (demo
  excluded, demo = e-mail `@demo.motivetag.com`), online, active today/7 days
  (`last_active_day`), new sign-ups, posts/comments/messages, open reports,
  suspended; sign-ups and posts per day for 14 days (bar charts); top posters and
  levels. 會員 (`GET /api/v1/admin/members?q=`): search by account or e-mail, facts,
  and actions: set level (`PUT .../level {level|exp}`, pushes `exp` with action
  `admin`), mark e-mail verified, send a notice (bell + Web Push), suspend/lift.
  公告 (`POST /api/v1/admin/announcements`): one bell notification for every
  non-demo member, no pushes. 紀錄: `admin_log` table (migration 0011) of every
  admin action (`GET /api/v1/admin/logs`).
- Sign-in lockout (`module/lockout.py`, in memory): 10 wrong passwords for an
  account within 15 minutes → 429 for the rest of the window; metric
  `login_locked`. Someone can lock another account out for 15 minutes this way.
- Sign-up refuses a name in `ADMIN_ACCOUNTS` (case-insensitive), and admin checks
  in `/admin` actions compare case-insensitively (MySQL matches accounts that way).

**On branch `claude/beautiful-faraday-a61bzb` (not merged yet)**: admins see a
"管理後台" button on their profile card (under 我 on phones), with the number of open
reports; the member page template gets `admin` only when `is_admin()`.

**UI/UX backlog (offered 2026-10-04, owner to pick)**
- Phones: move 登出 out of the top bar into 我 / 帳號設定; put 聊天 and 通知 in the
  bottom tab bar (5 tabs) so the top bar only holds logo + search; search as an icon
  that expands (the input is squeezed to "搜…" at 390px); 44px tap targets;
  a floating "發文" button instead of the always-visible composer; swipe back from a
  full-screen chat; visible pressed states.
- Desktop: wider feed column, the chat list as a right-hand dock, keyboard shortcuts
  (`/` search, `n` new post, `Esc` closes).
- Both: skeleton loaders instead of blank cards, optimistic likes/comments,
  an unread divider in chats, settings split into pages.

**Roadmap (ADR 0010, phase 1 done)**
1. ~~Account suspension on `/admin`~~ (PR #48).
2. Optional: a small "示範" badge on demo accounts, or remove them once real people join.
3. Then phase 0/2/3: UTC timestamps, OpenAPI + shared TypeScript core, React + Vite
   (`apps/web`), token auth, cursor paging, Redis presence; phase 4 Expo app.

**Other ideas offered, not started**
- Run Terraform from GitHub Actions (plan on PRs, apply with approval) so infra
  changes work from a phone.
- A free external uptime monitor (UptimeRobot / Better Stack) needs a Cloudflare
  exception because of the Taiwan-only rule.
