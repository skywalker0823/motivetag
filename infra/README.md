# Infrastructure

Terraform for the AWS side of motivetag. Everything runs from your Mac with the
`motivetag` AWS CLI profile (IAM Identity Center / SSO, so no long-lived keys).

| Directory | What it creates | State |
|---|---|---|
| `bootstrap/` | S3 bucket that stores Terraform state (run once) | local file |
| `main/` | SSM activation and role for the Raspberry Pi, GitHub deploy role, ECR, S3 buckets, secrets, SES, SNS alerts | in that S3 bucket |

The site runs on a Raspberry Pi at home behind a Cloudflare Tunnel
([ADR 0017](../docs/adr/0017-raspberry-pi-behind-cloudflare-tunnel.md)); until
2026-11 it ran on EC2, kept as the git tag `aws-ec2-final`.

Why things are set up this way: [`docs/adr/`](../docs/adr/README.md).

## Before you start

- AWS CLI signed in: `aws sts get-caller-identity --profile motivetag` works.
- Tools: `brew install awscli session-manager-plugin` and
  `brew tap hashicorp/tap && brew install hashicorp/tap/terraform`.
- Using the Taipei region (`ap-east-2`)? It is opt-in: enable it first under
  Account → AWS Regions.

## First run

```bash
export AWS_PROFILE=motivetag

# 1. State bucket (once per AWS account)
cd infra/bootstrap
terraform init
terraform apply -var region=ap-east-2
# copy the printed next_step command

# 2. The server
cd ../main
cp terraform.tfvars.example terraform.tfvars   # set region
terraform init -backend-config="bucket=motivetag-tfstate-<account-id>" -backend-config="region=ap-east-2"
terraform plan    # read it: expect ~8 resources to add
terraform apply
```

Commit the `.terraform.lock.hcl` files that `terraform init` creates.

## Check the server

On the home network (the Pi accepts SSH from there only):

```bash
ssh pikxl@192.168.0.145
sudo docker --version && sudo docker compose version
systemctl is-active amazon-ssm-agent   # active
df -h /srv/motivetag
```

## Moving to the Raspberry Pi (one time)

Do these in order. Nothing here opens a port on the Pi or the router. The site is
offline until step 6, and starts with an **empty database** (the EC2 data was
discarded in November 2026).

1. **Terraform** (Mac). Removes what is left of the EC2 setup (instance profile,
   security group) and creates the Pi's SSM activation.

   ```bash
   cd ~/Desktop/dev/motivetag
   git fetch origin && git switch pi-migration     # main once the PR is merged
   cd infra/main
   export AWS_PROFILE=motivetag
   aws sso login --profile motivetag               # if the session expired
   sed -i '' '/^paused/d' terraform.tfvars         # the variable no longer exists
   terraform init
   terraform plan
   ```

   Expect roughly: **add** `aws_ssm_activation.pi`; **change** `aws_iam_role.app`
   (trusted by SSM instead of EC2), `aws_iam_role_policy.github_deploy` and the backup
   lifecycle rule; **destroy** `aws_iam_instance_profile.app` and
   `aws_security_group.app` (plus the old data volume if it was never deleted).
   Nothing else may be destroyed. Then `terraform apply`.

2. **Cloudflare Tunnel** (Cloudflare dashboard, works on a phone).
   - DNS → delete the old `A` record `motivetag.com` (the EC2 address) and the
     `www` `CNAME`, if they exist; the tunnel creates its own.
   - Zero Trust → Networks → Tunnels → **Create a tunnel** → Cloudflared → name
     `motivetag-pi` → on the install page, copy only the **token** (the long text
     after `--token`). Do not run the command shown; the token goes to Parameter
     Store instead.
   - **Public hostnames**: `motivetag.com` → Service `HTTP` · `nginx:8080`, and
     `www.motivetag.com` → `HTTP` · `nginx:8080`.
   - Store the token (Mac; `read -s` keeps it off the screen and out of the shell
     history; paste, then Enter):

     ```bash
     read -rs TOKEN && aws ssm put-parameter --name /motivetag/cloudflare-tunnel-token \
       --type SecureString --value "$TOKEN" --region ap-east-2 --profile motivetag; unset TOKEN
     ```

     It prints `{"Version": 1, "Tier": "Standard"}`.
   - Free: Cloudflare Tunnel costs nothing. SSL/TLS mode, Always Use HTTPS, WAF and
     rate-limiting rules stay as they are.

