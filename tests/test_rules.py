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


def test_hashtags_stop_at_punctuation(member):
    alice, _, _ = member()
    tag = new_tag()
    block = post(alice, f"今天喝 #{tag}，很好喝！#{tag} #b_2")
    assert block["tags"] == [tag, "b_2"]


def test_feed_carries_comments_poll_and_my_reactions(member):
    alice, _, _ = member()
    bob, _, _ = member()
    tag = new_tag()
    block = post(alice, f"poll #{tag}", vote_box=["a", "b"])
    option = block["votes"][0]["vote_option_id"]
    bob.post("/api/vote", json={"vote_option_id": option, "block_id": block["block_id"]})
    bob.patch("/api/blocks", json={"block_id": block["block_id"]})
    bob.post("/api/message", json={"block_id": block["block_id"], "message": "hi", "score": 2})
    seen = next(b for b in tag_feed(bob, tag) if b["block_id"] == block["block_id"])
    assert seen["liked"] is True and seen["disliked"] is False
    assert [(o["option_name"], o["count"], o["mine"]) for o in seen["votes"]] == [
        ("a", 1, True),
        ("b", 0, False),
    ]
    assert [(c["content"], c["given_score"]) for c in seen["comments"]] == [("hi", 2)]
    # Alice sees the counts but not that she voted.
    mine = next(b for b in tag_feed(alice, tag) if b["block_id"] == block["block_id"])
    assert [o["mine"] for o in mine["votes"]] == [False, False]
    assert "member_id" not in str(alice.get(f"/api/vote?block_id={block['block_id']}").get_json())


def test_posts_and_comments_are_validated(member):
    alice, _, _ = member()

    def create(**body):
        base = {"type": "PUBLIC", "content": "hello", "tags": None, "vote_box": []}
        return alice.post("/api/blocks", json={**base, **body})

    assert create(content="   ").status_code == 400
    assert create(content="x" * 2001).status_code == 400
    assert create(type="ADMIN").status_code == 400
    assert create(vote_box=["only one"]).status_code == 400
    assert create(vote_box=list("abcdef")).status_code == 400
    block = create().get_json()["data"][0]

    def comment(**body):
        base = {"block_id": block["block_id"], "message": "hi", "score": 0}
        return alice.post("/api/message", json={**base, **body})

    assert comment(score=99).status_code == 400
    assert comment(message="").status_code == 400
    assert comment(score=-5).get_json()["comment"]["given_score"] == -5


def test_secret_posts_cannot_be_read_or_touched_by_others(member):
    alice, _, _ = member()
    bob, _, _ = member()
    secret = post(alice, "diary", kind="SECRET")
    block_id = secret["block_id"]
    assert bob.get(f"/api/message?block_id={block_id}").status_code == 404
    assert bob.post("/api/message", json={"block_id": block_id, "message": "hi"}).status_code == 404
    assert bob.patch("/api/blocks", json={"block_id": block_id}).status_code == 404
    assert alice.get(f"/api/message?block_id={block_id}").status_code == 200


def test_times_come_from_the_server(member, query):
    alice, _, _ = member()
    block = alice.post(
        "/api/blocks",
        json={"type": "PUBLIC", "content": "hi", "time": "1999-01-01 00:00:00", "vote_box": []},
    ).get_json()["data"][0]
    row = query("SELECT build_time FROM block WHERE block_id=%s", block["block_id"])[0]
    assert row["build_time"].year >= 2026


def test_mood_and_tag_names_are_validated(member):
    alice, _, _ = member()
    assert (
        alice.patch("/api/member", json={"category": "mood", "content": "x" * 101}).status_code
        == 400
    )
    assert (
        alice.patch("/api/member", json={"category": "email", "content": "a@b.c"}).status_code
        == 400
    )
    assert alice.patch("/api/member", json={"category": "mood", "content": "開心"}).get_json()["ok"]
    assert alice.patch("/api/member_tags", json={"tag": "有 空白"}).status_code == 400
    assert alice.patch("/api/member_tags", json={"tag": "#" + new_tag()}).get_json()["ok"]
