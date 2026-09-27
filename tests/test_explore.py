def post(client, content, kind="PUBLIC"):
    result = client.post("/api/blocks", json={"type": kind, "content": content}).get_json()
    return result["data"][0]["block_id"]


def explore(client, offset=0):
    return client.get(f"/api/v1/posts/explore?offset={offset}")


def test_explore_shows_public_and_anonymous_posts_but_not_secret(member):
    alice, _, alice_account = member()
    bob, _, _ = member()
    public = post(alice, "hello #explore")
    secret = post(alice, "only me", "SECRET")
    anonymous = post(alice, "guess who", "Anonymous")

    posts = {p["block_id"]: p for p in explore(bob).get_json()["data"]}
    assert posts[public]["account"] == alice_account
    assert posts[public]["tags"] == ["explore"]
    assert "comments" in posts[public] and "votes" in posts[public]
    assert secret not in posts
    assert posts[anonymous]["account"] is None
    assert posts[anonymous]["member_id"] is None


def test_explore_pages_and_errors(member, client):
    alice, _, _ = member()
    ids = [post(alice, f"post {i}") for i in range(3)]
    first = [p["block_id"] for p in explore(alice).get_json()["data"]]
    assert first[:3] == ids[::-1]  # newest first
    second = [p["block_id"] for p in explore(alice, 1).get_json()["data"]]
    assert second[0] == first[1]

    bad = explore(alice, -1)
    assert bad.status_code == 400
    assert bad.get_json()["error"]["code"] == "bad_offset"
    assert client.get("/api/v1/posts/explore").status_code == 401