3. **SSM agent on the Pi** (SSH from the home network):

   ```bash
   cd /tmp && curl -fsSLO https://s3.ap-east-2.amazonaws.com/amazon-ssm-ap-east-2/latest/debian_arm64/amazon-ssm-agent.deb
   sudo dpkg -i amazon-ssm-agent.deb && rm amazon-ssm-agent.deb
   sudo snap install aws-cli --classic     # CI's deploy command uses it for the ECR login
   ```

4. **Register the Pi** (Mac, same `infra/main` directory). The activation code goes
   from Terraform straight to the Pi over SSH and is never shown:

   ```bash
   terraform output -json pi_activation | ssh pikxl@192.168.0.145 \
     'python3 -c "import json,subprocess,sys; a=json.load(sys.stdin); subprocess.run([\"sudo\",\"amazon-ssm-agent\",\"-register\",\"-y\",\"-code\",a[\"code\"],\"-id\",a[\"id\"],\"-region\",a[\"region\"]],check=True)" && sudo systemctl restart amazon-ssm-agent'
   aws ssm describe-instance-information --region ap-east-2 \
     --query 'InstanceInformationList[].[InstanceId,PingStatus,PlatformName]' --output table
   ```

   The table shows one `mi-…` row, `Online`. On the Pi,
   `sudo ls -l /root/.aws/credentials` shows the file the agent keeps fresh (owner
   root, `-rw-------`). The code works once and for 24 hours; for a new one:
   `terraform apply -replace=aws_ssm_activation.pi`. Free: standard-tier hybrid
   nodes cost nothing (do not switch on the advanced tier, about US$5/month).

5. **GitHub** (works in the app): Settings → Secrets and variables → Actions →
   Variables: delete `SITE_PAUSED`. The other variables (`AWS_REGION`,
   `AWS_DEPLOY_ROLE_ARN`, `ECR_REPOSITORY_URL`, `IMAGE_BUCKET`) stay as they are
   (`terraform output github_variables`).

6. **First deploy**: merge the pull request (or Actions → CI → Run workflow on
   `main`). CI builds the arm64 image, pushes it to ECR and runs `deploy.sh` on the
   Pi. The job ends with `https://motivetag.com/healthz through Cloudflare: HTTP 200`.

7. **Admin account**: the database is empty; see "Resume" below.

8. **Clean up (optional, free either way)**: the origin certificate is unused now.
   `aws ssm delete-parameters --names /motivetag/tls/origin-cert /motivetag/tls/origin-key --region ap-east-2 --profile motivetag`,
   and Cloudflare → SSL/TLS → Origin Server → revoke the old certificate.

## Purging the Cloudflare cache on deploy (one time)

After each deploy CI purges Cloudflare's cache, so visitors never get an old
stylesheet or script. The step is skipped until these two are set:

1. **API token.** Cloudflare → My Profile → API Tokens → Create Token → **Custom
   token**. Permissions: `Zone` · `Cache Purge` · `Purge`. Zone Resources:
   `Include` · `Specific zone` · `motivetag.com`. Create it and copy the token (shown once).
2. **Zone ID.** Cloudflare → motivetag.com → Overview → right-hand column, **Zone ID**.
3. **GitHub.** Settings → Secrets and variables → Actions:
   - **Secrets** tab → New repository secret `CLOUDFLARE_API_TOKEN` = the token.
   - **Variables** tab → New repository variable `CLOUDFLARE_ZONE_ID` = the zone ID.

The token can only purge this zone's cache; nothing else in the account.

## Demo data

A fresh site looks empty, so `scripts/demo_data.py` can add 16 demo members with
posts, polls, comments, likes, friendships and tag-board topics spread over the past
two weeks. It uses the site's own API, so every rule applies as for real members.
Demo members have `@demo.motivetag.com` e-mail addresses and random passwords.

