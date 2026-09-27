"""S3 and SNS calls for backup.sh and restore_drill.sh (run inside the app image).

    backup_s3.py upload <bucket> <file>        store a dump under mysql/ in the bucket
    backup_s3.py latest <bucket> <dir>         download the newest dump; prints "<path> <age-hours>"
    backup_s3.py alert <topic-arn> <subject>    e-mail stdin through the SNS alerts topic

Uses the instance role through IMDS, like fetch_params.py.
"""

import os
import sys
from datetime import UTC, datetime

import boto3

PREFIX = "mysql/"


def upload(bucket, path):
    s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
    key = PREFIX + os.path.basename(path)
    s3.upload_file(path, bucket, key, ExtraArgs={"ContentType": "application/gzip"})
    print(f"uploaded s3://{bucket}/{key} ({os.path.getsize(path)} bytes)")


def latest(bucket, directory):
    s3 = boto3.client("s3", region_name=os.environ["AWS_REGION"])
    newest = None
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=PREFIX):
        for obj in page.get("Contents", []):
            if newest is None or obj["LastModified"] > newest["LastModified"]:
                newest = obj
    if newest is None:
        sys.exit(f"no backups under s3://{bucket}/{PREFIX}")
    path = os.path.join(directory, os.path.basename(newest["Key"]))
    s3.download_file(bucket, newest["Key"], path)
    age_hours = (datetime.now(UTC) - newest["LastModified"]).total_seconds() / 3600
    print(f"{path} {age_hours:.1f}")


def alert(topic_arn, subject):
    sns = boto3.client("sns", region_name=os.environ["AWS_REGION"])
    sns.publish(TopicArn=topic_arn, Subject=subject[:100], Message=sys.stdin.read() or subject)


COMMANDS = {"upload": upload, "latest": latest, "alert": alert}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        sys.exit(__doc__)
    COMMANDS[sys.argv[1]](*sys.argv[2:])
