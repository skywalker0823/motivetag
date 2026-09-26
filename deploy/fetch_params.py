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
    "sentry-dsn": "SENTRY_DSN",  # added by hand, see infra/README.md
}


def main():
    ssm = boto3.client("ssm", region_name=os.environ["AWS_REGION"])
    names = [f"/motivetag/{n}" for n in {**NAMES, **OPTIONAL}]
    response = ssm.get_parameters(Names=names, WithDecryption=True)
    missing = [
        n for n in response["InvalidParameters"] if n.removeprefix("/motivetag/") not in OPTIONAL
    ]
    if missing:
        sys.exit("missing parameters: " + ", ".join(missing))
    values = {p["Name"].removeprefix("/motivetag/"): p["Value"] for p in response["Parameters"]}
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