From your phone or anywhere: GitHub → **Actions** → **Demo data** → **Run workflow**
→ choose `seed` or `remove`. `remove` deletes every demo member and what they made
(including their tag-board topics) and recounts the tags they used; real members'
posts, comments and subscriptions are not touched.

## Operating the server

```bash
ssh pikxl@192.168.0.145
cd /srv/motivetag/app
sudo docker compose ps                           # service status
sudo docker compose logs -f app                  # app logs
sudo docker compose logs --tail 50 cloudflared   # tunnel: "Registered tunnel connection"
cat current_image                                # deployed image
```

Migrations run on container start. Write them so the previous release still works
with the new schema, because a rollback does not undo a migration.

## Backups, monitoring and Sentry (one time)

Everything here stays within free tiers (see `docs/adr/0006`). **Apply before merging
this change to `main`**: image uploads need the bucket's new CORS rule.

1. **E-mail for alerts.** Add `alert_email = "you@example.com"` to
   `infra/main/terraform.tfvars`.
2. **Apply.**

   ```bash
   cd infra/main
   terraform init
   terraform plan    # backup bucket, SNS topic + e-mail, 3 alarms, 2 parameters, images CORS
   terraform apply
   ```

3. **Confirm the SNS e-mail.** Until you click it, alerts go nowhere.
4. **Sentry (optional, free tier).** Create a Flask project in Sentry, copy its DSN:

   ```bash
   aws ssm put-parameter --name /motivetag/sentry-dsn --type SecureString --value 'https://...@....ingest.sentry.io/...' --region ap-east-2
   ```

   The next deploy picks it up; without it Sentry stays off.
5. **Merge to `main`.** The deploy installs the backup and restore-drill timers.
6. **Check on the server** (SSH to the Pi, `sudo -i`):

   ```bash
   systemctl list-timers 'motivetag-*'           # next backup / drill times
   systemctl start motivetag-backup               # first backup now
   journalctl -u motivetag-backup -n 20
   systemctl start motivetag-restore-drill        # prove it restores
   journalctl -u motivetag-restore-drill -n 40
   ```

## Sign-up protection: Turnstile and e-mail verification (one time)

Both are off until set up, and each can be done on its own (`docs/adr/0011`).
Commands use the `motivetag` profile from the Mac; in CloudShell leave out
`--profile motivetag`.

### Cloudflare Turnstile (free, about 5 minutes)

1. Cloudflare dashboard → **Turnstile** → **Add widget**: name `MotiveTag`, hostname
   `motivetag.com`, mode **Managed**. Copy the **Site Key** and the **Secret Key**.
2. Store both (the page shows the widget and the server checks it only when both
   exist):

   ```bash
   aws ssm put-parameter --name /motivetag/turnstile-site-key --type String --value 'SITE_KEY' --region ap-east-2 --profile motivetag
   aws ssm put-parameter --name /motivetag/turnstile-secret --type SecureString --value 'SECRET_KEY' --region ap-east-2 --profile motivetag
   ```

   Each prints `{"Version": 1, "Tier": "Standard"}`.
3. Redeploy: GitHub → **Actions** → **CI** → **Run workflow** (branch `main`); the
   GitHub app can do this too. The 註冊 form then shows the Cloudflare check.

### E-mail verification with Amazon SES

Costs US$0.10 per 1,000 e-mails after the first year's free 3,000 a month; the app
sends at most 500 a day (about US$1.50 a month at the very most).

1. **Create the sending identity.**

   ```bash
   cd infra/main
   terraform plan    # 3 to add (SES identity, bounce suppression, /motivetag/ses-region), 1 to change (app role may send e-mail)
   terraform apply
   terraform output ses_dns_records
   ```

2. **Add the DNS records** it lists in Cloudflare → DNS: three `CNAME`
   (`…._domainkey`) and one `TXT` (`_dmarc`), all **DNS only** (grey cloud). If a
   `_dmarc` record already exists, keep yours. Then check (can take up to an hour):

   ```bash
   aws sesv2 get-email-identity --email-identity motivetag.com --region ap-northeast-1 --profile motivetag --query VerifiedForSendingStatus
   ```

   It prints `true` when SES sees the records.
