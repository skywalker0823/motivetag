"""Hand the server's AWS credentials to the app container, the way EC2's IMDS did.

On the Raspberry Pi there is no instance role. The SSM agent (hybrid activation) keeps
short-lived credentials for the motivetag-app role in root's shared credentials file
and renews them on its own. The app holds long-lived boto3 clients, which cannot
re-read that file, so this relay answers the instance-metadata (IMDSv2) calls botocore
already knows; the app points at it with AWS_EC2_METADATA_SERVICE_ENDPOINT and its
credentials refresh as they did on EC2.

It runs as its own container on the internal compose network (no published port). Like
IMDSv2 it hands out credentials only after a PUT for a token, so a GET forged through
the app (SSRF) gets nothing.
"""

import configparser
import json
import os
import secrets
import time
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CREDENTIALS_FILE = os.environ.get("CREDENTIALS_FILE", "/aws/credentials")
PROFILE = os.environ.get("CREDENTIALS_PROFILE", "default")
ROLE = "motivetag-app"
# The agent renews well before its credentials expire; claiming a short life makes
# botocore ask again soon, so it picks up each renewal.
LIFETIME = timedelta(minutes=20)
TOKEN_TTL_MAX = 21600

tokens = {}  # token -> expiry (monotonic seconds)


def read_credentials():
    parser = configparser.ConfigParser()
    if not parser.read(CREDENTIALS_FILE):
        raise FileNotFoundError(CREDENTIALS_FILE)
    section = parser[PROFILE]
    return {
        "Code": "Success",
        "LastUpdated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Type": "AWS-HMAC",
        "AccessKeyId": section["aws_access_key_id"],
        "SecretAccessKey": section["aws_secret_access_key"],
        "Token": section.get("aws_session_token", ""),
        "Expiration": (datetime.now(UTC) + LIFETIME).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def valid_token(token):
    expiry = tokens.get(token or "")
    return expiry is not None and expiry > time.monotonic()


class Handler(BaseHTTPRequestHandler):
    server_version = "relay"
    sys_version = ""

    def reply(self, status, body=b"", content_type="text/plain"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_PUT(self):  # noqa: N802 - http.server's naming
        if self.path != "/latest/api/token":
            return self.reply(404)
        try:
            ttl = int(self.headers.get("X-aws-ec2-metadata-token-ttl-seconds", ""))
        except ValueError:
            return self.reply(400)
        if not 0 < ttl <= TOKEN_TTL_MAX:
            return self.reply(400)
        now = time.monotonic()
        for old in [t for t, expiry in tokens.items() if expiry <= now]:
            del tokens[old]
        token = secrets.token_urlsafe(32)
        tokens[token] = now + ttl
        self.reply(200, token.encode())

    def do_GET(self):  # noqa: N802
        if not valid_token(self.headers.get("X-aws-ec2-metadata-token")):
            return self.reply(401)
        base = "/latest/meta-data/iam/security-credentials/"
        if self.path == base:
            return self.reply(200, ROLE.encode())
        if self.path == base + ROLE:
            try:
                body = json.dumps(read_credentials()).encode()
            except (OSError, KeyError) as error:
                self.log_message("cannot read credentials: %s", error)
                return self.reply(503)
            return self.reply(200, body, "application/json")
        self.reply(404)

    def log_message(self, fmt, *args):
        # Paths only; credentials and tokens never reach the log.
        print(fmt % args, flush=True)


if __name__ == "__main__":
    # All interfaces of its own container; only the compose network can reach it.
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()  # noqa: S104
