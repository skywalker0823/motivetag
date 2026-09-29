"""Blocking members and reporting content (ADR 0014)."""

import pytest


def befriend(query, a_id, b_id):
    query(
        "INSERT INTO friendship (request_from, request_to, status) VALUES (%s, %s, '0')",
        a_id,
        b_id,
    )


def post(client, content="hello #safetytest", kind="PUBLIC"):
    result = client.post("/api/blocks", json={"type": kind, "content": content})
    return result.get_json()["data"][0]["block_id"]


def explore_ids(client):
    return {p["block_id"] for p in client.get("/api/v1/posts/explore").get_json()["data"]}


def comment(client, block_id, text="nice"):
    result = client.post("/api/message", json={"block_id": block_id, "message": text, "score": 0})
    return result.get_json()["comment"]["comment_id"]


# ---------- Blocking ----------


def test_blocking_hides_their_posts_and_comments_from_me(member):
    alice, _, _ = member()
    bob, _, bob_account = member()
    theirs = post(bob)
    mine = post(alice)
    comment(bob, mine, "from bob")
    assert theirs in explore_ids(alice)

    assert alice.put(f"/api/v1/blocks/{bob_account}").status_code == 200
    assert theirs not in explore_ids(alice)
    comments = alice.get(f"/api/message?block_id={mine}").get_json()["ok"]
    assert all(c["account"] != bob_account for c in comments)
    # They still see mine: blocking hides them from me, it is not announced to them.
    assert mine in explore_ids(bob)

    assert alice.get("/api/v1/blocks").get_json()["data"][0]["account"] == bob_account
    assert alice.delete(f"/api/v1/blocks/{bob_account}").status_code == 200
    assert theirs in explore_ids(alice)


def test_blocking_ends_friendship_and_stops_chat_and_invites(member, query):
    alice, alice_id, alice_account = member()
    bob, bob_id, bob_account = member()
    befriend(query, alice_id, bob_id)
    alice.put(f"/api/v1/blocks/{bob_account}")

    assert not query(
        "SELECT 1 FROM friendship WHERE request_from=%s AND request_to=%s", alice_id, bob_id
    )
    sent = bob.post(f"/api/v1/chats/{alice_account}/messages", json={"content": "hi"})
    assert sent.status_code == 403 and sent.get_json()["error"]["code"] == "blocked"
    assert bob.post("/api/friend", json={"who": alice_account}).get_json()["error"] == "blocked"
    assert alice.post("/api/friend", json={"who": bob_account}).get_json()["error"] == "blocked"
    history = alice.get(f"/api/v1/chats/{bob_account}/messages").get_json()
    assert history["can_send"] is False and history["blocked"] is True


def test_blocked_member_cannot_notify_me(member, query):
    alice, alice_id, _ = member()
    bob, _, bob_account = member()
    _, carol_id, _ = member()
    alice.put(f"/api/v1/blocks/{bob_account}")
    alice_account = query("SELECT account FROM member WHERE member_id=%s", alice_id)[0]["account"]
    bob.post("/api/notifi", json={"who": alice_account, "type": "friend_invite"})
    assert alice.get("/api/notifi").get_json()["data"] == []
    assert carol_id  # a third member is unaffected (nothing to check beyond not crashing)


def test_blocked_members_are_not_suggested(member):
    alice, _, _ = member()
    bob, _, bob_account = member()
    for client in (alice, bob):
        client.patch("/api/member_tags", json={"tag": "blocksuggest"})
    assert bob_account in [
        m["account"] for m in alice.get("/api/v1/members/suggested").get_json()["data"]
    ]
    bob.put(f"/api/v1/blocks/{alice.get('/api/member').get_json()['data']['account']}")
    assert bob_account not in [
        m["account"] for m in alice.get("/api/v1/members/suggested").get_json()["data"]
    ]


def test_cannot_block_myself_or_nobody(member):
    alice, _, alice_account = member()
    assert alice.put(f"/api/v1/blocks/{alice_account}").status_code == 400
    assert alice.put("/api/v1/blocks/nobody-at-all").status_code == 404


# ---------- Reporting ----------


def report(client, kind, target_id, reason="spam", **extra):
    return client.post(
        "/api/v1/reports", json={"type": kind, "id": target_id, "reason": reason, **extra}
    )


def test_reported_post_leaves_my_view_only(member):
    alice, _, _ = member()
    bob, _, _ = member()
    carol, _, _ = member()
    theirs = post(bob)
    result = report(alice, "post", theirs, detail="buy my stuff")
    assert result.status_code == 201 and result.get_json()["data"]["hidden"] is False
    assert theirs not in explore_ids(alice)
    assert theirs in explore_ids(carol)
    again = report(alice, "post", theirs)
    assert again.status_code == 409 and again.get_json()["error"]["code"] == "already_reported"