3. **Ask AWS for production access** (new accounts can only mail addresses they
   verified themselves):

   ```bash
   aws sesv2 put-account-details --region ap-northeast-1 --profile motivetag \
     --production-access-enabled --mail-type TRANSACTIONAL --contact-language EN \
     --website-url https://motivetag.com \
     --use-case-description "MotiveTag (https://motivetag.com) is a small social network. We only send one transactional e-mail: a link to confirm the address a person entered when signing up. Sending is limited to one message per minute and five per day per member, and 500 per day in total. Sign-up is protected by Cloudflare Turnstile and refuses disposable addresses. Bounces and complaints are handled by the SES account-level suppression list. No marketing e-mail is sent."
   ```

   AWS answers by e-mail, usually within a day. Check with
   `aws sesv2 get-account --region ap-northeast-1 --profile motivetag --query ProductionAccessEnabled`.
4. **Turn verification on** once approved: add `email_enabled = true` to
   `terraform.tfvars`, then

   ```bash
   terraform apply   # 1 to add: /motivetag/email-from
   ```

   and redeploy (**Run workflow** as above). New members now get the e-mail;
   existing members count as verified.
5. **Try it:** sign up a test account with your own address, find the mail (also in
   the spam folder the first time), click the link: the yellow banner disappears and
   posting works.

## Reviewing reports (one time, free)

Members can report posts, comments, chat messages and accounts (ADR 0014). Reports are
reviewed on **https://motivetag.com/admin**, which only the accounts listed in
`/motivetag/admin-accounts` can open (everyone else gets 404). Apple expects reports
to be handled within 24 hours once there is an iOS app.

1. Store your MotiveTag account name (several: comma-separated, no spaces), from your
   Mac or AWS CloudShell:

   ```bash
   aws ssm put-parameter --name /motivetag/admin-accounts --type String --value 'YOUR_ACCOUNT' --region ap-east-2 --profile motivetag
   ```

   (In CloudShell leave out `--profile motivetag`.) It prints
   `{"Version": 1, "Tier": "Standard"}`. To change it later add `--overwrite`.
2. Redeploy: GitHub → **Actions** → **CI** → **Run workflow** (branch `main`); the
   GitHub app can do this too.
3. Open `/admin` while signed in. New reports also arrive in your bell (通知) as
   「有一則新的檢舉待處理」. A post whose reports weigh 3 or more (a Lv 10 member's
   report counts twice) is hidden until you decide: **刪除內容** deletes it for good,
   **保留** closes the reports and shows it again.

## Contact e-mail for the privacy policy (one time, free)

`/privacy` and `/terms` show an address people can write to (Apple requires one for
the App Store). Until it is set they point to the in-site report instead.

```bash
aws ssm put-parameter --name /motivetag/contact-email --type String --value 'you@example.com' --region ap-east-2 --profile motivetag
```

Then **Run workflow** (GitHub → Actions → CI, branch `main`).

## Phone notifications (Web Push, one time, free)

Notifications for new chat messages and friend requests (ADR 0016) need a key pair
that only the server knows. In AWS CloudShell (or on the Mac), make one:

```bash
openssl ecparam -name prime256v1 -genkey -noout -out vapid.pem
python3 - <<'PY'
import base64, re, subprocess
text = subprocess.run(["openssl", "ec", "-in", "vapid.pem", "-text", "-noout"], capture_output=True, text=True).stdout
hexes = lambda part: bytes.fromhex(re.sub(r"[^0-9a-f]", "", part))
b64 = lambda raw: base64.urlsafe_b64encode(raw).decode().rstrip("=")
private = hexes(re.search(r"priv:(.*?)pub:", text, re.S).group(1))[-32:].rjust(32, b"\0")
public = hexes(re.search(r"pub:(.*?)ASN1", text, re.S).group(1))
print("PUBLIC=" + b64(public))
print("PRIVATE=" + b64(private))
PY
rm vapid.pem
```

It prints two lines, `PUBLIC=` (87 characters) and `PRIVATE=` (43 characters). Store
them (replace the values; in CloudShell leave out `--profile motivetag`):

