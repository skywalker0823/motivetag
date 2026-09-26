import pytest
from conftest import NOW


def create_block(client):
    result = client.post(
        "/api/blocks",
        json={"type": "Normal", "content": "hi #test", "time": NOW, "tags": None, "vote_box": []},
    ).get_json()
    return result["data"][0]["block_id"]


def exp_of(query, member_id):
    return query("SELECT exp FROM member WHERE member_id=%s", member_id)[0]["exp"]


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/api/blocks?page=0"),
        ("delete", "/api/blocks"),
        ("patch", "/api/friend"),
        ("post", "/api/notifi"),
        ("post", "/api/images"),
        ("delete", "/api/tag"),
    ],
)
def test_member_endpoints_require_login(client, method, path):
    assert getattr(client, method)(path, json={}).status_code == 401


def test_only_owner_can_delete_block(member, query):
    alice, _, _ = member()
    bob, _, _ = member()
    block_id = create_block(alice)
    assert bob.delete("/api/blocks", json={"block_id": block_id}).status_code == 403
    assert query("SELECT * FROM block WHERE block_id=%s", block_id)
    assert alice.delete("/api/blocks", json={"block_id": block_id}).status_code == 200
    assert not query("SELECT * FROM block WHERE block_id=%s", block_id)


def sign(client, kind, target_id, content_type="image/png"):
    return client.post(
        "/api/images/upload",
        json={"type": kind, "target_id": target_id, "content_type": content_type},
    )


def test_only_owner_can_sign_block_image(member):
    alice, _, _ = member()
    bob, _, _ = member()
    block_id = create_block(alice)
    assert sign(bob, "block", block_id).status_code == 403
    assert sign(alice, "block", block_id).get_json()["fields"]["key"] == f"block_{block_id}"


def test_upload_is_signed_for_own_avatar_only(member):
    alice, alice_id, _ = member()
    signed = sign(alice, "avatar", 12345).get_json()
    assert signed["fields"]["key"] == f"avatar_{alice_id}"
    assert signed["fields"]["Content-Type"] == "image/png"
    assert signed["url"].startswith("https://motivetag-images-test.s3.ap-east-2.amazonaws.com")


def test_image_type_is_checked(member):
    alice, _, _ = member()
    assert sign(alice, "avatar", None, content_type="text/html").status_code == 400


@pytest.fixture()
def uploaded(monkeypatch):
    """Pretend S3 holds an object with the given content type."""
    from api.blueprints import api_images

    def fake_head(content_type):
        monkeypatch.setattr(
            api_images.s3, "head_object", lambda **kw: {"ContentType": content_type}
        )

    return fake_head


def test_finished_upload_sets_block_image(member, query, uploaded):
    alice, _, _ = member()
    bob, _, _ = member()
    block_id = create_block(alice)
    uploaded("image/jpeg")
    finish = {"type": "block", "target_id": block_id}
    assert bob.post("/api/images", json=finish).status_code == 403
    assert alice.post("/api/images", json=finish).get_json()["ok"]
    rows = query("SELECT block_img FROM block WHERE block_id=%s", block_id)
    assert rows[0]["block_img"] == f"block_{block_id}"


def test_finished_upload_rejects_other_content(member, uploaded):
    alice, _, _ = member()
    uploaded("text/html")
    assert alice.post("/api/images", json={"type": "avatar"}).status_code == 400


def test_exp_is_awarded_by_server(member, query):
    alice, alice_id, _ = member()
    bob, bob_id, _ = member()
    block_id = create_block(alice)
    assert exp_of(query, alice_id) == 50
    bob.patch("/api/blocks", json={"block_id": block_id})
    assert exp_of(query, bob_id) == 5
    assert alice.post("/api/level", json={"exp": 99999}).status_code == 405


def test_friend_request_flow_is_scoped(member, query):
    alice, alice_id, _ = member()
    bob, bob_id, bob_account = member()
    carol, _, _ = member()
    alice.post("/api/friend", json={"who": bob_account})
    friendship_id = query(
        "SELECT friend_ship_id FROM friendship WHERE request_from=%s AND request_to=%s",
        alice_id,
        bob_id,
    )[0]["friend_ship_id"]
    body = {"friend_ship_id": friendship_id}
    assert alice.patch("/api/friend", json=body).get_json()["data_changed"] == 0
    assert "error" in carol.delete("/api/friend", json=body).get_json()
    assert bob.patch("/api/friend", json=body).get_json()["data_changed"] == 1


def test_notification_sender_comes_from_session(member, query):
    alice, alice_id, _ = member()
    bob, bob_id, _ = member()
    _, _, carol_account = member()
    content = "spoof-" + str(bob_id)
    bob.post(
        "/api/notifi",
        json={"me": alice_id, "who": carol_account, "type": "x", "content": content, "time": NOW},
    )
    assert query("SELECT sender_id FROM notifi WHERE content=%s", content)[0]["sender_id"] == bob_id


def test_member_tag_delete_is_scoped(member):
    alice, _, _ = member()
    carol, _, _ = member()
    alice.patch("/api/tag", json={"tag": "cats"})
    member_tag_id = alice.patch("/api/member_tags", json={"tag": "cats"}).get_json()[
        "member_tag_id"
    ]
    assert "error" in carol.delete("/api/member_tags", json={"tag": member_tag_id}).get_json()
