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

param() {
  aws ssm get-parameter --region "$REGION" --with-decryption \
    --name "/motivetag/$1" --query Parameter.Value --output text
}

# compose.yaml and nginx.conf come from the same image, so a release is one artifact.
docker run --rm --entrypoint cat "$IMAGE" deploy/compose.yaml > compose.yaml
docker run --rm --entrypoint cat "$IMAGE" deploy/nginx.conf > nginx.conf
param tls/origin-cert > certs/origin.pem
param tls/origin-key > certs/origin.key

secret_key=$(param secret-key)
db_password=$(param db-password)
db_root_password=$(param db-root-password)

write_env() {
  cat > .env <<ENV
APP_IMAGE=$1
AWS_REGION=$REGION
IMAGE_BUCKET=$BUCKET
SECRET_KEY=$secret_key
DB_PASSWORD=$db_password
DB_ROOT_PASSWORD=$db_root_password
ENV
}

previous=$(cat current_image 2>/dev/null || true)

write_env "$IMAGE"
if docker compose up -d --remove-orphans --wait --wait-timeout 300; then
  echo "$IMAGE" > current_image
  echo "Deployed $IMAGE"
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
