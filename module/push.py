"""Web Push notifications (ADR 0016): new chat messages and notifications reach a
member's phone or computer while the site is closed.

Off unless /motivetag/vapid-public-key and -private-key exist (infra/README.md,
"Phone notifications"). Pushes go only to members with no open tab, since an open
tab already shows the message. Sending happens in a background greenlet, so the
request that caused it does not wait for Google's or Apple's push servers.
"""

import json

from flask import current_app
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from data.data import PushSubscription
from module.urls import public_base_url

TTL = 24 * 3600  # a push not delivered within a day is dropped by the push service


def enabled():
    config = current_app.config
    return bool(config["VAPID_PUBLIC_KEY"] and config["VAPID_PRIVATE_KEY"])


def _vapid():
    # The raw 32-byte key, base64url (from_raw decodes it itself).
    return Vapid.from_raw(current_app.config["VAPID_PRIVATE_KEY"].encode())


def _deliver(app, subscriptions, payload, claims):
    with app.app_context():
        vapid = _vapid()
        for sub in subscriptions:
            info = {
                "endpoint": sub["endpoint"],
                "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
            }
            try:
                webpush(
                    info,
                    payload,
                    vapid_private_key=vapid,
                    vapid_claims=dict(claims),  # webpush adds "aud" and "exp" to it
                    ttl=TTL,
                    timeout=5,
                )
            except WebPushException as exc:
                status = exc.response.status_code if exc.response is not None else None
                if status in (404, 410):  # the browser unsubscribed or the app was removed
                    PushSubscription.remove(sub["endpoint"])
                else:
                    app.logger.warning("push failed (%s): %s", status, exc)
            except Exception as exc:  # noqa: BLE001 - a push must never break the request
                app.logger.warning("push failed: %s", exc)


def notify(member_id, account, title, body, url="/"):
    """Pushes {title, body, url} to every device of `member_id`, unless they have the
    site open (`account` is checked against the members online)."""
    if not enabled():
        return
    from api import socketio  # the app package imports this module's users
    from api.blueprints.api_chat import online

    if account in online:
        return
    subscriptions = PushSubscription.for_member(member_id)
    if not subscriptions:
        return
    payload = json.dumps({"title": title, "body": body[:200], "url": url}, ensure_ascii=False)
    claims = {"sub": public_base_url()}
    app = current_app._get_current_object()
    socketio.start_background_task(_deliver, app, subscriptions, payload, claims)
