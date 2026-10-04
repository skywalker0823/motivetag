"""Turning phone and computer notifications on and off (module/push.py, ADR 0016).

The browser asks GET /push/key for the server's public key, subscribes with its own
push service, then hands the subscription over here.
"""

from flask import current_app, request, session

from data.data import PushSubscription
from module import push
from module.clock import taipei_datetime

from . import error, login_required, v1


@v1.route("/push/key", methods=["GET"])
@login_required
def push_key():
    if not push.enabled():
        return error("push_off", "目前尚未開放通知", 404)
    return {"data": {"key": current_app.config["VAPID_PUBLIC_KEY"]}}


def _endpoint(body):
    endpoint = body.get("endpoint")
    if not isinstance(endpoint, str) or not endpoint.startswith("https://") or len(endpoint) > 500:
        return None
    return endpoint


@v1.route("/push/subscriptions", methods=["POST"])
@login_required
def subscribe():
    """{endpoint, keys: {p256dh, auth}}, as PushSubscription.toJSON() gives it."""
    if not push.enabled():
        return error("push_off", "目前尚未開放通知", 404)
    body = request.get_json(silent=True) or {}
    endpoint = _endpoint(body)
    keys = body.get("keys") if isinstance(body.get("keys"), dict) else {}
    p256dh, auth = keys.get("p256dh"), keys.get("auth")
    if (
        not endpoint
        or not isinstance(p256dh, str)
        or not isinstance(auth, str)
        or not 0 < len(p256dh) <= 200
        or not 0 < len(auth) <= 100
    ):
        return error("bad_subscription", "通知設定無效", 400)
    PushSubscription.save(session["member_id"], endpoint, p256dh, auth, taipei_datetime())
    return {"data": {"subscribed": True}}, 201


@v1.route("/push/subscriptions", methods=["DELETE"])
@login_required
def unsubscribe():
    endpoint = _endpoint(request.get_json(silent=True) or {})
    if not endpoint:
        return error("bad_subscription", "通知設定無效", 400)
    PushSubscription.remove(endpoint, session["member_id"])
    return {"data": {"subscribed": False}}
