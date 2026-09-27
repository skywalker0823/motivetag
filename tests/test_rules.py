"""Privacy and game rules the server enforces, whatever the browser sends."""

import uuid

from conftest import NOW


def post(client, content, kind="Normal", tags=None, vote_box=None):
    result = client.post(
        "/api/blocks",
        json={"type": kind, "content": content, "time": NOW, "tags": tags, "vote_box": vote_box},
    ).get_json()
    return result["data"][0]


def tag_feed(client, tag):
    result = client.get(f"/api/blocks?page=0&key={tag}").get_json()
    return result.get("data", [])


def new_tag():
    return "t" + uuid.uuid4().hex[:10]


def test_anonymous_author_is_hidden_from_others(member):
    alice, alice_id, _ = member()
    bob, _, _ = member()
    tag = new_tag()
    block = post(alice, f"secret crush #{tag}", kind="Anonymous", tags="Anonymous")
    seen = [b for b in tag_feed(bob, tag) if b["block_id"] == block["block_id"]]
    assert seen and seen[0]["account"] is None and seen[0]["member_id"] is None
    own = [b for b in tag_feed(alice, tag) if b["block_id"] == block["block_id"]]
    assert own[0]["member_id"] == alice_id


def test_secret_posts_stay_out_of_tag_search(member):
    alice, _, _ = member()
    bob, _, _ = member()
    tag = new_tag()
    block = post(alice, f"diary #{tag}", kind="SECRET")
    assert block["block_id"] not in [b["block_id"] for b in tag_feed(bob, tag)]
    assert block["block_id"] in [b["block_id"] for b in tag_feed(alice, tag)]


def test_new_post_is_returned_even_with_the_same_timestamp(member):
    alice, _, _ = member()
    first = post(alice, "one")
    second = post(alice, "two")
    assert second["block_id"] != first["block_id"]
    assert second["content"] == "two"


def test_vote_option_must_belong_to_the_post(member, query):
    alice, _, _ = member()
    bob, bob_id, _ = member()
    poll = post(alice, "tea or coffee", vote_box=["tea", "coffee"])
    other = post(alice, "no poll here")
    option = poll["votes"][0]["vote_option_id"]
    wrong = {"vote_option_id": option, "block_id": other["block_id"]}
    assert "error" in bob.post("/api/vote", json=wrong).get_json()
    right = {"vote_option_id": option, "block_id": poll["block_id"]}
    assert bob.post("/api/vote", json=right).get_json()["ok"]
    assert "error" in bob.post("/api/vote", json=right).get_json()
    assert len(query("SELECT * FROM votes WHERE member_id=%s", bob_id)) == 1


def test_tag_popularity_counts_each_subscriber_once(member, query):
    alice, _, _ = member()
    bob, _, _ = member()
    tag = new_tag()

    def popularity():
        return query("SELECT popularity FROM tag WHERE name=%s", tag)[0]["popularity"]

    sub = alice.patch("/api/member_tags", json={"tag": tag}).get_json()
    assert sub["ok"] and popularity() == 1
    assert "error" in alice.patch("/api/member_tags", json={"tag": tag}).get_json()
    bob.patch("/api/member_tags", json={"tag": tag})
    assert popularity() == 2
    alice.delete("/api/member_tags", json={"tag": sub["member_tag_id"]})
    alice.delete("/api/member_tags", json={"tag": sub["member_tag_id"]})
    assert popularity() == 1
    # Popularity can no longer be set directly.
    assert alice.patch("/api/tag", json={"tag": tag}).status_code == 405
    assert alice.delete("/api/tag", json={"tag": tag}).status_code == 405


def signup(client, **overrides):
    account = "s" + uuid.uuid4().hex[:10]
    body = {
        "account": account,
        "password": "long-enough",
        "email": account + "@example.com",
        "birthday": "2000-1-1",
        "first_signup": "2026-9-27",
    }
    body.update(overrides)
    return client.post("/api/member", json=body)


def test_signup_validates_input(client):
    assert signup(client).get_json() == {"ok": True}
    assert signup(client, account="ab").status_code == 400
    assert signup(client, account="api").status_code == 400
    assert signup(client, account="a/b<script>").status_code == 400
    assert signup(client, password="short").status_code == 400
    assert signup(client, email="not-an-email").status_code == 400
    assert signup(client, birthday="2000-13-40").status_code == 400
    assert client.post("/api/member", json={}).status_code == 400


def test_sign_in_rejects_missing_fields(client):
    assert client.put("/api/member", json={"account": "guest"}).status_code == 400
