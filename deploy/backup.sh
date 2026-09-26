#!/bin/bash
# Daily MySQL backup to S3. deploy.sh installs this with the motivetag-backup systemd
# timer; run it by hand with `systemctl start motivetag-backup`.
# Every run publishes BackupSuccess (1 or 0); a CloudWatch alarm fires when a day
# passes without a 1 (infra/main/monitoring.tf).
set -euo pipefail

APP_DIR=/srv/motivetag/app
OUT=/srv/motivetag/backups
KEEP_LOCAL=3

cd "$APP_DIR"
env_value() { grep "^$1=" .env | cut -d= -f2-; }
IMAGE=$(env_value APP_IMAGE)
REGION=$(env_value AWS_REGION)
BUCKET=$(env_value BACKUP_BUCKET)

# Runs a backup_s3.py command inside the app image (boto3 + the instance role).
s3() {
  docker run --rm --user 0 -e AWS_REGION="$REGION" -v "$OUT:/backups" \
    --entrypoint python "$IMAGE" deploy/backup_s3.py "$@"
}

report() {
  local status=$?
  s3 metric BackupSuccess "$([ "$status" = 0 ] && echo 1 || echo 0)" || true
  rm -f "$OUT"/*.partial
  exit "$status"
}
trap report EXIT

[ -n "$BUCKET" ] || { echo "BACKUP_BUCKET is not set in $APP_DIR/.env" >&2; exit 1; }
mkdir -p "$OUT"
umask 077
name="motivetag-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"

# --single-transaction takes a consistent InnoDB snapshot without locking the site.
# The root password stays inside the mysql container's environment.
docker compose exec -T mysql sh -c 'exec mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" \
    --single-transaction --routines --triggers --events --databases motivetag' \
  | gzip > "$OUT/$name.partial"

# A dump cut short (disk full, killed server) lacks mysqldump's closing line.
zcat "$OUT/$name.partial" | tail -n 1 | grep -q '^-- Dump completed' \
  || { echo "dump is incomplete" >&2; exit 1; }
mv "$OUT/$name.partial" "$OUT/$name"

s3 upload "$BUCKET" "/backups/$name"

# A few recent dumps stay on the server for a fast restore; S3 is the real copy.
ls -1t "$OUT"/motivetag-*.sql.gz | tail -n +$((KEEP_LOCAL + 1)) | xargs -r rm --
