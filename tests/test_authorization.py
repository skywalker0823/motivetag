import io

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


def test_only_owner_can_set_block_image(member):
    alice, _, _ = member()
    bob, _, _ = member()
    block_id = create_block(alice)
    upload = {"image": (io.BytesIO(b"x"), "a.png"), "type": "block", "target_id": str(block_id)}
    assert bob.post("/api/images", data=upload).status_code == 403


def test_image_extension_is_checked(member):
    alice, _, _ = member()
    upload = {"image": (io.BytesIO(b"x"), "a.html"), "type": "avatar", "target_id": "null"}
    assert alice.post("/api/images", data=upload).status_code == 400


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