```bash
aws ssm put-parameter --name /motivetag/vapid-public-key --type String --value 'PUBLIC_VALUE' --region ap-east-2 --profile motivetag
aws ssm put-parameter --name /motivetag/vapid-private-key --type SecureString --value 'PRIVATE_VALUE' --region ap-east-2 --profile motivetag
```

Each prints `{"Version": 1, "Tier": "Standard"}`. Then **Run workflow**. In 帳號設定 →
手機通知, 開啟通知 now asks for permission. Never change the keys once people have
subscribed: their subscriptions would stop working until they turn notifications on
again.

## Daily NASA picture (APOD, free)

The member **NASA_APOD** posts NASA's Astronomy Picture of the Day every day
(`module/apod.py`, `scripts/apod.py`), from the server's `motivetag-apod.timer` at
14:00 and again at 20:00 Taiwan time (a day already posted is skipped). The account is
created on its first run; nobody can sign in as it. It works with nothing set up.

- **Post now** instead of waiting: GitHub → **Actions** → **APOD post** → **Run
  workflow** (`dry-run` only shows the post; `repost` deletes the bot's post for that
  day and posts it again; **date** picks another day). The GitHub app can do this too.
- The bot reads the day's APOD page itself (apod.nasa.gov now redirects to
  science.nasa.gov/apod/): api.nasa.gov's APOD API returned NASA's logo and the title
  "NASA Science" on 2026-10-05. If NASA changes the page again, the bot posts nothing
  and the workflow fails with "could not read the APOD page"; save the page's source
  as a new file in `tests/fixtures/` so the parser can be fixed against it.
