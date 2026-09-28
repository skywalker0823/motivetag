"""Demo members and activity, so a fresh site does not look empty.

    python scripts/demo_data.py seed      create demo members, posts, polls, comments…
    python scripts/demo_data.py remove    delete every demo member and what they made

Everything goes through the site's own API (Flask's test client, no network), so the
same validation, exp and tag popularity rules apply as for real members. Timestamps
are then spread over the past two weeks. Demo members are recognisable by their
e-mail domain and have random passwords nobody knows. In production this runs inside
the app container (the "Demo data" GitHub Actions workflow does it).
"""

import os
import random
import secrets
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from demo_content import ANONYMOUS_POSTS, COMMENTS, POSTS, TOPICS, USERS  # noqa: E402

from api import create_app  # noqa: E402
from data.data import Member  # noqa: E402
from module.clock import TAIPEI, taipei_now  # noqa: E402

DEMO_DOMAIN = "demo.motivetag.com"
DAYS = 14


def members(query):
    return query("SELECT member_id, account FROM member WHERE email LIKE %s", (f"%@{DEMO_DOMAIN}",))


class Demo:
    def __init__(self, app, rng):
        self.app = app
        self.rng = rng
        self.clients = {}  # account -> signed-in test client
        self.ids = {}  # account -> member_id
        self.posts = []  # (block_id, author, tag, poll options)
        self.comments = []  # comment ids
        self.topics = []  # brick ids

    # ---------- helpers ----------

    def client(self, account):
        return self.clients[account]

    def call(self, account, method, path, body=None):
        response = getattr(self.client(account), method)(path, json=body)
        data = response.get_json(silent=True) or {}
        if response.status_code >= 400 or (isinstance(data, dict) and data.get("error")):
            raise RuntimeError(f"{account} {method.upper()} {path}: {response.status_code} {data}")
        return data

    def fans_of(self, tag, exclude=None):
        return [u for u, _, tags in USERS if tag in tags and u != exclude]

    def others(self, exclude):
        return [u for u, _, _ in USERS if u != exclude]

    # ---------- steps ----------

    def create_members(self):
        for account, mood, tags in USERS:
            client = self.app.test_client()
            # Production cookies are Secure, so the test client must speak "https".
            client.environ_base["wsgi.url_scheme"] = "https"
            password = secrets.token_urlsafe(18)
            birthday = f"{self.rng.randint(1985, 2004)}-{self.rng.randint(1, 12)}-{self.rng.randint(1, 28)}"
            signup = client.post(
                "/api/member",
                json={
                    "account": account,
                    "password": password,
                    "email": f"{account}@{DEMO_DOMAIN}",
                    "birthday": birthday,
                },
            ).get_json()
            if not signup.get("ok"):
                raise RuntimeError(f"sign-up of {account} failed: {signup}")
            signin = client.put("/api/member", json={"account": account, "password": password})
            self.clients[account] = client
            self.ids[account] = signin.get_json()["data"]["member_id"]
            # Demo addresses cannot receive mail, so they are verified directly.
            Member.mark_verified(self.ids[account], taipei_now())
            self.call(account, "patch", "/api/member", {"category": "mood", "content": mood})
            # Most people drop the beginner tag new members start with.
            if self.rng.random() < 0.75:
                for tag in self.call(account, "get", "/api/member_tags")["tag"]:
                    if tag["name"] == "新手引導":
                        self.call(
                            account, "delete", "/api/member_tags", {"tag": tag["member_tag_id"]}
                        )
            for tag in tags:
                self.call(account, "patch", "/api/member_tags", {"tag": tag})
        # A few follow the anonymous board.
        for account in self.rng.sample([u for u, _, _ in USERS], 5):
            self.call(account, "patch", "/api/member_tags", {"tag": "Anonymous"})

    def create_friendships(self):
        pairs = set()
        for account, _, tags in USERS:
            for friend in self.rng.sample(self.fans_of(self.rng.choice(tags), account), 1):
                pairs.add(tuple(sorted((account, friend))))
        for a, b in pairs:
            self.call(a, "post", "/api/friend", {"who": b})
            relation = self.call(b, "get", f"/api/friend?who={a}")["ok"][0]
            self.call(b, "patch", "/api/friend", {"friend_ship_id": relation["friend_ship_id"]})

    def create_posts(self):
        for tag, posts in POSTS.items():
            for post in posts:
                text, options = post if isinstance(post, tuple) else (post, [])
                author = self.rng.choice(self.fans_of(tag))
                block = self.call(
                    author,
                    "post",
                    "/api/blocks",
                    {"type": "PUBLIC", "content": text, "tags": None, "vote_box": options},
                )["data"][0]
                self.posts.append((block["block_id"], author, tag, block["votes"]))
        for text in ANONYMOUS_POSTS:
            author = self.rng.choice([u for u, _, _ in USERS])
            block = self.call(
                author,
                "post",
                "/api/blocks",
                {"type": "Anonymous", "content": text, "tags": "Anonymous", "vote_box": []},
            )["data"][0]
            self.posts.append((block["block_id"], author, "_", []))

    def react(self):
        for block_id, author, tag, options in self.posts:
            crowd = self.others(author)
            fans = self.fans_of(tag, author) if tag != "_" else crowd
            for account in self.rng.sample(crowd, self.rng.randint(1, 9)):
                self.call(account, "patch", "/api/blocks", {"block_id": block_id})
            if self.rng.random() < 0.2:
                account = self.rng.choice(crowd)
                try:
                    self.call(account, "put", "/api/blocks", {"block_id": block_id})
                except RuntimeError:
                    pass  # already reacted
            pool = COMMENTS.get(tag, []) + COMMENTS["_"]
            for account in self.rng.sample(
                fans or crowd, min(len(fans or crowd), self.rng.randint(0, 4))
            ):
                result = self.call(
                    account,
                    "post",
                    "/api/message",
                    {
                        "block_id": block_id,
                        "message": self.rng.choice(pool),
                        "score": self.rng.choice([0, 1, 1, 2, 2, 3, 5, -1]),
                    },
                )
                self.comments.append(result["comment"]["comment_id"])
            if options:
                weights = [self.rng.random() + 0.2 for _ in options]
                for account in self.rng.sample(crowd, self.rng.randint(5, len(crowd))):
                    choice = self.rng.choices(options, weights)[0]
                    self.call(
                        account,
                        "post",
                        "/api/vote",
                        {"vote_option_id": choice["vote_option_id"], "block_id": block_id},
                    )
        for comment_id in self.rng.sample(self.comments, len(self.comments) // 2):
            account = self.rng.choice([u for u, _, _ in USERS])
            try:
                self.call(account, "patch", "/api/message", {"message_id": comment_id})
            except RuntimeError:
                pass

    def create_topics(self):
        for tag, topics in TOPICS.items():
            for title, category, content, replies in topics:
                author = self.rng.choice(self.fans_of(tag))
                self.call(
                    author,
                    "post",
                    "/api/tag_page",
                    {"title": title, "classifi": category, "content": content, "tag_name": tag},
                )
                brick = self.call(author, "get", f"/api/tag_page?keyword={tag}")["data"][0]
                self.topics.append(brick["brick_id"])
                for reply in replies:
                    replier = self.rng.choice(self.fans_of(tag, author) or self.others(author))
                    self.call(
                        replier,
                        "post",
                        "/api/bricks",
                        {"brick_id": brick["brick_id"], "content": reply},
                    )
                for _ in range(self.rng.randint(5, 40)):
                    self.call(author, "patch", "/api/tag_page", {"brick_id": brick["brick_id"]})

    def spread_over_time(self, query):
        """Everything was created just now; move it into the past two weeks."""
        now = datetime.now(TAIPEI).replace(tzinfo=None)

        def moment(start, end):
            return start + (end - start) * self.rng.random()

        ids = list(self.ids.values())
        for member_id in ids:
            joined = now - timedelta(days=self.rng.randint(DAYS + 5, 90))
            query(
                "UPDATE member SET first_signup=%s, last_signin=%s WHERE member_id=%s",
                (joined.date(), moment(now - timedelta(days=2), now), member_id),
            )
        start = now - timedelta(days=DAYS)
        for block_id, _, _, _ in self.posts:
            posted = moment(start, now - timedelta(hours=1))
            query("UPDATE block SET build_time=%s WHERE block_id=%s", (posted, block_id))
            for row in query("SELECT comment_id FROM block_comment WHERE block_id=%s", (block_id,)):
                query(
                    "UPDATE block_comment SET build_time=%s WHERE comment_id=%s",
                    (moment(posted, min(posted + timedelta(days=2), now)), row["comment_id"]),
                )
        for brick_id in self.topics:
            opened = moment(start, now - timedelta(days=1))
            query("UPDATE bricks SET time=%s WHERE brick_id=%s", (opened, brick_id))
            for row in query(
                "SELECT brick_discuss_id FROM brick_discuss WHERE brick_id=%s", (brick_id,)
            ):
                query(
                    "UPDATE brick_discuss SET time=%s WHERE brick_discuss_id=%s",
                    (moment(opened, min(opened + timedelta(days=3), now)), row["brick_discuss_id"]),
                )


def sql(app):
    """A query function over the app's own database connection."""
    from data.data import connection

    def query(statement, params=()):
        with connection.cursor() as cursor:
            cursor.execute(statement, params)
            rows = cursor.fetchall()
        connection.commit()
        return rows

    return query


def seed(app, seed_value=2026):
    # Demo members sign up through the app: no mail to their made-up addresses, and no
    # Turnstile widget to solve. The settings are put back afterwards.
    saved = {key: app.config.get(key) for key in ("MAIL_SUPPRESS", "TURNSTILE_SECRET")}
    app.config.update(MAIL_SUPPRESS=True, TURNSTILE_SECRET=None)
    try:
        return _seed(app, seed_value)
    finally:
        app.config.update(saved)


def _seed(app, seed_value):
    with app.app_context():
        query = sql(app)
        if members(query):
            raise SystemExit("Demo data is already there; run `remove` first.")
        demo = Demo(app, random.Random(seed_value))  # noqa: S311 - repeatable demo content
        demo.create_members()
        demo.create_friendships()
        demo.create_posts()
        demo.react()
        demo.create_topics()
        demo.spread_over_time(query)
        return {
            "members": len(demo.ids),
            "posts": len(demo.posts),
            "comments": len(demo.comments),
            "topics": len(demo.topics),
        }


def remove(app):
    """Deletes demo members; posts, comments, votes, likes and friendships go with them."""
    with app.app_context():
        query = sql(app)
        ids = [row["member_id"] for row in members(query)]
        if not ids:
            return {"members": 0}
        marks = ",".join(["%s"] * len(ids))
        tag_ids = {
            row["tag_id"]
            for row in query(
                f"SELECT tag_id FROM member_tags WHERE member_id IN ({marks})"  # noqa: S608
                f" UNION SELECT bt.tag_id FROM block_tag bt JOIN block b ON b.block_id=bt.block_id"
                f" WHERE b.member_id IN ({marks})",
                (*ids, *ids),
            )
        }
        created = [
            row["tag_id"]
            for row in query(f"SELECT tag_id FROM tag WHERE create_by IN ({marks})", ids)  # noqa: S608
        ]
        # Topics and replies would otherwise stay, authorless.
        query(f"DELETE FROM brick_discuss WHERE member_id IN ({marks})", ids)  # noqa: S608
        query(
            f"DELETE FROM brick_discuss WHERE brick_id IN"  # noqa: S608
            f" (SELECT brick_id FROM bricks WHERE member_id IN ({marks}))",
            ids,
        )
        query(f"DELETE FROM bricks WHERE member_id IN ({marks})", ids)  # noqa: S608
        query(f"DELETE FROM member WHERE member_id IN ({marks})", ids)  # noqa: S608
        # Popularity counts subscriptions and uses; recount the tags demo members touched.
        for tag_id in tag_ids | set(created):
            query(
                """UPDATE tag SET popularity=
                    (SELECT COUNT(*) FROM member_tags WHERE tag_id=%s)
                    + (SELECT COUNT(*) FROM block_tag WHERE tag_id=%s)
                WHERE tag_id=%s""",
                (tag_id, tag_id, tag_id),
            )
        # Tags only demo members ever used disappear too.
        for tag_id in created:
            query(
                """DELETE FROM tag WHERE tag_id=%s
                AND NOT EXISTS (SELECT 1 FROM member_tags WHERE tag_id=%s)
                AND NOT EXISTS (SELECT 1 FROM block_tag WHERE tag_id=%s)
                AND NOT EXISTS (SELECT 1 FROM bricks WHERE tag_id=%s)""",
                (tag_id, tag_id, tag_id, tag_id),
            )
        return {"members": len(ids)}


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command not in {"seed", "remove"}:
        raise SystemExit(__doc__)
    app = create_app(os.getenv("FLASK_CONFIG", "pro"))
    print(command, seed(app) if command == "seed" else remove(app))
