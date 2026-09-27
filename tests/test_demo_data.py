"""scripts/demo_data.py seeds through the real API and removes only what it made."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts"))

import demo_data  # noqa: E402


def test_seed_then_remove_leaves_real_members_alone(app, member, query):
    alice, alice_id, _ = member()
    alice.patch("/api/member_tags", json={"tag": "咖啡"})
    demo_data.remove(app)  # a previous run in this database, if any

    counts = demo_data.seed(app)
    assert counts["members"] == len(demo_data.USERS)
    assert counts["posts"] > 50 and counts["comments"] > 50 and counts["topics"] > 0
    feed = alice.get("/api/blocks?page=0&key=咖啡").get_json()["data"]
    assert feed and all(post["build_time"] for post in feed)

    assert demo_data.remove(app) == {"members": len(demo_data.USERS)}
    assert not query("SELECT 1 FROM member WHERE email LIKE %s", f"%@{demo_data.DEMO_DOMAIN}")
    assert query("SELECT 1 FROM member WHERE member_id=%s", alice_id)
    subscribed = query(
        "SELECT t.popularity FROM member_tags mt JOIN tag t USING (tag_id) WHERE mt.member_id=%s",
        alice_id,
    )
    assert subscribed and subscribed[0]["popularity"] >= 1
