"""Suspending accounts from /admin (module/suspension.py, api/v1/admin.py)."""

import pytest

from module import suspension


@pytest.fixture()
def admin(app, member, monkeypatch):
    client, _, account = member()
    monkeypatch.setitem(app.config, "ADMIN_ACCOUNTS", frozenset({account}))
    return client, account


def sign_in(app, account):
    client = app.test_client()
    result = client.put("/api/member", json={"account": account, "password": account + "-pw"})
    return client, result.get_json()


def test_only_admins_suspend(member):
    alice, _, _ = member()
    _, _, bob_account = member()
    assert (
        alice.put(f"/api/v1/admin/members/{bob_account}/suspension", json={"days": 7}).status_code
        == 404
    )
    assert alice.get("/api/v1/admin/suspensions").status_code == 404


def test_suspended_member_is_signed_out_and_cannot_sign_in(app, member, admin, query):
    client, _ = admin
    bob, bob_id, bob_account = member()
    assert bob.get("/api/v1/me/profile").status_code != 401

    result = client.put(
        f"/api/v1/admin/members/{bob_account}/suspension", json={"days": 7, "reason": "洗版"}
    )
    assert result.status_code == 200
    assert result.get_json()["data"]["until"] is not None
    assert (
        query("SELECT suspended_reason FROM member WHERE member_id=%s", bob_id)[0][
            "suspended_reason"
        ]
        == "洗版"
    )

    # The open session ends on its next request: API calls get 401, pages go to /.
    ended = bob.get("/api/v1/me/profile")
    assert ended.status_code == 401
    assert ended.get_json()["error"]["code"] == "suspended"
    assert bob.get(f"/{bob_account}").status_code == 302

    _, answer = sign_in(app, bob_account)
    assert "停權" in answer["error"]["msg"] and "洗版" in answer["error"]["msg"]

    listed = client.get("/api/v1/admin/suspensions").get_json()["data"]
    assert [row["account"] for row in listed if row["account"] == bob_account] == [bob_account]

    assert client.delete(f"/api/v1/admin/members/{bob_account}/suspension").status_code == 200
    _, answer = sign_in(app, bob_account)
    assert answer.get("ok"), answer


def test_permanent_suspension_and_bad_input(app, member, admin):
    client, admin_account = admin
    _, _, bob_account = member()
    url = f"/api/v1/admin/members/{bob_account}/suspension"
    assert client.put(url, json={"days": 2}).status_code == 400
    assert client.put(url, json={"days": True}).status_code == 400
    assert client.put(url, json={}).status_code == 400
    assert client.put(url, json={"days": 7, "reason": "x" * 201}).status_code == 400
    assert (
        client.put("/api/v1/admin/members/nobody-here/suspension", json={"days": 7}).status_code
        == 404
    )
    assert (
        client.put(
            f"/api/v1/admin/members/{admin_account}/suspension", json={"days": 7}
        ).status_code
        == 400
    )

    forever = client.put(url, json={"days": None})
    assert forever.status_code == 200 and forever.get_json()["data"]["until"] is None
    _, answer = sign_in(app, bob_account)
    assert "永久停權" in answer["error"]["msg"]


def test_expired_suspension_lets_them_back(app, member, query):
    _, bob_id, bob_account = member()
    query("UPDATE member SET suspended_until='2020-01-01 00:00:00' WHERE member_id=%s", bob_id)
    suspension._cache.pop(bob_id, None)
    _, answer = sign_in(app, bob_account)
    assert answer.get("ok"), answer


def test_suspending_resolves_reports_and_shows_on_cards(member, admin):
    client, _ = admin
    bob, bob_id, bob_account = member()
    reporter, _, _ = member()
    reporter.post("/api/v1/reports", json={"type": "member", "id": bob_id, "reason": "spam"})
    group = next(
        g
        for g in client.get("/api/v1/admin/reports").get_json()["data"]
        if g["type"] == "member" and g["id"] == bob_id
    )
    assert group["author"]["suspended"] is False

    done = client.put(f"/api/v1/admin/members/{bob_account}/suspension", json={"days": 1})
    assert done.get_json()["data"]["closed"] == 1
    resolved = client.get("/api/v1/admin/reports?status=resolved").get_json()["data"]
    group = next(g for g in resolved if g["type"] == "member" and g["id"] == bob_id)
    assert group["author"]["suspended"] is True


def test_suspension_closes_sockets(member, admin, socket_client, chat_state):
    client, _ = admin
    bob, _, bob_account = member()
    socket = socket_client(bob)
    assert socket.is_connected()

    client.put(f"/api/v1/admin/members/{bob_account}/suspension", json={"days": 1})
    assert not socket.is_connected()
    assert bob_account not in chat_state.online
