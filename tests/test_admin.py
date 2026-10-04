"""The /admin tools beyond reports (api/v1/admin.py) and sign-in protection."""

import pytest

from module import levels, lockout

ADMIN_ONLY = [
    ("get", "/api/v1/admin/stats"),
    ("get", "/api/v1/admin/members"),
    ("get", "/api/v1/admin/logs"),
    ("put", "/api/v1/admin/members/someone/level"),
    ("post", "/api/v1/admin/members/someone/verify"),
    ("post", "/api/v1/admin/members/someone/notice"),
    ("post", "/api/v1/admin/announcements"),
]


@pytest.fixture()
def admin(app, member, monkeypatch):
    client, admin_id, account = member()
    monkeypatch.setitem(app.config, "ADMIN_ACCOUNTS", frozenset({account}))
    return client, account


@pytest.mark.parametrize(("method", "url"), ADMIN_ONLY)
def test_everyone_else_gets_404(client, member, method, url):
    alice, _, _ = member()
    for who in (client, alice):
        assert getattr(who, method)(url, json={}).status_code == 404


def test_stats(admin, member):
    client, _ = admin
    bob, _, _ = member()
    bob.post("/api/blocks", json={"type": "PUBLIC", "content": "stats #admintest"})
    data = client.get("/api/v1/admin/stats").get_json()["data"]
    assert data["members"]["members"] >= 2 and data["members"]["new_today"] >= 2
    assert data["posts"]["today"] >= 1
    assert len(data["daily"]) == 14 and data["daily"][-1]["posts"] >= 1
    assert "open_reports" in data and "online" in data


def test_member_lookup_and_level(admin, member, query, socket_client):
    client, admin_account = admin
    bob, bob_id, bob_account = member()
    found = client.get(f"/api/v1/admin/members?q={bob_account}").get_json()["data"]
    assert found[0]["account"] == bob_account and found[0]["level"] == 1
    assert found[0]["admin"] is False
    # Wildcards in the search are taken literally.
    assert client.get("/api/v1/admin/members?q=%25").get_json()["data"] == []

    socket = socket_client(bob)
    socket.get_received()
    result = client.put(f"/api/v1/admin/members/{bob_account}/level", json={"level": 5})
    assert result.get_json()["data"] == {
        "account": bob_account,
        "exp": levels.exp_for(5),
        "level": 5,
    }
    assert query("SELECT exp FROM member WHERE member_id=%s", bob_id)[0]["exp"] == 800
    pushed = [m["args"][0] for m in socket.get_received() if m["name"] == "exp"]
    assert pushed and pushed[0]["level"] == 5 and pushed[0]["level_up"] is True

    assert (
        client.put(f"/api/v1/admin/members/{bob_account}/level", json={"exp": 60}).status_code
        == 200
    )
    for bad in ({"level": 0}, {"level": 51}, {"level": True}, {"exp": -1}, {}):
        assert client.put(f"/api/v1/admin/members/{bob_account}/level", json=bad).status_code == 400
    assert client.put("/api/v1/admin/members/nobody-x/level", json={"level": 2}).status_code == 404

    log = client.get("/api/v1/admin/logs").get_json()["data"]
    assert log[0]["action"] == "level" and log[0]["admin"] == admin_account
    assert log[0]["target"] == bob_account


def test_verify_notice_and_announcement(admin, member, query):
    client, _ = admin
    bob, bob_id, bob_account = member()
    query("UPDATE member SET email_verified_at=NULL WHERE member_id=%s", bob_id)
    assert client.post(f"/api/v1/admin/members/{bob_account}/verify").status_code == 200
    assert query("SELECT email_verified_at FROM member WHERE member_id=%s", bob_id)[0][
        "email_verified_at"
    ]

    assert (
        client.post(f"/api/v1/admin/members/{bob_account}/notice", json={"message": ""}).status_code
        == 400
    )
    sent = client.post(
        f"/api/v1/admin/members/{bob_account}/notice", json={"message": "請注意用語"}
    )
    assert sent.status_code == 200
    notes = query("SELECT content FROM notifi WHERE reciever_id=%s", bob_id)
    assert any("請注意用語" in n["content"] for n in notes)

    result = client.post("/api/v1/admin/announcements", json={"message": "明晚維修"})
    assert result.get_json()["data"]["sent"] >= 1
    notes = query("SELECT content FROM notifi WHERE reciever_id=%s", bob_id)
    assert any("明晚維修" in n["content"] for n in notes)
    actions = [row["action"] for row in client.get("/api/v1/admin/logs").get_json()["data"][:3]]
    assert actions == ["announce", "notice", "verify"]


def test_admin_accounts_cannot_be_suspended_in_any_case(admin):
    client, admin_account = admin
    url = f"/api/v1/admin/members/{admin_account.upper()}/suspension"
    assert client.put(url, json={"days": 1}).status_code == 400


def test_free_admin_name_cannot_be_taken(app, client, monkeypatch):
    monkeypatch.setitem(app.config, "ADMIN_ACCOUNTS", frozenset({"Owner_Free"}))
    body = {
        "account": "owner_free",
        "password": "long-enough-pw",
        "email": "owner_free@example.com",
        "birthday": "1990-1-1",
    }
    assert client.post("/api/member", json=body).status_code == 400


def test_sign_in_locks_after_ten_wrong_passwords(app, member):
    _, _, account = member()
    client = app.test_client()
    try:
        for _ in range(lockout.MAX_FAILURES):
            wrong = client.put("/api/member", json={"account": account, "password": "nope"})
            assert wrong.get_json()["error"]["msg"] == "wrong account or password"
        locked = client.put("/api/member", json={"account": account, "password": account + "-pw"})
        assert locked.status_code == 429 and "分鐘後再試" in locked.get_json()["error"]["msg"]
    finally:
        lockout.succeeded(account)
    ok = client.put("/api/member", json={"account": account, "password": account + "-pw"})
    assert ok.get_json().get("ok")


def test_a_right_password_clears_the_count(app, member):
    _, _, account = member()
    client = app.test_client()
    for _ in range(lockout.MAX_FAILURES - 1):
        client.put("/api/member", json={"account": account, "password": "nope"})
    assert client.put(
        "/api/member", json={"account": account, "password": account + "-pw"}
    ).get_json()["ok"]
    for _ in range(lockout.MAX_FAILURES - 1):
        client.put("/api/member", json={"account": account, "password": "nope"})
    assert client.put(
        "/api/member", json={"account": account, "password": account + "-pw"}
    ).get_json()["ok"]


def test_member_page_links_admins_to_admin(admin, member):
    client, account = admin
    assert 'href="/admin"' in client.get(f"/{account}").get_data(as_text=True)
    alice, _, alice_account = member()
    assert 'href="/admin"' not in alice.get(f"/{alice_account}").get_data(as_text=True)
