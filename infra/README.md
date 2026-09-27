# Infrastructure

Terraform for the AWS side of motivetag. Everything runs from your Mac with the
`motivetag` AWS CLI profile (IAM Identity Center / SSO, so no long-lived keys).

| Directory | What it creates | State |
|---|---|---|
| `bootstrap/` | S3 bucket that stores Terraform state (run once) | local file |
| `main/` | EC2 server, data volume, Elastic IP, security group, IAM roles, ECR, S3 buckets, secrets, backups, monitoring | in that S3 bucket |

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

```bash
$(terraform output -raw connect)   # shell on the server via Session Manager, no SSH
docker --version && docker compose version
df -h /srv/motivetag               # the separate data volume
```

## Going live (one time)

Do these in order; the last step (merging to `main`) triggers the first deploy.

1. **Apply the deploy stack.** After pulling the latest `main`:

   ```bash
   cd infra/main
   terraform init        # installs the new http and random providers
   terraform plan        # ~16 to add, 1 to change (security group gets port 443)
   terraform apply
   ```

   It creates the ECR repository, the private image bucket, generated secrets in
   Parameter Store, and the GitHub OIDC deploy role, and opens 443 to Cloudflare only.

2. **Cloudflare origin certificate.** Cloudflare → your domain → SSL/TLS →
   Origin Server → Create Certificate (keep the defaults: `motivetag.com`,
   `*.motivetag.com`, 15 years). Save the two text boxes as `origin.pem` and
   `origin.key`, then store them in Parameter Store and delete the local key:

   ```bash
   aws ssm put-parameter --name /motivetag/tls/origin-cert --type SecureString --value file://origin.pem --region ap-east-2
   aws ssm put-parameter --name /motivetag/tls/origin-key  --type SecureString --value file://origin.key --region ap-east-2
   rm origin.key
   ```

3. **Cloudflare settings.**
   - SSL/TLS → Overview → encryption mode **Full (strict)**.
   - SSL/TLS → Edge Certificates → **Always Use HTTPS** on.
   - DNS → add `A` record `@` → the `public_ip` output, **Proxied** (orange cloud);
     add `CNAME` `www` → `motivetag.com`, Proxied.

4. **GitHub repository variables.** `terraform output github_variables`, then add
   each key/value under Settings → Secrets and variables → Actions → **Variables**
   (not secrets; none of them is sensitive).

5. **Merge to `main`.** CI runs, then the `deploy` job builds the image, pushes it to
   ECR tagged with the commit SHA, and runs `deploy/deploy.sh` on the server through
   SSM. If the new version is unhealthy it rolls back to the previous image and the
   job fails. To redeploy without a code change: Actions → CI → the latest `main`
   run → Re-run all jobs.

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
$(terraform output -raw connect)             # shell via Session Manager
sudo -i && cd /srv/motivetag/app
docker compose ps                            # service status
docker compose logs -f app                   # app logs
cat current_image                            # deployed image
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
6. **Check on the server** (Session Manager shell, `sudo -i`):

   ```bash
   systemctl list-timers 'motivetag-*'           # next backup / drill times
   systemctl start motivetag-backup               # first backup now
   journalctl -u motivetag-backup -n 20
   systemctl start motivetag-restore-drill        # prove it restores
   journalctl -u motivetag-restore-drill -n 40
   ```

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
$(terraform output -raw connect)
sudo -i && cd /srv/motivetag/app

# 1. Pick a dump: a local one, or the newest from S3.
ls -lt /srv/motivetag/backups/
docker run --rm --user 0 -e AWS_REGION=ap-east-2 -v /srv/motivetag/backups:/backups \
  --entrypoint python "$(cat current_image)" deploy/backup_s3.py latest \
  "$(grep ^BACKUP_BUCKET= .env | cut -d= -f2)" /backups
# (An older one: aws s3 cp s3://<bucket>/mysql/<file> . on your Mac, then upload it.)

# 2. Keep a copy of the current state, then stop writes.
systemctl start motivetag-backup
docker compose stop nginx app

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
| `motivetag-system-check-failed` | AWS hardware problem; the instance is recovered automatically |
| `motivetag-instance-check-failed` | The OS stops responding; the instance is rebooted automatically |
| `motivetag-cpu-high` | CPU > 80 % for 15 minutes |
| "MySQL backup failed" / "Restore drill failed" | The job failed; the e-mail has its last log lines |
| "… is NN% full" | `/` or `/srv/motivetag` over 85 %, checked daily by the backup job |

Application errors go to Sentry when `/motivetag/sentry-dsn` is set, tagged with
the git SHA. Nothing checks from outside that the site is reachable yet; a free
UptimeRobot or Better Stack monitor on `https://motivetag.com/healthz` would (it
also fails when the database is down).

## Notes

- There is no SSH; the only inbound port is 443, from Cloudflare's IP ranges.
- The data volume has `prevent_destroy`; `terraform destroy` stops on it on purpose.
- Changing the AMI or `user_data.sh.tftpl` does not replace a running server
  (`ignore_changes`). To rebuild: `terraform apply -replace=aws_instance.app`
  (the data volume is kept and re-attached).
