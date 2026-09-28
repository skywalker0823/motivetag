"""Cloudflare Turnstile: a free check that sign-ups come from a person, not a script.

On only when both TURNSTILE_SITE_KEY (the page shows the widget) and TURNSTILE_SECRET
(the server checks its answer) are set, from Parameter Store /motivetag/turnstile-*.
With only one of them a check could never pass, so both are needed; without them
every sign-up passes, as in local development.
"""

import json
import urllib.parse
import urllib.request

from flask import current_app

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def enabled():
    config = current_app.config
    return bool(config.get("TURNSTILE_SITE_KEY") and config.get("TURNSTILE_SECRET"))


def passed(token, remote_ip=None):
    """Whether Cloudflare accepts the widget's token. Fails closed if it cannot be asked."""
    if not enabled():
        return True
    if not token or not isinstance(token, str):
        return False
    form = {"secret": current_app.config["TURNSTILE_SECRET"], "response": token}
    if remote_ip:
        form["remoteip"] = remote_ip
    request = urllib.request.Request(VERIFY_URL, data=urllib.parse.urlencode(form).encode())
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310 - fixed https URL
            return bool(json.load(response).get("success"))
    except (OSError, ValueError) as exc:
        current_app.logger.warning("Turnstile check failed: %s", exc)
        return False
