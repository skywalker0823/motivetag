"""Web Push (module/push.py, api/v1/push.py) and the PWA files."""

import pytest
from pywebpush import WebPushException

from api import socketio
from module import push

# A real P-256 pair, made with the commands in infra/README.md, used only in tests.
PUBLIC = "BEIo38ndglY-5Sy7gArn75jDzsddnR38u3tmshDLOyhUV1Hflms4ZF9nBqdBmXktrC8rTK2uYWaOgB-wZIH1nv4"
PRIVATE = "0_WjKHegTcir4c46oILT6ovf1Wlg3qSm1-5FduDwExo"
SUBSCRIPTION = {
    "endpoint": "https://push.example.com/send/abc",
    "keys": {
        "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlUls0VJXg7A8u-Ts1XbjhazAkj7I99e8QcYP7DkM",
        "auth": "tBHItJI5svbpez7KI4CCXg",
    },
}


@pytest.fixture()
def push_on(app, monkeypatch):
    monkeypatch.setitem(app.config, "VAPID_PUBLIC_KEY", PUBLIC)
    monkeypatch.setitem(app.config, "VAPID_PRIVATE_KEY", PRIVATE)
    # Deliver at once instead of in a background greenlet.
    monkeypatch.setattr(socketio, "start_background_task", lambda fn, *args: fn(*args))
    sent = []
    monkeypatch.setattr(push, "webpush", lambda info, data, **kw: sent.append((info, data, kw)))
    return sent


def befriend(query, a_id, b_id):
    query(
        "INSERT INTO friendship (request_from, request_to, status) VALUES (%s, %s, '0')",
        a_id,
        b_id,
    )


def test_off_without_keys(member):
    alice, _, _ = member()
    assert alice.get("/api/v1/push/key").status_code == 404
    assert alice.post("/api/v1/push/subscriptions", json=SUBSCRIPTION).status_code == 404


def test_subscribe_and_unsubscribe(member, push_on, query):
    alice, alice_id, _ = member()
    assert alice.get("/api/v1/push/key").get_json()["data"]["key"] == PUBLIC
    assert alice.post("/api/v1/push/subscriptions", json=SUBSCRIPTION).status_code == 201
    rows = query(
        "SELECT member_id FROM push_subscription WHERE endpoint=%s", SUBSCRIPTION["endpoint"]
    )
    assert rows == [{"member_id": alice_id}]
    bad = {"endpoint": "http://insecure.example.com", "keys": SUBSCRIPTION["keys"]}
    assert alice.post("/api/v1/push/subscriptions", json=bad).status_code == 400
    gone = alice.delete("/api/v1/push/subscriptions", json={"endpoint": SUBSCRIPTION["endpoint"]})
    assert gone.status_code == 200
    assert not query("SELECT 1 FROM push_subscription WHERE endpoint=%s", SUBSCRIPTION["endpoint"])


def test_offline_friend_gets_a_push_for_a_message(member, push_on, query, socket_client):
    alice, alice_id, alice_account = member()
    bob, bob_id, bob_account = member()
    befriend(query, alice_id, bob_id)
    bob.post("/api/v1/push/subscriptions", json=SUBSCRIPTION)
    alice.post(f"/api/v1/chats/{bob_account}/messages", json={"content": "在嗎？"})
    assert len(push_on) == 1
    info, data, kw = push_on[0]
    assert info["endpoint"] == SUBSCRIPTION["endpoint"]
    assert '"title": "%s"' % alice_account in data and "在嗎？" in data
    assert f"?chat={alice_account}" in data
    assert kw["vapid_claims"]["sub"].startswith("http")
    # With the site open, the tab shows it; no push.
    socket_client(bob)
    alice.post(f"/api/v1/chats/{bob_account}/messages", json={"content": "again"})
    assert len(push_on) == 1


def test_notifications_are_pushed_too(member, push_on):
    alice, _, _ = member()
    bob, _, bob_account = member()
    bob.post("/api/v1/push/subscriptions", json=SUBSCRIPTION)
    alice.post("/api/notifi", json={"who": bob_account, "type": "friend_invite"})
    assert len(push_on) == 1 and "想加你為好友" in push_on[0][1]


def test_a_gone_subscription_is_forgotten(member, push_on, query, monkeypatch):
    alice, _, _ = member()
    bob, _, bob_account = member()
    bob.post("/api/v1/push/subscriptions", json=SUBSCRIPTION)

    class Gone:
        status_code = 410

    def refuse(*args, **kwargs):
        raise WebPushException("gone", response=Gone())

    monkeypatch.setattr(push, "webpush", refuse)
    alice.post("/api/notifi", json={"who": bob_account, "type": "friend_invite"})
    assert not query("SELECT 1 FROM push_subscription WHERE endpoint=%s", SUBSCRIPTION["endpoint"])


def test_pwa_files(client):
    worker = client.get("/sw.js")
    assert worker.status_code == 200 and worker.headers["Cache-Control"] == "no-cache"
    assert b"showNotification" in worker.data
    manifest = client.get("/manifest.webmanifest")
    assert manifest.status_code == 200
    assert manifest.headers["Content-Type"].startswith("application/manifest+json")
    assert manifest.get_json()["display"] == "standalone"
