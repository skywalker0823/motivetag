#!/bin/bash
# Weekly restore drill: loads the newest S3 backup into a throwaway MySQL container,
# checks the result and reports how long it took. Production is only read from.
# Installed by deploy.sh with the motivetag-restore-drill systemd timer; run it by
# hand with `systemctl start motivetag-restore-drill`, then
# `journalctl -u motivetag-restore-drill` for the report.
set -euo pipefail

APP_DIR=/srv/motivetag/app
WORK=/srv/motivetag/backups/drill
DRILL=motivetag-restore-drill

cd "$APP_DIR"
env_value() { grep "^$1=" .env | cut -d= -f2-; }
IMAGE=$(env_value APP_IMAGE)
REGION=$(env_value AWS_REGION)
BUCKET=$(env_value BACKUP_BUCKET)
TOPIC=$(env_value ALERT_TOPIC_ARN)

s3() {
  docker run --rm -i --user 0 -e AWS_REGION="$REGION" -v "$WORK:/backups" \
    --entrypoint python "$IMAGE" deploy/backup_s3.py "$@"
}

report() {
  local status=$?
  if [ "$status" != 0 ] && [ -n "$TOPIC" ]; then
    journalctl -u motivetag-restore-drill -n 40 --no-pager 2>/dev/null \
      | s3 alert "$TOPIC" "motivetag: Restore drill failed" || true
  fi
  docker rm -f "$DRILL" >/dev/null 2>&1 || true
  rm -rf "$WORK"
  exit "$status"
}
trap report EXIT

[ -n "$BUCKET" ] || { echo "BACKUP_BUCKET is not set in $APP_DIR/.env" >&2; exit 1; }
umask 077
mkdir -p "$WORK"
started=$(date +%s)

latest=$(s3 latest "$BUCKET" /backups)
read -r dump age_hours <<< "$latest"
file="$WORK/$(basename "$dump")"
echo "Newest backup: $(basename "$dump"), ${age_hours}h old"
# Daily backups mean the newest is never much more than a day old.
if [ "${age_hours%.*}" -ge 26 ]; then
  echo "newest backup is ${age_hours}h old; is motivetag-backup.timer running?" >&2
  exit 1
fi

# Same MySQL version as production, data on tmpfs so nothing is left behind.
password=$(openssl rand -hex 16)
mysql_image=$(grep -m1 'image: mysql' compose.yaml | awk '{print $2}')
docker run -d --name "$DRILL" --memory 768m --tmpfs /var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD="$password" "$mysql_image" --innodb-buffer-pool-size=64M >/dev/null
sql() { docker exec -i -e MYSQL_PWD="$password" "$DRILL" mysql -uroot -h127.0.0.1 -N "$@"; }

# The image's init server skips networking, so TCP answers only once MySQL is ready.
for _ in $(seq 1 60); do
  sql -e 'SELECT 1' >/dev/null 2>&1 && break
  sleep 2
done
sql -e 'SELECT 1' >/dev/null 2>&1 || { echo "drill MySQL did not start" >&2; exit 1; }

zcat "$file" | sql
restored=$(date +%s)

# The restored schema must be one Alembic knows, and the core tables must hold rows.
version=$(sql motivetag -e 'SELECT version_num FROM alembic_version')
[ -n "$version" ] || { echo "restored database has no alembic_version" >&2; exit 1; }
echo "Schema version: $version"
printf '%-24s %10s %10s\n' table restored production
for table in $(sql motivetag -e 'SHOW TABLES'); do
  [ "$table" = alembic_version ] && continue
  count=$(sql motivetag -e "SELECT COUNT(*) FROM \`$table\`")
  live=$(docker compose exec -T mysql sh -c \
    "mysql -uroot -p\"\$MYSQL_ROOT_PASSWORD\" -N -e 'SELECT COUNT(*) FROM motivetag.\`$table\`' 2>/dev/null" || echo '?')
  printf '%-24s %10s %10s\n' "$table" "$count" "$live"
done
members=$(sql motivetag -e 'SELECT COUNT(*) FROM member')
[ "$members" -gt 0 ] || { echo "restored member table is empty" >&2; exit 1; }

seconds=$((restored - started))
echo "Restore drill passed: backup ${age_hours}h old (RPO), restored in ${seconds}s (RTO for the data)"
