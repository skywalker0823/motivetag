"""讚 / 爛 on posts and likes on comments: one reaction at most, a second tap takes it back."""


def exp_of(query, member_id):
    return query("SELECT exp FROM member WHERE member_id=%s", member_id)[0]["exp"]


def new_post(client):
    result = client.post("/api/blocks", json={"type": "PUBLIC", "content": "react to me"})
    return result.get_json()["data"][0]["block_id"]


def react(client, block_id, reaction):
    return client.put(f"/api/v1/posts/{block_id}/reaction", json={"reaction": reaction})


def mine(client, block_id):
    posts = client.get("/api/v1/posts/explore").get_json()["data"]
    post = next(p for p in posts if p["block_id"] == block_id)
    return post["liked"], post["disliked"], post["good"], post["bad"]


def test_like_and_dislike_exclude_each_other_and_can_be_taken_back(member):
    alice, _, _ = member()
    bob, _, _ = member()
    block_id = new_post(alice)

    assert react(bob, block_id, "like").get_json()["data"] == {
        "reaction": "like",
        "good": 1,
        "bad": 0,
    }
    # Switching to 爛 removes the 讚.
    assert react(bob, block_id, "dislike").get_json()["data"] == {
        "reaction": "dislike",
        "good": 0,
        "bad": 1,
    }
    assert mine(bob, block_id) == (False, True, 0, 1)
    # null takes it back.
    assert react(bob, block_id, None).get_json()["data"]["bad"] == 0
    assert mine(bob, block_id) == (False, False, 0, 0)


def test_taking_a_like_back_and_again_earns_nothing_more(member, query):
    alice, alice_id, _ = member()
    bob, bob_id, _ = member()
    block_id = new_post(alice)
    for reaction in ("like", None, "like", None, "like"):
        react(bob, block_id, reaction)
    assert exp_of(query, bob_id) == 1
    assert exp_of(query, alice_id) == 20 + 5


def test_old_endpoints_also_keep_one_reaction(member):
    alice, _, _ = member()
    bob, _, _ = member()
    block_id = new_post(alice)
    bob.patch("/api/blocks", json={"block_id": block_id})
    bob.put("/api/blocks", json={"block_id": block_id})
    assert mine(bob, block_id) == (False, True, 0, 1)
    again = bob.put("/api/blocks", json={"block_id": block_id}).get_json()
    assert again["error"] == "you pressed this boo before"


def test_bad_reactions_are_refused(member):
    alice, _, _ = member()
    block_id = new_post(alice)
    assert react(alice, block_id, "love").status_code == 400
    assert react(alice, 10**9, "like").status_code == 404


def test_comment_likes_toggle(member, query):
    alice, alice_id, _ = member()
    bob, bob_id, _ = member()
    block_id = new_post(alice)
    result = alice.post("/api/message", json={"block_id": block_id, "message": "hi", "score": 0})
    comment_id = result.get_json()["comment"]["comment_id"]
    url = f"/api/v1/comments/{comment_id}/like"
    assert bob.put(url, json={"liked": True}).get_json()["data"] == {"liked": True, "likes": 1}
    assert bob.put(url, json={"liked": False}).get_json()["data"] == {"liked": False, "likes": 0}
    assert bob.put(url, json={"liked": True}).get_json()["data"]["likes"] == 1
    assert bob.put(url, json={"liked": "yes"}).status_code == 400
    assert bob.put("/api/v1/comments/999999999/like", json={"liked": True}).status_code == 404
    # Liked twice today: counted once.
    assert exp_of(query, bob_id) == 1
    assert exp_of(query, alice_id) == 20 + 5 + 3
