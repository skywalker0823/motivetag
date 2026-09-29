"""Deleting an account (App Store Guideline 5.1.1(v))."""

from conftest import NOW


def test_deleting_needs_sign_in_and_the_password(client, member):
    assert client.delete("/api/v1/account", json={"password": "x"}).status_code == 401
    alice, _, account = member()
    wrong = alice.delete("/api/v1/account", json={"password": "wrong"})
    assert wrong.status_code == 403
    assert wrong.get_json() == {"error": {"code": "wrong_password", "message": "密碼不正確"}}
    assert alice.get("/api/member").get_json()["data"]["account"] == account


def test_deleting_removes_the_member_and_their_content(member, query):
    alice, alice_id, account = member()
    bob, bob_id, bob_account = member()
    own = alice.post(
        "/api/blocks", json={"type": "PUBLIC", "content": "mine #deltest", "vote_box": ["a", "b"]}
    ).get_json()["data"][0]
    bobs = bob.post("/api/blocks", json={"type": "PUBLIC", "content": "bob's", "vote_box": []})
    bobs = bobs.get_json()["data"][0]
    alice.post("/api/message", json={"block_id": bobs["block_id"], "message": "hi", "score": 1})
    alice.patch("/api/blocks", json={"block_id": bobs["block_id"]})
    bob.post("/api/message", json={"block_id": own["block_id"], "message": "yo", "score": 0})
    alice.post("/api/friend", json={"who": bob_account})
    query("UPDATE member SET exp=200 WHERE member_id=%s", alice_id)  # Lv 3 opens topics
    topic = alice.post(
        "/api/tag_page",
        json={"title": "topic", "content": "body", "classifi": "閒聊", "tag_name": "deltest"},
    )
    assert topic.get_json() == {"ok": "tag post success"}

    deleted = alice.delete("/api/v1/account", json={"password": account + "-pw"})
    assert deleted.status_code == 200 and deleted.get_json() == {"deleted": True}

    assert not query("SELECT 1 FROM member WHERE member_id=%s", alice_id)
    assert not query("SELECT 1 FROM block WHERE member_id=%s", alice_id)
    assert not query("SELECT 1 FROM block_comment WHERE member_id=%s", alice_id)
    assert not query("SELECT 1 FROM goods WHERE member_id=%s", alice_id)
    assert not query(
        "SELECT 1 FROM friendship WHERE request_from=%s OR request_to=%s", alice_id, alice_id
    )
    # Others' posts stay; comments on her post went with the post.
    assert query("SELECT 1 FROM block WHERE block_id=%s", bobs["block_id"])
    assert query("SELECT 1 FROM member WHERE member_id=%s", bob_id)
    # The tag she created and her topic stay, without an author.
    assert query("SELECT create_by FROM tag WHERE name='deltest'")[0]["create_by"] is None
    assert (
        query("SELECT member_id FROM bricks WHERE title='topic' ORDER BY brick_id DESC")[0][
            "member_id"
        ]
        is None
    )
    # Signed out, and the account name is free again.
    assert alice.get("/api/member").get_json().get("error")
    assert (
        alice.put(
            "/api/member", json={"account": account, "password": account + "-pw", "time": NOW}
        )
        .get_json()
        .get("error")
    )
