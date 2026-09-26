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

# SECRET_KEY, DB_PASSWORD, DB_ROOT_PASSWORD, BACKUP_BUCKET, SENTRY_DSN
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
SENTRY_DSN=$SENTRY_DSN
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

previous=$(cat current_image 2>/dev/null || true)

write_env "$IMAGE"
if docker compose up -d --remove-orphans --wait --wait-timeout 300; then
  echo "$IMAGE" > current_image
  echo "Deployed $IMAGE"
  install_jobs
  docker image prune -af --filter "until=168h" >/dev/null
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
