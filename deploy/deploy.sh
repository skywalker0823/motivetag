#!/bin/bash
# Deploys one app image on the server. Run as root by SSM Run Command from CI:
#   deploy.sh <image-uri> <aws-region> <image-bucket>
# The image is already pulled; this script ships inside it.
set -euo pipefail

IMAGE=$1
REGION=$2
BUCKET=$3
DIR=/srv/motivetag/app

mkdir -p "$DIR/certs" /srv/motivetag/mysql
cd "$DIR"
umask 077

# compose.yaml and nginx.conf come from the same image, so a release is one artifact.
docker run --rm --entrypoint cat "$IMAGE" deploy/compose.yaml > compose.yaml
docker run --rm --entrypoint cat "$IMAGE" deploy/nginx.conf > nginx.conf

# Check the Cloudflare origin certificate before touching the running stack:
# nginx exits on a bad certificate, which would take the site down.
# Secrets are read with boto3 inside the app image (instance role via IMDS); the host's
# snap AWS CLI returned empty values when run from SSM.
docker run --rm --user 0 -e AWS_REGION="$REGION" -v "$DIR:/out" \
  --entrypoint python "$IMAGE" deploy/fetch_params.py
if ! openssl x509 -noout -in certs/origin.pem.new 2>/dev/null; then
  echo "/motivetag/tls/origin-cert is not a PEM certificate (first line must be -----BEGIN CERTIFICATE-----)" >&2
  exit 1
fi
if ! openssl pkey -noout -in certs/origin.key.new 2>/dev/null; then
  echo "/motivetag/tls/origin-key is not a PEM private key (first line must be -----BEGIN PRIVATE KEY-----)" >&2
  exit 1
fi
if [ "$(openssl x509 -noout -pubkey -in certs/origin.pem.new)" != "$(openssl pkey -pubout -in certs/origin.key.new)" ]; then
  echo "/motivetag/tls/origin-cert and /motivetag/tls/origin-key are not a matching pair" >&2
  exit 1
fi
mv certs/origin.pem.new certs/origin.pem
mv certs/origin.key.new certs/origin.key

# SECRET_KEY, DB_PASSWORD, DB_ROOT_PASSWORD, BACKUP_BUCKET, ALERT_TOPIC_ARN,
# SENTRY_DSN, EMAIL_FROM, SES_REGION, TURNSTILE_SITE_KEY, TURNSTILE_SECRET
# shellcheck source=/dev/null
. ./params.env
rm params.env

write_env() {
  cat > .env <<ENV
APP_IMAGE=$1
AWS_REGION=$REGION
IMAGE_BUCKET=$BUCKET
SECRET_KEY=$SECRET_KEY
DB_PASSWORD=$DB_PASSWORD
DB_ROOT_PASSWORD=$DB_ROOT_PASSWORD
BACKUP_BUCKET=$BACKUP_BUCKET
ALERT_TOPIC_ARN=$ALERT_TOPIC_ARN
SENTRY_DSN=$SENTRY_DSN
EMAIL_FROM=$EMAIL_FROM
SES_REGION=$SES_REGION
TURNSTILE_SITE_KEY=$TURNSTILE_SITE_KEY
TURNSTILE_SECRET=$TURNSTILE_SECRET
ENV
}

# Backup and restore-drill scripts and their systemd timers ship in the image too.
install_jobs() {
  local cid
  cid=$(docker create "$IMAGE")
  docker cp "$cid:/app/deploy/backup.sh" backup.sh
  docker cp "$cid:/app/deploy/restore_drill.sh" restore_drill.sh
  docker cp "$cid:/app/deploy/systemd/." /etc/systemd/system/
  docker rm "$cid" >/dev/null
  chmod 644 /etc/systemd/system/motivetag-*
  systemctl daemon-reload
  systemctl enable --now motivetag-backup.timer motivetag-restore-drill.timer
}

# The public path (Cloudflare → origin certificate → security group → nginx) checked
# from this server: CI runners are abroad, and the site may block non-Taiwan visitors.
check_public() {
  local code
  for _ in $(seq 1 10); do
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 https://motivetag.com/healthz || true)
    echo "https://motivetag.com/healthz through Cloudflare: HTTP $code"
    case $code in
      200) return 0 ;;
      403) echo "Cloudflare refused this server's address (a country or WAF rule); the origin itself is healthy" >&2
           return 0 ;;
    esac
    sleep 6
  done
  echo "The site is not reachable through Cloudflare, although the containers are healthy" >&2
  return 1
}

previous=$(cat current_image 2>/dev/null || true)

write_env "$IMAGE"
if docker compose up -d --remove-orphans --wait --wait-timeout 300; then
  echo "$IMAGE" > current_image
  echo "Deployed $IMAGE"
  install_jobs
  docker image prune -af --filter "until=168h" >/dev/null
  check_public
  exit 0
fi

echo "Deploy of $IMAGE failed; recent app logs:" >&2
docker compose logs --tail 100 app >&2 || true
if [ -n "$previous" ]; then
  echo "Rolling back to $previous" >&2
  write_env "$previous"
  docker compose up -d --remove-orphans --wait --wait-timeout 300 || true
fi
exit 1