def test_three_reports_hide_a_post_until_reviewed(member, query):
    bob, _, _ = member()
    theirs = post(bob)
    for _ in range(3):
        reporter, _, _ = member()
        report(reporter, "post", theirs)
    onlooker, _, _ = member()
    assert query("SELECT hidden FROM block WHERE block_id=%s", theirs)[0]["hidden"] == 1
    assert theirs not in explore_ids(onlooker)
    assert theirs in explore_ids(bob)  # the author still sees it


def test_trusted_members_reports_count_double(member, query):
    bob, _, _ = member()
    theirs = post(bob)
    trusted, trusted_id, _ = member()
    query("UPDATE member SET exp=4050 WHERE member_id=%s", trusted_id)  # Lv 10
    assert report(trusted, "post", theirs).get_json()["data"]["hidden"] is False
    other, _, _ = member()
    assert report(other, "post", theirs).get_json()["data"]["hidden"] is True


def test_reporting_comments_messages_and_members(member, query):
    alice, alice_id, alice_account = member()
    bob, bob_id, bob_account = member()
    befriend(query, alice_id, bob_id)
    mine = post(alice)
    bobs_comment = comment(bob, mine, "rude")
    assert report(alice, "comment", bobs_comment, reason="harassment").status_code == 201
    comments = alice.get(f"/api/message?block_id={mine}").get_json()["ok"]
    assert bobs_comment not in [c["comment_id"] for c in comments]

    message = bob.post(f"/api/v1/chats/{alice_account}/messages", json={"content": "scam link"})
    message_id = message.get_json()["data"]["id"]
    # Only the recipient can report a message.
    assert report(bob, "message", message_id).status_code in (400, 404)
    assert report(alice, "message", message_id, reason="scam").status_code == 201

    assert report(alice, "member", bob_id, reason="harassment").status_code == 201
    assert report(alice, "member", alice_id).status_code == 400
    snapshot = query(
        "SELECT snapshot FROM report WHERE target_type='message' AND target_id=%s", message_id
    )[0]["snapshot"]
    assert snapshot == "scam link"
    assert bob_account


def test_bad_reports_are_refused(member):
    alice, _, _ = member()
    bob, _, _ = member()
    theirs = post(bob)
    assert report(alice, "post", theirs, reason="because").status_code == 400
    assert report(alice, "thing", theirs).status_code == 400
    assert report(alice, "post", 10**9).status_code == 404
    assert report(alice, "post", theirs, detail="x" * 501).status_code == 400
    own = post(alice)
    assert report(alice, "post", own).status_code == 400
    secret = post(bob, kind="SECRET")
    assert report(alice, "post", secret).status_code == 404


def test_reports_per_day_are_limited(member, monkeypatch):
    monkeypatch.setattr("api.v1.reports.PER_DAY", 1)
    alice, _, _ = member()
    bob, _, _ = member()
    first, second = post(bob), post(bob)
    assert report(alice, "post", first).status_code == 201
    assert report(alice, "post", second).status_code == 429


# ---------- Reviewing ----------


@pytest.fixture()
def admin(app, member, monkeypatch):
    client, _, account = member()
    monkeypatch.setitem(app.config, "ADMIN_ACCOUNTS", frozenset({account}))
    return client, account


def test_admin_pages_are_hidden_from_everyone_else(member, admin):
    alice, _, _ = member()
    assert alice.get("/admin").status_code == 404
    assert alice.get("/api/v1/admin/reports").status_code == 404
    client, _ = admin
    assert client.get("/admin").status_code == 200
    assert client.get("/api/v1/admin/reports").status_code == 200


def test_admin_removes_or_keeps_reported_content(member, admin, query):
    client, admin_account = admin
    bob, _, _ = member()
    bad, fine = post(bob, "bad post"), post(bob, "fine post")
    for _ in range(3):
        reporter, _, _ = member()
        report(reporter, "post", bad)
        report(reporter, "post", fine)
    # Admins hear about it through the bell.
    assert client.get("/api/notifi").get_json()["data"]

    groups = client.get("/api/v1/admin/reports").get_json()["data"]
    mine = {g["id"]: g for g in groups if g["type"] == "post" and g["id"] in (bad, fine)}
    assert mine[bad]["snapshot"] == "bad post" and mine[bad]["hidden"] is True
    assert len(mine[bad]["reports"]) == 3 and mine[bad]["weight"] == 3

    removed = client.post(f"/api/v1/admin/reports/post/{bad}", json={"action": "remove"})
    assert removed.get_json()["data"] == {"closed": 3, "removed": True}
    assert not query("SELECT 1 FROM block WHERE block_id=%s", bad)

    kept = client.post(f"/api/v1/admin/reports/post/{fine}", json={"action": "dismiss"})
    assert kept.get_json()["data"]["closed"] == 3
    assert query("SELECT hidden FROM block WHERE block_id=%s", fine)[0]["hidden"] == 0
    open_ids = [g["id"] for g in client.get("/api/v1/admin/reports").get_json()["data"]]
    assert bad not in open_ids and fine not in open_ids
    closed = client.get("/api/v1/admin/reports?status=dismissed").get_json()["data"]
    assert fine in [g["id"] for g in closed]
    assert admin_account