- **Pictures that belong to their photographers**: NASA's own pictures are public
  domain and are posted with the photo. Many APOD pictures are copyrighted by the
  photographer (APOD shows their name); those days post the text, the credit and the
  link only. To copy those pictures too (at your own risk; APOD asks you to get the
  photographer's permission):

  ```bash
  aws ssm put-parameter --name /motivetag/apod-copyrighted-images --type String --value 1 --region ap-east-2 --profile motivetag
  ```

  (In CloudShell leave out `--profile motivetag`.) Then **Run workflow** on CI.
- Check the timer on the server: `systemctl list-timers motivetag-apod.timer` and
  `journalctl -u motivetag-apod.service -n 20`.

## Backups

- Daily at 03:00 Taipei time: `mysqldump` → gzip → `s3://<backup_bucket>/mysql/`
  (kept 35 days). The last three dumps also stay in `/srv/motivetag/backups`.
- Sundays at 04:30: the restore drill loads the newest dump into a throwaway MySQL
  container, checks it, and logs the backup age and restore time. Production is
  only read.
- A failure of either job e-mails its last log lines. The drill also fails when the
  newest backup is more than 26 hours old (the daily job stopped running).
- The server can add backups but not delete them. List them from your Mac:
  `aws s3 ls s3://$(terraform output -raw backup_bucket)/mysql/`.

### Restoring production

```bash
ssh pikxl@192.168.0.145
sudo -i && cd /srv/motivetag/app

# 1. Pick a dump: a local one, or the newest from S3.
ls -lt /srv/motivetag/backups/
docker run --rm --user 0 -e AWS_REGION=ap-east-2 -v /root/.aws:/root/.aws:ro \
  -v /srv/motivetag/backups:/backups --entrypoint python "$(cat current_image)" deploy/backup_s3.py latest \
  "$(grep ^BACKUP_BUCKET= .env | cut -d= -f2)" /backups
# (An older one: aws s3 cp s3://<bucket>/mysql/<file> . on your Mac, then upload it.)

# 2. Keep a copy of the current state, then stop writes.
systemctl start motivetag-backup
docker compose stop cloudflared nginx app

# 3. Load it. The dump recreates every table it contains.
zcat /srv/motivetag/backups/<file>.sql.gz \
  | docker compose exec -T mysql sh -c 'exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD"'

# 4. Start again (migrations bring an older schema up to date).
docker compose up -d --wait
```

The weekly drill times step 3; expect about the same.

## Monitoring

| Alert | When |
|---|---|
| "MySQL backup failed" / "Restore drill failed" | The job failed; the e-mail has its last log lines |
| "… is NN% full" | `/` or `/srv/motivetag` over 85 %, checked daily by the backup job |

Application errors go to Sentry when `/motivetag/sentry-dsn` is set, tagged with
the git SHA. The Grafana Cloud dashboard (below) shows memory, requests, errors,
latency and sign-in failures. Nothing checks from outside that the site is reachable yet; a free
UptimeRobot or Better Stack monitor on `https://motivetag.com/healthz` would (it
also fails when the database is down).

### Dashboard on Grafana Cloud (free, one time)

CPU, memory, disk, network, requests, errors, latency and sign-ins on one page
(`docs/adr/0012`). Grafana Alloy runs next to the app once the three settings below
exist; about 400–1,500 series at one sample a minute, well inside the free tier's
10,000.

1. **Sign up** at https://grafana.com (free plan, no card). Create a stack, e.g.
   `motivetag`; pick an Asia region if offered.
2. **Find the Prometheus details:** grafana.com → *My Account* → your stack →
   **Prometheus** → *Details* (or *Send metrics*). Note the **Remote Write
   Endpoint** (`https://prometheus-prod-….grafana.net/api/prom/push`) and the
   **Username / Instance ID** (a number).
3. **Create a token** that can only write metrics: *Administration* → *Users and
   access* → **Access policies** → *Create access policy* (scope `metrics:write`)
   → *Add token*. It starts with `glc_`.
4. **Store the three values:**

   ```bash
   aws ssm put-parameter --name /motivetag/grafana-prom-url --type String --value 'https://prometheus-prod-XX-prod-XX.grafana.net/api/prom/push' --region ap-east-2 --profile motivetag
   aws ssm put-parameter --name /motivetag/grafana-prom-user --type String --value '1234567' --region ap-east-2 --profile motivetag
   aws ssm put-parameter --name /motivetag/grafana-cloud-token --type SecureString --value 'glc_...' --region ap-east-2 --profile motivetag
   ```

5. **Redeploy:** GitHub → Actions → CI → **Run workflow** on `main`. In the server
   Pi (`sudo -i`), `docker ps` now lists `motivetag-alloy-1`, and
   `docker logs --tail 20 motivetag-alloy-1` shows no `401`/`403`.
6. **Import the dashboard:** open `deploy/grafana/motivetag-overview.json` on
   GitHub → *Raw* → copy everything. In your Grafana (`https://<stack>.grafana.net`)
   → *Dashboards* → *New* → **Import** → paste → *Load* → pick the
   `grafanacloud-…-prom` data source → *Import*. Data appears within two minutes.

## Pausing the site (and bringing it back)

On the Pi nothing is billed while it runs, so pausing only takes the site offline:

```bash
ssh pikxl@192.168.0.145
cd /srv/motivetag/app && sudo docker compose stop     # data stays in /srv/motivetag/mysql
```

Add the repository variable `SITE_PAUSED` = `true` in GitHub so CI skips the deploy
and the APOD and demo-data workflows. To bring it back, delete the variable and run
Actions → CI → Run workflow on `main`.

### Resume with an empty database

After a move to a new machine the database starts empty. Sign-up refuses the names
in `/motivetag/admin-accounts`, so free the name, sign up as yourself on
https://motivetag.com, then put it back and run the workflow again (Mac, profile
`motivetag`):

```bash
NAME=$(aws ssm get-parameter --name /motivetag/admin-accounts --query Parameter.Value --output text)
aws ssm put-parameter --name /motivetag/admin-accounts --value none --overwrite
# ... Run workflow, sign up as "$NAME" on the site ...
aws ssm put-parameter --name /motivetag/admin-accounts --value "$NAME" --overwrite
# ... Run workflow again: /admin opens for you
```

Then run the **Demo data** or **APOD post** workflows if wanted.

## Notes

- No inbound port anywhere: the Pi's firewall admits only SSH from the home network,
  the router forwards nothing, and visitors arrive through the Cloudflare Tunnel.
- The Pi has no long-lived AWS keys; the SSM agent renews short-lived role
  credentials in `/root/.aws/credentials` (ADR 0017).
- The EC2 setup (Terraform, runbook) is the git tag `aws-ec2-final`.

