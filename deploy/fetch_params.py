"""Write the deploy's secrets from Parameter Store into /out (run inside the app image).

deploy.sh runs this as root with the server's app directory mounted at /out. It uses the
instance role through IMDS, so the host's own AWS CLI is not involved.
"""

import os
import sys

import boto3

NAMES = {
    "secret-key": "SECRET_KEY",
    "db-password": "DB_PASSWORD",
    "db-root-password": "DB_ROOT_PASSWORD",
    "tls/origin-cert": None,
    "tls/origin-key": None,
}
# Written empty when missing, so a deploy works before they are set up.
OPTIONAL = {
    "backup-bucket": "BACKUP_BUCKET",  # created by infra/main/backup.tf
    "alert-topic-arn": "ALERT_TOPIC_ARN",  # created by infra/main/monitoring.tf
    "sentry-dsn": "SENTRY_DSN",  # added by hand, see infra/README.md
    "email-from": "EMAIL_FROM",  # created by infra/main/ses.tf
    "ses-region": "SES_REGION",  # created by infra/main/ses.tf
    "turnstile-site-key": "TURNSTILE_SITE_KEY",  # added by hand, see infra/README.md
    "turnstile-secret": "TURNSTILE_SECRET",  # added by hand, see infra/README.md
    "grafana-prom-url": "GRAFANA_PROM_URL",  # added by hand, see infra/README.md
    "grafana-prom-user": "GRAFANA_PROM_USER",  # added by hand, see infra/README.md
    "grafana-cloud-token": "GRAFANA_CLOUD_TOKEN",  # added by hand, see infra/README.md
    "admin-accounts": "ADMIN_ACCOUNTS",  # added by hand, see infra/README.md
    "contact-email": "CONTACT_EMAIL",  # added by hand, see infra/README.md
    "vapid-public-key": "VAPID_PUBLIC_KEY",  # added by hand, see infra/README.md
    "vapid-private-key": "VAPID_PRIVATE_KEY",  # added by hand, see infra/README.md
    "apod-copyrighted-images": "APOD_COPYRIGHTED_IMAGES",  # added by hand, see infra/README.md
}


BATCH = 10  # GetParameters takes at most 10 names per call


def get_parameters(ssm, names):
    """All of `names` in batches; returns (found parameters, names that do not exist)."""
    found, invalid = [], []
    for start in range(0, len(names), BATCH):
        response = ssm.get_parameters(Names=names[start : start + BATCH], WithDecryption=True)
        found += response["Parameters"]
        invalid += response["InvalidParameters"]
    return found, invalid


def main():
    ssm = boto3.client("ssm", region_name=os.environ["AWS_REGION"])
    names = [f"/motivetag/{n}" for n in {**NAMES, **OPTIONAL}]
    found, invalid = get_parameters(ssm, names)
    missing = [n for n in invalid if n.removeprefix("/motivetag/") not in OPTIONAL]
    if missing:
        sys.exit("missing parameters: " + ", ".join(missing))
    values = {p["Name"].removeprefix("/motivetag/"): p["Value"] for p in found}
    for name, value in values.items():
        if not value.strip():
            sys.exit(f"/motivetag/{name} is empty")

    os.umask(0o077)
    os.makedirs("/out/certs", exist_ok=True)
    with open("/out/certs/origin.pem.new", "w") as f:
        f.write(values["tls/origin-cert"].strip() + "\n")
    with open("/out/certs/origin.key.new", "w") as f:
        f.write(values["tls/origin-key"].strip() + "\n")
    with open("/out/params.env", "w") as f:
        for name, env in NAMES.items():
            if env:
                f.write(f"{env}={values[name]}\n")
        for name, env in OPTIONAL.items():
            f.write(f"{env}={values.get(name, '').strip()}\n")


if __name__ == "__main__":
    main()
