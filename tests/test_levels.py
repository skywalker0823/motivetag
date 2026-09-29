"""Levels and exp (module/levels.py, ADR 0015)."""

import importlib.util
from pathlib import Path

from module import levels


def exp_of(query, member_id):
    return query("SELECT exp FROM member WHERE member_id=%s", member_id)[0]["exp"]


def post(client, content="level test"):
    return client.post("/api/blocks", json={"type": "PUBLIC", "content": content})


def test_curve():
    assert [levels.level_of(e) for e in (0, 49, 50, 199, 200, 799, 800, 4050)] == [
        1,
        1,
        2,
        2,
        3,
        4,
        5,
        10,
    ]
    assert levels.exp_for(10) == 4050
    assert levels.level_of(None) == 1 and levels.level_of(-5) == 1


def test_posting_is_capped_per_day(member, query):
    alice, alice_id, _ = member()
    for n in range(5):
        assert post(alice, f"post {n}").get_json()["ok"]
    assert exp_of(query, alice_id) == 3 * 20


def test_newcomers_post_ten_times_a_day(member):
    alice, _, _ = member()
    results = [post(alice, f"post {n}") for n in range(11)]
    assert [r.status_code for r in results] == [200] * 10 + [429]
    assert "Lv 3" in results[-1].get_json()["error"]


def test_authors_earn_from_likes_and_comments(member, query):
    alice, alice_id, _ = member()
    bob, bob_id, _ = member()
    block_id = post(alice).get_json()["data"][0]["block_id"]
    bob.patch("/api/blocks", json={"block_id": block_id})
    bob.put("/api/blocks", json={"block_id": block_id})  # a boo earns nobody anything
    result = bob.post("/api/message", json={"block_id": block_id, "message": "hi", "score": 0})
    comment_id = result.get_json()["comment"]["comment_id"]
    alice.patch("/api/message", json={"message_id": comment_id})
    # Alice: post 20 + like received 5 + comment received 3 + like given 1
    assert exp_of(query, alice_id) == 29
    # Bob: like given 1 + comment 5 + comment like received 3
    assert exp_of(query, bob_id) == 9


def test_liking_my_own_comment_gives_no_author_bonus(member, query):
    alice, alice_id, _ = member()
    block_id = post(alice).get_json()["data"][0]["block_id"]
    result = alice.post("/api/message", json={"block_id": block_id, "message": "me", "score": 0})
    alice.patch("/api/message", json={"message_id": result.get_json()["comment"]["comment_id"]})
    assert exp_of(query, alice_id) == 20 + 5 + 1


def test_first_visit_of_the_day_and_streaks(member, query):
    alice, alice_id, account = member()
    query(
        "UPDATE member SET last_active_day=CURDATE() - INTERVAL 1 DAY, streak=6 WHERE member_id=%s",
        alice_id,
    )
    before = exp_of(query, alice_id)
    page = alice.get(f"/{account}").get_data(as_text=True)
    assert '"streak": 7' in page
    assert exp_of(query, alice_id) == before + 10 + 50
    alice.get(f"/{account}")  # a second visit the same day counts nothing
    assert exp_of(query, alice_id) == before + 60


def test_exp_is_pushed_with_level_ups(member, socket_client, query):
    alice, alice_id, _ = member()
    query("UPDATE member SET exp=45 WHERE member_id=%s", alice_id)
    sa = socket_client(alice)
    sa.get_received()
    post(alice)
    pushed = [m["args"][0] for m in sa.get_received() if m["name"] == "exp"]
    assert pushed == [{"exp": 65, "level": 2, "gained": 20, "action": "post", "level_up": True}]


def test_topics_need_level_three(member, query):
    alice, alice_id, _ = member()
    body = {"title": "t", "content": "c", "classifi": "閒聊", "tag_name": "新手引導"}
    assert alice.post("/api/tag_page", json=body).status_code == 403
    query("UPDATE member SET exp=200 WHERE member_id=%s", alice_id)
    assert alice.post("/api/tag_page", json=body).get_json() == {"ok": "tag post success"}


def test_levels_show_on_posts_but_not_for_anonymous_authors(member, query):
    alice, alice_id, _ = member()
    bob, _, _ = member()
    query("UPDATE member SET exp=800 WHERE member_id=%s", alice_id)
    post(alice, "public")
    alice.post("/api/blocks", json={"type": "Anonymous", "content": "secret identity"})
    posts = {p["content"]: p for p in bob.get("/api/v1/posts/explore").get_json()["data"]}
    assert posts["public"]["level"] == 5
    assert posts["secret identity"]["level"] is None


def test_migration_keeps_every_level():
    path = Path(__file__).parent.parent / "migrations/versions/0006_levels.py"
    spec = importlib.util.spec_from_file_location("levels_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    for exp in [*range(0, 3000), 12345, 123456]:
        new = migration.convert(exp, migration.old_level, migration.old_total, migration.new_total)
        assert levels.level_of(new) == migration.old_level(exp)
        back = migration.convert(new, migration.new_level, migration.new_total, migration.old_total)
        assert abs(back - exp) <= 1
