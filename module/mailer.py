"""Sending e-mail through Amazon SES (infra/main/ses.tf).

On only when EMAIL_FROM (a bare address; the display name is added here, because
deploy.sh reads the value as shell) is set; SES_REGION says where the verified domain lives (SES
is not offered in every region). Without EMAIL_FROM, messages are logged instead of
sent, which is what local development wants.
"""

import boto3
from flask import current_app


def enabled():
    return bool(current_app.config.get("EMAIL_FROM")) and not current_app.config.get(
        "MAIL_SUPPRESS"
    )


def send(to, subject, text, html):
    """Returns True when SES took the message."""
    if not enabled():
        current_app.logger.warning("e-mail to %s not sent (mail is off): %s\n%s", to, subject, text)
        return False
    client = boto3.client("sesv2", region_name=current_app.config["SES_REGION"])
    client.send_email(
        FromEmailAddress=f"MotiveTag <{current_app.config['EMAIL_FROM']}>",
        Destination={"ToAddresses": [to]},
        Content={
            "Simple": {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": text, "Charset": "UTF-8"},
                    "Html": {"Data": html, "Charset": "UTF-8"},
                },
            }
        },
    )
    return True
