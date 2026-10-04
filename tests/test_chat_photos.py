"""Photos in chat (api/v1/chats.py): presigned upload, then a message with the key."""

import importlib

import pytest
from botocore.exceptions import ClientError

api_images = importlib.import_module("api.blueprints.api_images")


def befriend(query, a_id, b_id):
    query(
        "INSERT INTO friendship (request_from, request_to, status) VALUES (%s, %s, '0')",
        a_id,
        b_id,
    )


@pytest.fixture()
def s3_has(monkeypatch):
    """Pretend S3 holds every object with this content type (None: holds nothing)."""

    def set_type(content_type):
        def head(**kw):
            if content_type is None:
                raise ClientError({"Error": {"Code": "404"}}, "HeadObject")
            return {"ContentType": content_type}

        monkeypatch.setattr(api_images.s3, "head_object", head)

    return set_type


@pytest.fixture()
def pair(member, query):
    alice, alice_id, alice_account = member()
    bob, bob_id, bob_account = member()
    befriend(query, alice_id, bob_id)
    return alice, alice_id, alice_account, bob, bob_id, bob_account


def sign(client, account, content_type="image/webp"):
    return client.post(f"/api/v1/chats/{account}/images", json={"content_type": content_type})


def test_photo_is_signed_for_friends_only(pair, member):
    alice, alice_id, _, _, _, bob_account = pair
    signed = sign(alice, bob_account)
    assert signed.status_code == 200
    key = signed.get_json()["data"]["key"]
    assert key.startswith(f"dm_{alice_id}_") and api_images.CHAT_KEY.match(key)
    assert signed.get_json()["data"]["fields"]["key"] == key
    assert sign(alice, bob_account, "text/html").status_code == 400
    carol, _, _ = member()
    assert sign(carol, bob_account).status_code == 403


def test_send_a_photo(pair, s3_has, socket_client):
    alice, _, _, bob, _, bob_account = pair
    key = sign(alice, bob_account).get_json()["data"]["key"]
    s3_has("image/webp")
    sb = socket_client(bob)
    sb.get_received()
    sent = alice.post(f"/api/v1/chats/{bob_account}/messages", json={"image": key})
    assert sent.status_code == 201
    message = sent.get_json()["data"]
    assert message["image"] == f"/images/{key}" and message["content"] == ""
    pushed = [m["args"][0] for m in sb.get_received() if m["name"] == "chat:message"]
    assert pushed == [message]
    # With a caption too.
    key2 = sign(alice, bob_account).get_json()["data"]["key"]
    captioned = alice.post(
        f"/api/v1/chats/{bob_account}/messages", json={"image": key2, "content": "看這個"}
    )
    assert captioned.get_json()["data"]["content"] == "看這個"
    # It shows in the conversation list and the history.
    chats = bob.get("/api/v1/chats").get_json()["data"]
    assert chats[0]["last"]["image"] == f"/images/{key2}"


def test_photos_that_are_not_mine_unused_and_uploaded_are_refused(pair, member, s3_has):
    alice, _, alice_account, bob, _, bob_account = pair
    url = f"/api/v1/chats/{bob_account}/messages"
    key = sign(alice, bob_account).get_json()["data"]["key"]
    s3_has(None)
    assert alice.post(url, json={"image": key}).status_code == 400  # not uploaded yet
    s3_has("text/html")
    assert alice.post(url, json={"image": key}).status_code == 400  # not an image
    s3_has("image/png")
    # Bob cannot send Alice's photo, and nobody can make up a key.
    assert (
        bob.post(f"/api/v1/chats/{alice_account}/messages", json={"image": key}).status_code == 400
    )
    assert alice.post(url, json={"image": "dm_1_" + "0" * 32}).status_code == 400
    assert alice.post(url, json={"image": "block_1"}).status_code == 400
    assert alice.post(url, json={"image": key}).status_code == 201
    assert alice.post(url, json={"image": key}).status_code == 400  # used once


def test_only_the_two_of_them_can_open_the_photo(pair, member, s3_has, client):
    alice, _, _, bob, _, bob_account = pair
    key = sign(alice, bob_account).get_json()["data"]["key"]
    s3_has("image/jpeg")
    alice.post(f"/api/v1/chats/{bob_account}/messages", json={"image": key})
    for viewer in (alice, bob):
        response = viewer.get(f"/images/{key}")
        assert response.status_code == 302 and key in response.headers["Location"]
    carol, _, _ = member()
    assert carol.get(f"/images/{key}").status_code == 404
    assert client.get(f"/images/{key}").status_code == 404
    # A key that was signed but never sent is nobody's.
    unsent = sign(alice, bob_account).get_json()["data"]["key"]
    assert alice.get(f"/images/{unsent}").status_code == 404


def test_signing_is_rate_limited(pair, monkeypatch):
    alice, _, _, _, _, bob_account = pair
    monkeypatch.setattr("api.v1.chats.PHOTO_UPLOADS", 2)
    codes = [sign(alice, bob_account).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_reported_photo_reaches_the_admin(pair, s3_has, query, app, monkeypatch):
    alice, _, _, bob, _, bob_account = pair
    key = sign(alice, bob_account).get_json()["data"]["key"]
    s3_has("image/png")
    message_id = alice.post(
        f"/api/v1/chats/{bob_account}/messages", json={"image": key}
    ).get_json()["data"]["id"]
    assert (
        bob.post("/api/v1/reports", json={"type": "message", "id": message_id, "reason": "sexual"})
    ).status_code == 201
    snapshot = query(
        "SELECT snapshot FROM report WHERE target_type='message' AND target_id=%s", message_id
    )[0]["snapshot"]
    assert key in snapshot
    monkeypatch.setitem(app.config, "ADMIN_ACCOUNTS", frozenset({bob_account}))
    groups = bob.get("/api/v1/admin/reports").get_json()["data"]
    mine = next(g for g in groups if g["type"] == "message" and g["id"] == message_id)
    assert mine["photo"] == f"/images/{key}"


def test_deleting_an_account_deletes_chat_photos_both_ways(pair, s3_has, monkeypatch):
    alice, _, alice_account, bob, _, bob_account = pair
    s3_has("image/png")
    from_alice = sign(alice, bob_account).get_json()["data"]["key"]
    alice.post(f"/api/v1/chats/{bob_account}/messages", json={"image": from_alice})
    from_bob = sign(bob, alice_account).get_json()["data"]["key"]
    bob.post(f"/api/v1/chats/{alice_account}/messages", json={"image": from_bob})
    removed = []
    monkeypatch.setattr("api.v1.account.remove_images", lambda keys: removed.extend(keys))
    assert (
        alice.delete("/api/v1/account", json={"password": alice_account + "-pw"}).status_code == 200
    )
    assert {from_alice, from_bob} <= set(removed)
