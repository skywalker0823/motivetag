import traceback

import pymysql
from dbutils.pooled_db import PooledDB
from flask import g
from werkzeug.security import check_password_hash, generate_password_hash

from config import db_settings

settings = db_settings()


def create_pool():
    for host in settings["hosts"]:
        print(f"try to connect to host:{host}")
        try:
            pool = PooledDB(
                creator=pymysql,
                maxconnections=10,
                mincached=2,
                blocking=True,
                ping=1,  # check a connection when it is taken, so a MySQL restart heals itself
                host=host,
                port=3306,
                user=settings["user"],
                password=settings["password"],
                database=settings["database"],
                charset="utf8mb4",  # the tables are utf8mb4; "utf8" cannot store emoji
                cursorclass=pymysql.cursors.DictCursor,
            )
            print(f"Connect to host:{host} success")
            return pool
        except pymysql.Error as e:
            print(f"Connect to host:{host} failed: {e}")
    raise Exception("All DB's host are down")


POOL = create_pool()


class _RequestConnection:
    """The pooled connection of the current request.

    gunicorn's gevent worker serves many requests at once in one process; sharing a
    single pymysql connection between them interleaves their queries and fails
    ("reentrant call"). Each request (and Socket.IO event) takes its own connection
    from the pool on first use, and release_connection() returns it afterwards.
    """

    def _get(self):
        if "db" not in g:
            g.db = POOL.connection()
        return g.db

    def cursor(self):
        return self._get().cursor()

    def commit(self):
        self._get().commit()


connection = _RequestConnection()


def release_connection(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()  # back to the pool; an unfinished transaction is rolled back


def _in(ids):
    """Placeholders for `IN (...)` with one %s per id."""
    return ",".join(["%s"] * len(ids))


def _is_password_hash(value):
    return isinstance(value, str) and (value.startswith("scrypt:") or value.startswith("pbkdf2:"))


class Member:
    def get_member(account):
        with connection.cursor() as cursor:
            # Every column except the password hash.
            cursor.execute(
                """SELECT member_id, account, email, birthday, first_signup, last_signin,
                member_img, follower, mood, exp, email_verified_at FROM member WHERE account=%s""",
                (account,),
            )
            result = cursor.fetchone()
            connection.commit()
            return result

    def id_for(account):
        """The member_id of `account`, or None."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT member_id FROM member WHERE account=%s", (account,))
            row = cursor.fetchone()
        return row["member_id"] if row else None

    def is_verified(member_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM member WHERE member_id=%s AND email_verified_at IS NOT NULL",
                (member_id,),
            )
            return cursor.fetchone() is not None

    def mark_verified(member_id, time):
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE member SET email_verified_at=%s WHERE member_id=%s", (time, member_id)
            )
        connection.commit()

    def ping():
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

    def account_exists(account):
        with connection.cursor() as cursor:
            got = cursor.execute("SELECT member_id FROM member WHERE account=%s", (account,))
            connection.commit()
            return got != 0

    def sign_up(account, password, email, birthday, first_signup):
        try:
            with connection.cursor() as cursor:
                account_check = cursor.execute(
                    """SELECT * FROM member WHERE account=%s""", (account,)
                )
                email_check = cursor.execute("""SELECT * FROM member WHERE email=%s""", (email,))
                connection.commit()
                if account_check != 0:
                    return "Already registed"
                elif email_check != 0:
                    return "Same email used"
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO 
                    member(
                        account,
                        password,
                        email,
                        birthday,
                        first_signup
                    )VALUES(%s,%s,%s,%s,%s)""",
                    (
                        account,
                        generate_password_hash(password),
                        email,
                        birthday,
                        first_signup,
                    ),
                )
                connection.commit()
                return "ok"
        except Exception as e:
            print("type error: " + str(e))
            print(traceback.format_exc())
            return "sign up database error"

    def sign_in(account, password, time):
        with connection.cursor() as cursor:
            got = cursor.execute("SELECT * FROM member WHERE account=%s", (account,))
            result = cursor.fetchone()
            connection.commit()
            if got == 0:
                return {"msg": "wrong account or password"}
            stored = result["password"]
            if _is_password_hash(stored):
                valid = check_password_hash(stored, password)
            else:
                # Legacy plaintext row: compare once, then upgrade it to a hash.
                valid = stored == password
                if valid:
                    cursor.execute(
                        "UPDATE member SET password=%s WHERE member_id=%s",
                        (generate_password_hash(password), result["member_id"]),
                    )
            if not valid:
                connection.commit()
                return {"msg": "wrong account or password"}
            cursor.execute(
                "UPDATE member SET last_signin=%s WHERE member_id=%s", (time, result["member_id"])
            )
            connection.commit()
            del result["password"]
            return {"msg": "ok", "data": result}

    def patch_user_data(member_id, category, content):
        if category == "mood":
            with connection.cursor() as cursor:
                result = cursor.execute(
                    "UPDATE member SET mood=%s WHERE member_id=%s", (content, member_id)
                )
                connection.commit()
            return result

    def password_matches(member_id, password):
        with connection.cursor() as cursor:
            cursor.execute("SELECT password FROM member WHERE member_id=%s", (member_id,))
            row = cursor.fetchone()
        if not row or not isinstance(password, str):
            return False
        stored = row["password"]
        return (
            check_password_hash(stored, password)
            if _is_password_hash(stored)
            else stored == password
        )

    def delete(member_id):
        """Deletes the member and, through the foreign keys, everything that is theirs.

        Returns the S3 keys of their images (avatar, post images and chat photos either way) for the caller to
        remove, or None if there was no such member.
        """
        with connection.cursor() as cursor:
            cursor.execute("SELECT member_img FROM member WHERE member_id=%s", (member_id,))
            member = cursor.fetchone()
            if member is None:
                return None
            cursor.execute(
                "SELECT block_img FROM block WHERE member_id=%s AND block_img IS NOT NULL",
                (member_id,),
            )
            keys = [row["block_img"] for row in cursor.fetchall()]
            # Their conversations are deleted both ways, photos included.
            cursor.execute(
                """SELECT image FROM direct_message WHERE image IS NOT NULL
                   AND (sender_id=%s OR recipient_id=%s)""",
                (member_id, member_id),
            )
            keys += [row["image"] for row in cursor.fetchall()]
            if member["member_img"]:
                keys.append(member["member_img"])
            cursor.execute("DELETE FROM member WHERE member_id=%s", (member_id,))
            connection.commit()
        return keys

    def getting_data_without_private(member_id):
        """What any member may see about another: age, never the full birthday."""
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT account, TIMESTAMPDIFF(YEAR, birthday, CURDATE()) AS age,
                          first_signup, last_signin, mood, exp
                   FROM member WHERE member_id=%s""",
                (member_id,),
            )
            data = cursor.fetchone()
            return data

    def suggested(member_id, limit=10):
        """Members who share the most tags with me, excluding anyone I already have a
        friendship row with (friends, invitations either way). The starter tag and
        the anonymous board say nothing about someone, so they do not count."""
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT m.member_id, m.account, m.mood, m.last_signin,
                          COUNT(DISTINCT t.tag_id) AS shared_count,
                          GROUP_CONCAT(DISTINCT t.name ORDER BY t.popularity DESC
                                       SEPARATOR '\n') AS shared
                   FROM member_tags mine
                   JOIN member_tags theirs
                     ON theirs.tag_id = mine.tag_id AND theirs.member_id <> mine.member_id
                   JOIN tag t ON t.tag_id = mine.tag_id
                   JOIN member m ON m.member_id = theirs.member_id
                   WHERE mine.member_id = %s AND t.name NOT IN ({_in(NEUTRAL_TAGS)})
                     AND NOT EXISTS (
                       SELECT 1 FROM friendship f
                       WHERE (f.request_from = %s AND f.request_to = m.member_id)
                          OR (f.request_to = %s AND f.request_from = m.member_id))
                     AND NOT EXISTS (
                       SELECT 1 FROM member_block b
                       WHERE (b.blocker_id = %s AND b.blocked_id = m.member_id)
                          OR (b.blocked_id = %s AND b.blocker_id = m.member_id))
                   GROUP BY m.member_id, m.account, m.mood, m.last_signin
                   ORDER BY shared_count DESC, m.last_signin DESC
                   LIMIT %s""",  # noqa: S608 - placeholders only
                (member_id, *NEUTRAL_TAGS, member_id, member_id, member_id, member_id, limit),
            )
            rows = cursor.fetchall()
        for row in rows:
            row["shared"] = row["shared"].split("\n")
        return rows

    def shared_tags(member_id, other_id):
        """Tag names both members subscribe to, most popular first."""
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT DISTINCT t.name, t.popularity FROM member_tags a
                   JOIN member_tags b ON b.tag_id = a.tag_id
                   JOIN tag t ON t.tag_id = a.tag_id
                   WHERE a.member_id = %s AND b.member_id = %s
                     AND t.name NOT IN ({_in(NEUTRAL_TAGS)})
                   ORDER BY t.popularity DESC""",  # noqa: S608 - placeholders only
                (member_id, other_id, *NEUTRAL_TAGS),
            )
            return [row["name"] for row in cursor.fetchall()]


class EmailToken:
    """One-time links for confirming an e-mail address; only token hashes are kept."""

    def create(member_id, token_hash, now, expires_at):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO email_token (token_hash, member_id, created_at, expires_at)"
                " VALUES (%s, %s, %s, %s)",
                (token_hash, member_id, now, expires_at),
            )
        connection.commit()

    def member_for(token_hash, now):
        """The member a still-valid token belongs to, or None."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT member_id FROM email_token WHERE token_hash=%s AND expires_at > %s",
                (token_hash, now),
            )
            row = cursor.fetchone()
            return row["member_id"] if row else None

    def last_sent(member_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT MAX(created_at) AS at FROM email_token WHERE member_id=%s", (member_id,)
            )
            return cursor.fetchone()["at"]

    def sent_since(since, member_id=None):
        """How many links were sent since `since`, by everyone or to one member."""
        with connection.cursor() as cursor:
            if member_id is None:
                cursor.execute(
                    "SELECT COUNT(*) AS n FROM email_token WHERE created_at >= %s", (since,)
                )
            else:
                cursor.execute(
                    "SELECT COUNT(*) AS n FROM email_token WHERE member_id=%s AND created_at >= %s",
                    (member_id, since),
                )
            return cursor.fetchone()["n"]

    def purge(before):
        """Expired links are useless; they only counted towards the daily limits."""
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM email_token WHERE expires_at < %s", (before,))
        connection.commit()


# Tags that do not describe a person: every new member starts with the first, and the
# anonymous board is where people go not to be identified.
NEUTRAL_TAGS = ("新手引導", "Anonymous")

FEED_PAGE = 10  # posts per /api/blocks page; PAGE in static/js/pages/member/feed.js

# What `member_id` (the %s, three times) may see of post `{b}`: nothing by members they
# blocked, nothing they reported, and nothing waiting for review unless it is theirs.
SEEN_BY = """
    AND NOT EXISTS (SELECT 1 FROM member_block mb
                    WHERE mb.blocker_id=%s AND mb.blocked_id={b}.member_id)
    AND NOT EXISTS (SELECT 1 FROM report r WHERE r.reporter_id=%s
                    AND r.target_type='post' AND r.target_id={b}.block_id)
    AND ({b}.hidden=0 OR {b}.member_id=%s)"""


class Block:
    def get_block(member_id, page, obseve_key=None, order_by=None):
        page = int(page)
        sql_observe_key = f"""SELECT account, block_id, block.member_id, content_type, content,
                                     build_time, good, bad, block_img
                              FROM block JOIN member ON member.member_id=block.member_id
                              WHERE block_id IN (SELECT block_id FROM block_tag WHERE tag_id=
                                                 (SELECT tag_id FROM tag WHERE name=%s))
                                AND (content_type <> 'SECRET' OR block.member_id=%s)
                                {SEEN_BY.format(b="block")}
                              ORDER BY build_time DESC LIMIT %s,%s"""  # noqa: S608 - constant fragment
        # My friends' posts, my own and those under tags I follow, minus what I blocked,
        # reported or what waits for review.
        sql_all = f"""SELECT feed.* FROM (
                        SELECT account, block_id, block.member_id, content_type, content,
                               build_time, good, bad, block_img
                        FROM block JOIN member ON member.member_id=block.member_id
                        WHERE block.member_id IN (
                            SELECT request_from FROM friendship
                            WHERE status='0' AND (request_from=%s OR request_to=%s)
                            UNION
                            SELECT request_to FROM friendship
                            WHERE status='0' AND (request_from=%s OR request_to=%s))
                          AND content_type <> 'SECRET' AND content_type <> 'Anonymous'
                        UNION
                        SELECT account, block_id, block.member_id, content_type, content,
                               build_time, good, bad, block_img
                        FROM block JOIN member ON member.member_id=block.member_id
                        WHERE block.member_id=%s
                        UNION
                        SELECT account, block_id, block.member_id, content_type, content,
                               build_time, good, bad, block_img
                        FROM block JOIN member ON member.member_id=block.member_id
                        WHERE block_id IN (SELECT block_id FROM block_tag WHERE tag_id IN
                                           (SELECT tag_id FROM member_tags WHERE member_id=%s))
                          AND content_type <> 'SECRET'
                      ) AS feed JOIN block b ON b.block_id = feed.block_id
                      WHERE 1=1 {SEEN_BY.format(b="b")}
                      ORDER BY feed.build_time DESC
                      LIMIT %s,%s"""  # noqa: S608 - constant fragment
        with connection.cursor() as cursor:
            if obseve_key is None:
                got = cursor.execute(sql_all, (*[member_id] * 6, *[member_id] * 3, page, FEED_PAGE))
            else:
                got = cursor.execute(
                    sql_observe_key,
                    (obseve_key, member_id, *[member_id] * 3, page, FEED_PAGE),
                )
            result = cursor.fetchall()
            connection.commit()
            if got == 0:
                return {"msg": "No blocks found"}
            return {"msg": "ok", "datas": result}

    def explore(offset, member_id):
        """Everyone's newest posts except secret ones; anonymous authors are hidden later."""
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT account, block_id, block.member_id, content_type, content, build_time,
                          good, bad, block_img
                   FROM block JOIN member ON member.member_id=block.member_id
                   WHERE content_type <> 'SECRET' {SEEN_BY.format(b="block")}
                   ORDER BY build_time DESC, block_id DESC LIMIT %s,%s""",  # noqa: S608 - constant fragment
                (*[member_id] * 3, offset, FEED_PAGE),
            )
            return cursor.fetchall()

    def create_my_block(member_id, block):
        try:
            type = block["type"]
            content = block["content"]
            time = block["time"]
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO
                    block(
                        member_id,
                        content_type,
                        content,
                        build_time
                    )VALUES(%s,%s,%s,%s)
                    """,
                    (member_id, type, content, time),
                )
                block_id = cursor.lastrowid
                connection.commit()
                cursor.execute(
                    """SELECT account, block_id, block.member_id, content_type, content, build_time,good,bad,block_img
                               FROM block RIGHT JOIN member ON member.member_id=block.member_id
                               WHERE block_id=%s""",
                    (block_id,),
                )
                result = cursor.fetchone()
                connection.commit()
            return {"msg": "ok", "content": result}
        except Exception as e:
            print("type error: " + str(e))
            print(traceback.format_exc())
            return {"msg": "block create database error"}

    def visible(member_id, block_id):
        """Whether this member may see the post: it exists, is not someone else's secret
        and is not waiting for review (unless it is theirs)."""
        with connection.cursor() as cursor:
            got = cursor.execute(
                """SELECT 1 FROM block WHERE block_id=%s
                   AND ((content_type<>'SECRET' AND hidden=0) OR member_id=%s)""",
                (block_id, member_id),
            )
            return got != 0

    def set_reaction(member_id, block_id, reaction):
        """Sets my reaction to a post: "like", "dislike" or None (neither; one at most).

        Returns (my previous reaction, good count, bad count); the counts are recounted
        from the reaction rows so they cannot drift.
        """
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT EXISTS(SELECT 1 FROM goods WHERE member_id=%s AND block_id=%s) AS liked,
                          EXISTS(SELECT 1 FROM bads WHERE member_id=%s AND block_id=%s) AS disliked""",
                (member_id, block_id, member_id, block_id),
            )
            row = cursor.fetchone()
            previous = "like" if row["liked"] else "dislike" if row["disliked"] else None
            cursor.execute(
                "DELETE FROM goods WHERE member_id=%s AND block_id=%s", (member_id, block_id)
            )
            cursor.execute(
                "DELETE FROM bads WHERE member_id=%s AND block_id=%s", (member_id, block_id)
            )
            if reaction in ("like", "dislike"):
                table = "goods" if reaction == "like" else "bads"
                cursor.execute(
                    f"INSERT INTO {table} (member_id, block_id) VALUES (%s, %s)",  # noqa: S608 - fixed names
                    (member_id, block_id),
                )
            cursor.execute(
                """UPDATE block SET good=(SELECT COUNT(*) FROM goods WHERE block_id=%s),
                                    bad=(SELECT COUNT(*) FROM bads WHERE block_id=%s)
                   WHERE block_id=%s""",
                (block_id, block_id, block_id),
            )
            cursor.execute("SELECT good, bad FROM block WHERE block_id=%s", (block_id,))
            counts = cursor.fetchone()
        connection.commit()
        return previous, counts["good"], counts["bad"]

    def my_reactions(member_id, block_ids):
        """(ids I liked, ids I disliked) among `block_ids`."""
        if not block_ids:
            return set(), set()
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT block_id FROM goods WHERE member_id=%s AND block_id IN ({_in(block_ids)})",  # noqa: S608 - placeholders only
                (member_id, *block_ids),
            )
            liked = {row["block_id"] for row in cursor.fetchall()}
            cursor.execute(
                f"SELECT block_id FROM bads WHERE member_id=%s AND block_id IN ({_in(block_ids)})",  # noqa: S608 - placeholders only
                (member_id, *block_ids),
            )
            disliked = {row["block_id"] for row in cursor.fetchall()}
        return liked, disliked

    def author(block_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT member_id FROM block WHERE block_id=%s", (block_id,))
            row = cursor.fetchone()
        return row["member_id"] if row else None

    def is_owner(member_id, block_id):
        with connection.cursor() as cursor:
            got = cursor.execute(
                "SELECT block_id FROM block WHERE block_id=%s AND member_id=%s",
                (block_id, member_id),
            )
            connection.commit()
            return got != 0

    def modify_block(key, value):
        with connection.cursor() as cursor:
            result = cursor.execute("UPDATE block SET block_img=%s WHERE block_id=%s", (value, key))
            connection.commit()
            return {"ok": result}

    def delete_block(member_id, block_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "DELETE FROM block WHERE block_id=%s AND member_id=%s", (block_id, member_id)
            )
            connection.commit()
        return result


class Block_tags:
    def get_all_tag_of_a_block():
        return None

    def tag_into_block(tags, block_id, member_id):
        try:
            sql1 = "INSERT INTO tag(name,popularity,create_by)VALUES(%s,%s,%s)ON DUPLICATE KEY UPDATE popularity = popularity+1"
            sql2 = "INSERT INTO block_tag(block_id,tag_id)VALUES(%s,(SELECT tag_id FROM tag WHERE name=%s))"
            with connection.cursor() as cursor:
                for tag in tags:
                    cursor.execute(sql1, (tag, 1, member_id))
                    cursor.execute(sql2, (block_id, tag))
                    connection.commit()
            return {"msg": "ok"}
        except Exception as e:
            print("type error: " + str(e))
            print(traceback.format_exc())
            return {"msg": "tag into block database error"}


class Member_tags:
    def getting_member_tags(member_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * from member_tags RIGHT JOIN tag ON member_tags.tag_id=tag.tag_id WHERE member_id=%s",
                (member_id,),
            )
            result = cursor.fetchall()
            connection.commit()
            return {"msg": "ok", "all_tags": result}

    def find_member_tags(member_id, tag):
        with connection.cursor() as cursor:
            count = cursor.execute(
                "SELECT * FROM member_tags WHERE member_id=%s AND tag_id=(SELECT tag_id FROM tag WHERE name=%s)",
                (member_id, tag),
            )
            return count

    def add_member_tag(member_id, tag):
        """Subscribe to a tag (creating it if new); popularity counts each subscriber once."""
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO tag(name,popularity,create_by)VALUES(%s,0,%s) ON DUPLICATE KEY UPDATE tag_id=tag_id",
                (tag, member_id),
            )
            result = cursor.execute(
                """INSERT INTO member_tags(member_id,tag_id)
                SELECT %s, tag_id FROM tag WHERE name=%s AND NOT EXISTS
                (SELECT 1 FROM member_tags WHERE member_id=%s AND tag_id=(SELECT tag_id FROM tag WHERE name=%s))""",
                (member_id, tag, member_id, tag),
            )
            if result:
                cursor.execute("UPDATE tag SET popularity=popularity+1 WHERE name=%s", (tag,))
            cursor.execute(
                "SELECT member_tag_id from member_tags WHERE member_id=%s AND tag_id=(SELECT tag_id from tag WHERE name=%s)",
                (member_id, tag),
            )
            data = cursor.fetchone()
            connection.commit()
        return {"result": result, "data": data}

    def del_member_tag(member_id, member_tag_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tag_id FROM member_tags WHERE member_tag_id=%s AND member_id=%s",
                (member_tag_id, member_id),
            )
            row = cursor.fetchone()
            result = cursor.execute(
                "DELETE FROM member_tags WHERE member_tag_id=%s AND member_id=%s",
                (member_tag_id, member_id),
            )
            if result and row:
                cursor.execute(
                    "UPDATE tag SET popularity=GREATEST(popularity-1,0) WHERE tag_id=%s",
                    (row["tag_id"],),
                )
            connection.commit()
            return {"ok": True, "count": result}

    def new_bie_tag(member_id, tag):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO member_tags(member_id,tag_id)VALUES(%s,(SELECT tag_id FROM tag WHERE name=%s))",
                (member_id, tag),
            )
            connection.commit()
            return None


class Tag:
    def getting_tags_global():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tag_id,name,popularity,create_date,create_by FROM tag ORDER BY popularity DESC LIMIT 10"
            )
            result = cursor.fetchall()
            connection.commit()
            return result


class Friend:
    def confrim_relationship(me, someone_else):
        if not someone_else or someone_else == "undefined":
            with connection.cursor() as cursor:
                result = cursor.execute(
                    "SELECT friend_ship_id,request_from AS req_from_id,request_to AS req_to_id,(SELECT account FROM member WHERE request_from=member_id)AS req_from,(SELECT account FROM member WHERE request_to=member_id)AS req_to,status FROM friendship WHERE (request_from=%s OR request_to=%s)AND(status=%s OR status=%s)",
                    (me, me, "0", "1"),
                )
                data = cursor.fetchall()
                connection.commit()
            return {"data": data, "count": result, "msg": "friend status fetch"}
        with connection.cursor() as cursor:
            result = cursor.execute("SELECT * FROM member WHERE account=%s", (someone_else,))
            data = cursor.fetchall()
            connection.commit()
            if result == 0:
                return {"data": None, "count": 0, "msg": "No such user"}
        with connection.cursor() as cursor:
            result = cursor.execute(
                "SELECT * FROM friendship WHERE ((request_from=%s AND request_to=(SELECT member_id FROM member WHERE account=%s)) OR (request_from=(SELECT member_id FROM member WHERE account=%s) AND request_to=%s)) AND (status=%s OR status=%s)",
                (me, someone_else, someone_else, me, "0", "1"),
            )
            data = cursor.fetchall()
            connection.commit()
            if result != 0:
                return {"count": result, "data": data, "msg": "might be friends"}
            return {"msg": "no data", "count": result}

    def send_friend_request(me, someone_else):
        try:
            with connection.cursor() as cursor:
                result = cursor.execute(
                    "SELECT * FROM friendship WHERE((request_from=%s and request_to=(SELECT member_id FROM member WHERE account=%s)) OR(request_from=(SELECT member_id FROM member WHERE account=%s) and request_to=%s))AND status=%s",
                    (me, someone_else, someone_else, me, "0"),
                )
                connection.commit()
                if result != 0:
                    return {"error": "Already friend"}
            with connection.cursor() as cursor:
                result = cursor.execute(
                    "SELECT * FROM friendship WHERE request_from=(SELECT member_id FROM member WHERE account=%s) AND request_to=%s",
                    (someone_else, me),
                )
                data = cursor.fetchall()
                connection.commit()
                if result != 0:
                    return {"ok": "FAST", "data": data}
            with connection.cursor() as cursor:
                result = cursor.execute(
                    "SELECT * FROM friendship WHERE request_from=%s AND request_to=(SELECT member_id FROM member WHERE account=%s)",
                    (me, someone_else),
                )
                connection.commit()
                if result != 0:
                    return {"error": "same invite found"}
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO friendship(request_from,request_to,status)VALUES(%s,(SELECT member_id FROM member WHERE account=%s),%s)""",
                    (me, someone_else, "1"),
                )
                connection.commit()
                return {"ok": "friend request sent!", "msg": "ok"}
        except Exception as e:
            print("type error: " + str(e))
            print(traceback.format_exc())
            return {"error": "friend requet error", "msg": "already invite"}

    def forge_friend_request(me, target):
        # Only the member who received the request may accept it.
        with connection.cursor() as cursor:
            result = cursor.execute(
                "UPDATE friendship SET status=%s WHERE friend_ship_id=%s AND request_to=%s",
                ("0", target, me),
            )
            cursor.execute("SELECT * FROM friendship WHERE friend_ship_id=%s", (target,))
            data = cursor.fetchone()
            connection.commit()
            return {"ok": "friendship updated", "result": result, "data": data}

    def connect(member_a, member_b):
        """Makes two members friends at once, unless they already have a friendship row."""
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO friendship (request_from, request_to, status)
                   SELECT %s, %s, '0' FROM DUAL WHERE NOT EXISTS (
                     SELECT 1 FROM friendship
                     WHERE (request_from=%s AND request_to=%s)
                        OR (request_from=%s AND request_to=%s))""",
                (member_a, member_b, member_a, member_b, member_b, member_a),
            )
        connection.commit()

    def delete_relation(me, target):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "DELETE FROM friendship WHERE friend_ship_id=%s AND (request_from=%s OR request_to=%s)",
                (target, me, me),
            )
            connection.commit()
            if result != 1:
                return {"error": "Delete friend fail"}
            return {"ok": "Delete Frind success", "result": result}

    def are_friends(member_a, member_b):
        with connection.cursor() as cursor:
            got = cursor.execute(
                """SELECT 1 FROM friendship WHERE status='0'
                   AND ((request_from=%s AND request_to=%s) OR (request_from=%s AND request_to=%s))""",
                (member_a, member_b, member_b, member_a),
            )
        return got != 0

    def friend_ship_checker(member_id, target_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM friendship WHERE (request_from=%s AND request_to=%s)OR(request_from=%s AND request_to=%s)",
                (member_id, target_id, target_id, member_id),
            )
            result = cursor.fetchone()
        return result


class Message:
    def get_message_of_a_block(block_id):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT (SELECT account FROM member WHERE block_comment.member_id=member.member_id)AS account,comment_id,member_id,content,build_time,nice_comment,given_score FROM block_comment WHERE block_id=%s
            """,
                (block_id,),
            )
            data = cursor.fetchall()
            connection.commit()
            return data

    def post_message(member_id, message):
        with connection.cursor() as cursor:
            result = cursor.execute(
                """
                INSERT INTO block_comment(
                    member_id,
                    block_id,
                    content,
                    build_time,
                    given_score
                )VALUES(%s,%s,%s,%s,%s);
            """,
                (
                    member_id,
                    message["block_id"],
                    message["message"],
                    message["time"],
                    message["score"],
                ),
            )
            cursor.execute("SELECT LAST_INSERT_ID()")
            id = cursor.fetchone()
            connection.commit()
            if result == 1:
                return {"ok": id}
            return {"error": "message POST Error"}

    def for_blocks(member_id, block_ids):
        """Comments of several posts at once, oldest first, each with whether I liked it.
        Leaves out comments by members I blocked and comments I reported."""
        if not block_ids:
            return {}
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT c.comment_id, c.block_id, c.member_id, m.account, m.exp, c.content,
                    c.build_time, c.nice_comment, c.given_score,
                    EXISTS(SELECT 1 FROM c_goods g
                           WHERE g.comment_id=c.comment_id AND g.member_id=%s) AS liked
                FROM block_comment c JOIN member m ON m.member_id=c.member_id
                WHERE c.block_id IN ({_in(block_ids)})
                  AND NOT EXISTS (SELECT 1 FROM member_block mb
                                  WHERE mb.blocker_id=%s AND mb.blocked_id=c.member_id)
                  AND NOT EXISTS (SELECT 1 FROM report r WHERE r.reporter_id=%s
                                  AND r.target_type='comment' AND r.target_id=c.comment_id)
                ORDER BY c.comment_id""",  # noqa: S608 - placeholders only
                (member_id, *block_ids, member_id, member_id),
            )
            rows = cursor.fetchall()
        comments = {block_id: [] for block_id in block_ids}
        for row in rows:
            row["liked"] = bool(row["liked"])
            comments[row["block_id"]].append(row)
        return comments

    def author(comment_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT member_id FROM block_comment WHERE comment_id=%s", (comment_id,))
            row = cursor.fetchone()
        return row["member_id"] if row else None

    def comment(comment_id):
        """(block_id, author) of a comment, or None."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT block_id, member_id FROM block_comment WHERE comment_id=%s", (comment_id,)
            )
            return cursor.fetchone()

    def set_like(member_id, comment_id, liked):
        """Likes or unlikes a comment; returns (liked before, like count)."""
        with connection.cursor() as cursor:
            before = cursor.execute(
                "DELETE FROM c_goods WHERE member_id=%s AND comment_id=%s", (member_id, comment_id)
            )
            if liked:
                cursor.execute(
                    "INSERT INTO c_goods (member_id, comment_id) VALUES (%s, %s)",
                    (member_id, comment_id),
                )
            cursor.execute(
                """UPDATE block_comment
                   SET nice_comment=(SELECT COUNT(*) FROM c_goods WHERE comment_id=%s)
                   WHERE comment_id=%s""",
                (comment_id, comment_id),
            )
            cursor.execute(
                "SELECT nice_comment FROM block_comment WHERE comment_id=%s", (comment_id,)
            )
            count = cursor.fetchone()["nice_comment"]
        connection.commit()
        return before > 0, count

    def nice_message(comment_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "UPDATE block_comment SET nice_comment=nice_comment+1 WHERE comment_id=%s",
                (comment_id,),
            )
            connection.commit()
            return {"ok": result}

    def nice_message_checker(member_id, message_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "INSERT INTO c_goods(member_id,comment_id) SELECT * FROM (SELECT %s,%s) AS tmp WHERE NOT exists (SELECT member_id,comment_id FROM c_goods WHERE member_id=%s AND comment_id=%s) LIMIT 1;",
                (member_id, message_id, member_id, message_id),
            )
            connection.commit()
            return result


DM_COLUMNS = "message_id, sender_id, recipient_id, content, image, sent_at, read_at"


class DirectMessage:
    """One-to-one chat messages (api/v1/chats.py). A conversation is a pair of members."""

    def send(sender_id, recipient_id, content, now, image=None):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO direct_message (sender_id, recipient_id, content, image, sent_at)"
                " VALUES (%s, %s, %s, %s, %s)",
                (sender_id, recipient_id, content, image, now),
            )
            message_id = cursor.lastrowid
            connection.commit()
            cursor.execute(
                f"SELECT {DM_COLUMNS} FROM direct_message WHERE message_id=%s",  # noqa: S608 - constant columns
                (message_id,),
            )
            return cursor.fetchone()

    def history(me, other, before=None, limit=30):
        """Up to `limit` messages between two members older than message `before`
        (the newest when None), oldest first."""
        before_sql = "AND message_id < %s" if before else ""
        extra = (before,) if before else ()
        args = (me, other, *extra, other, me, *extra)
        with connection.cursor() as cursor:
            # Two index range scans (one per direction) instead of an OR over both.
            cursor.execute(
                f"""(SELECT {DM_COLUMNS} FROM direct_message
                     WHERE sender_id=%s AND recipient_id=%s {before_sql}
                     ORDER BY message_id DESC LIMIT {int(limit)})
                   UNION ALL
                   (SELECT {DM_COLUMNS} FROM direct_message
                     WHERE sender_id=%s AND recipient_id=%s {before_sql}
                     ORDER BY message_id DESC LIMIT {int(limit)})
                   ORDER BY message_id DESC LIMIT {int(limit)}""",  # noqa: S608 - no user input
                args,
            )
            rows = list(cursor.fetchall())  # an empty result is a tuple
        rows.reverse()
        return rows

    def conversations(me, limit=50):
        """My conversations, newest first: the partner, the last message and how many
        of theirs I have not read."""
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT m.message_id, m.sender_id, m.recipient_id, m.content, m.image, m.sent_at,
                          m.read_at, p.member_id AS partner_id, p.account AS partner,
                          (SELECT COUNT(*) FROM direct_message u
                           WHERE u.recipient_id=%s AND u.sender_id=p.member_id
                             AND u.read_at IS NULL) AS unread
                   FROM (
                     SELECT partner_id, MAX(message_id) AS last_id FROM (
                       SELECT recipient_id AS partner_id, message_id FROM direct_message
                        WHERE sender_id=%s
                       UNION ALL
                       SELECT sender_id AS partner_id, message_id FROM direct_message
                        WHERE recipient_id=%s
                     ) mine GROUP BY partner_id
                   ) last
                   JOIN direct_message m ON m.message_id = last.last_id
                   JOIN member p ON p.member_id = last.partner_id
                   WHERE NOT EXISTS (SELECT 1 FROM member_block b
                                     WHERE b.blocker_id=%s AND b.blocked_id=p.member_id)
                   ORDER BY m.message_id DESC LIMIT {int(limit)}""",  # noqa: S608 - no user input
                (me, me, me, me),
            )
            return cursor.fetchall()

    def mark_read(me, sender_id, up_to, now):
        """Marks what `sender_id` sent me, up to message `up_to`, as read; returns how many."""
        with connection.cursor() as cursor:
            count = cursor.execute(
                """UPDATE direct_message SET read_at=%s
                   WHERE recipient_id=%s AND sender_id=%s AND read_at IS NULL
                     AND message_id <= %s""",
                (now, me, sender_id, up_to),
            )
        connection.commit()
        return count

    def unread_count(me):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS n FROM direct_message WHERE recipient_id=%s AND read_at IS NULL",
                (me,),
            )
            return cursor.fetchone()["n"]

    def may_see_image(member_id, key):
        """Whether a chat photo was sent to or by this member."""
        with connection.cursor() as cursor:
            got = cursor.execute(
                """SELECT 1 FROM direct_message WHERE image=%s
                   AND (sender_id=%s OR recipient_id=%s) LIMIT 1""",
                (key, member_id, member_id),
            )
        return got != 0

    def image_used(key):
        with connection.cursor() as cursor:
            return (
                cursor.execute("SELECT 1 FROM direct_message WHERE image=%s LIMIT 1", (key,)) != 0
            )

    def sent_since(sender_id, since):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS n FROM direct_message WHERE sender_id=%s AND sent_at >= %s",
                (sender_id, since),
            )
            return cursor.fetchone()["n"]


class MemberBlock:
    """Members I blocked: I no longer see their posts or comments, and neither of us can
    message, befriend or notify the other (api/v1/blocks.py)."""

    def block(blocker_id, blocked_id, now):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT IGNORE INTO member_block (blocker_id, blocked_id, created_at)"
                " VALUES (%s, %s, %s)",
                (blocker_id, blocked_id, now),
            )
            # Friendship and pending invitations end either way.
            cursor.execute(
                """DELETE FROM friendship WHERE (request_from=%s AND request_to=%s)
                   OR (request_from=%s AND request_to=%s)""",
                (blocker_id, blocked_id, blocked_id, blocker_id),
            )
        connection.commit()

    def unblock(blocker_id, blocked_id):
        with connection.cursor() as cursor:
            count = cursor.execute(
                "DELETE FROM member_block WHERE blocker_id=%s AND blocked_id=%s",
                (blocker_id, blocked_id),
            )
        connection.commit()
        return count

    def blocked_by(blocker_id):
        """The members I blocked, most recent first."""
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT m.member_id, m.account, b.created_at FROM member_block b
                   JOIN member m ON m.member_id = b.blocked_id
                   WHERE b.blocker_id=%s ORDER BY b.created_at DESC""",
                (blocker_id,),
            )
            return list(cursor.fetchall())

    def has_blocked(blocker_id, blocked_id):
        with connection.cursor() as cursor:
            got = cursor.execute(
                "SELECT 1 FROM member_block WHERE blocker_id=%s AND blocked_id=%s",
                (blocker_id, blocked_id),
            )
        return got != 0

    def between(member_a, member_b):
        """Whether either member blocked the other."""
        with connection.cursor() as cursor:
            got = cursor.execute(
                """SELECT 1 FROM member_block WHERE (blocker_id=%s AND blocked_id=%s)
                   OR (blocker_id=%s AND blocked_id=%s)""",
                (member_a, member_b, member_b, member_a),
            )
        return got != 0


REPORT_COLUMNS = """r.report_id, r.target_type, r.target_id, r.target_member_id,
    t.account AS target_account, r.reporter_id, rp.account AS reporter, r.reason, r.detail,
    r.weight, r.snapshot, r.created_at, r.status, r.handled_at"""


class Report:
    """Reports of posts, comments, members and chat messages (api/v1/reports.py)."""

    def create(report):
        """Stores a report; returns its id, or None if this member already reported it."""
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    """INSERT INTO report (reporter_id, target_type, target_id, target_member_id,
                         reason, detail, weight, snapshot, created_at)
                       VALUES (%(reporter_id)s, %(target_type)s, %(target_id)s,
                         %(target_member_id)s, %(reason)s, %(detail)s, %(weight)s,
                         %(snapshot)s, %(created_at)s)""",
                    report,
                )
            except pymysql.err.IntegrityError:
                return None
            report_id = cursor.lastrowid
        connection.commit()
        return report_id

    def open_weight(target_type, target_id):
        """How much the open reports on something weigh together."""
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT COALESCE(SUM(weight), 0) AS w FROM report
                   WHERE target_type=%s AND target_id=%s AND status='open'""",
                (target_type, target_id),
            )
            return int(cursor.fetchone()["w"])

    def made_since(reporter_id, since):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS n FROM report WHERE reporter_id=%s AND created_at >= %s",
                (reporter_id, since),
            )
            return cursor.fetchone()["n"]

    def listing(status, limit=100):
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT {REPORT_COLUMNS} FROM report r
                    JOIN member rp ON rp.member_id = r.reporter_id
                    LEFT JOIN member t ON t.member_id = r.target_member_id
                    WHERE r.status=%s ORDER BY r.report_id DESC LIMIT {int(limit)}""",  # noqa: S608 - constant columns
                (status,),
            )
            return list(cursor.fetchall())

    def get(report_id):
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT {REPORT_COLUMNS} FROM report r
                    JOIN member rp ON rp.member_id = r.reporter_id
                    LEFT JOIN member t ON t.member_id = r.target_member_id
                    WHERE r.report_id=%s""",  # noqa: S608 - constant columns
                (report_id,),
            )
            return cursor.fetchone()

    def close_all(target_type, target_id, status, now):
        """Closes every open report on the same thing (resolved or dismissed)."""
        with connection.cursor() as cursor:
            count = cursor.execute(
                """UPDATE report SET status=%s, handled_at=%s
                   WHERE target_type=%s AND target_id=%s AND status='open'""",
                (status, now, target_type, target_id),
            )
        connection.commit()
        return count

    def open_count():
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS n FROM report WHERE status='open'")
            return cursor.fetchone()["n"]


class Moderation:
    """What a report can point at, and what the owner can do about it."""

    def post(block_id):
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT block_id, member_id, content_type, content, block_img, hidden
                   FROM block WHERE block_id=%s""",
                (block_id,),
            )
            return cursor.fetchone()

    def comment(comment_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT comment_id, block_id, member_id, content FROM block_comment"
                " WHERE comment_id=%s",
                (comment_id,),
            )
            return cursor.fetchone()

    def message(message_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT message_id, sender_id, recipient_id, content, image FROM direct_message"
                " WHERE message_id=%s",
                (message_id,),
            )
            return cursor.fetchone()

    def set_hidden(block_id, hidden):
        with connection.cursor() as cursor:
            cursor.execute("UPDATE block SET hidden=%s WHERE block_id=%s", (int(hidden), block_id))
        connection.commit()

    def remove(target_type, target_id):
        """Deletes a post, comment or message; returns the post's image key to remove."""
        table, key = {
            "post": ("block", "block_id"),
            "comment": ("block_comment", "comment_id"),
            "message": ("direct_message", "message_id"),
        }[target_type]
        image = None
        with connection.cursor() as cursor:
            if target_type == "post":
                cursor.execute("SELECT block_img FROM block WHERE block_id=%s", (target_id,))
                row = cursor.fetchone()
                image = row and row["block_img"]
            if target_type == "message":
                cursor.execute("SELECT image FROM direct_message WHERE message_id=%s", (target_id,))
                row = cursor.fetchone()
                image = row and row["image"]
            count = cursor.execute(f"DELETE FROM {table} WHERE {key}=%s", (target_id,))  # noqa: S608 - fixed names
        connection.commit()
        return count, image


class Images:
    def has_avatar(member_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT member_img FROM member WHERE member_id=%s", (member_id,))
            row = cursor.fetchone()
        return bool(row and row["member_img"])

    def has_block_image(block_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT block_img FROM block WHERE block_id=%s", (block_id,))
            row = cursor.fetchone()
        return bool(row and row["block_img"])

    def post_image(member_id, filename):
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE member SET member_img=%s WHERE member_id=%s", (filename, member_id)
                )
            connection.commit()
            return "ok"
        except Exception as e:
            print(e)
            return "upload error"


class Notification:
    def get_notifi(member_id):
        try:
            with connection.cursor() as cursor:
                result = cursor.execute("SELECT * FROM notifi WHERE reciever_id=%s", (member_id,))
            data = cursor.fetchall()
            connection.commit()
            return {"ok": "Notification GET", "data": data, "count": result}
        except Exception as e:
            print(e)
            return {"error": "GET notifi error"}

    def post_notifi(me, who, content, time):
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                INSERT INTO notifi(
                    sender_id,
                    reciever_id,
                    content,
                    send_time
                )VALUES(%s,(SELECT member_id FROM member WHERE account=%s),%s,%s)""",
                    (me, who, content, time),
                )
            connection.commit()
            return {"ok": "Notification send"}
        except Exception as e:
            print(e)
            return {"error": "post notifi error"}

    def patch_notifi(member_id):
        return None

    def delete_notifi(member_id):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM notifi WHERE reciever_id=%s", (member_id,))
            connection.commit()
            return {"ok": "notifi read"}


class Vote_table:
    def get_vote(block_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM vote_options WHERE block_id=%s", (block_id,))
            data = cursor.fetchall()
            connection.commit()
        return data

    def create_vote(block_id, votes):
        try:
            with connection.cursor() as cursor:
                for vote in votes:
                    cursor.execute(
                        """
                    INSERT INTO vote_options(
                        block_id,
                        option_name
                    )VALUES(%s,%s)""",
                        (block_id, vote),
                    )
                cursor.execute("SELECT * FROM vote_options WHERE block_id=%s", (block_id,))
                data = cursor.fetchall()
                connection.commit()
            return {"msg": data}
        except Exception as e:
            print(e)
            return {"msg": "vote create error"}

    def summary(member_id, block_ids):
        """Poll options of several posts with their vote counts and whether I chose them."""
        if not block_ids:
            return {}
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT o.vote_option_id, o.block_id, o.option_name,
                    COUNT(v.vote_id) AS count, COALESCE(MAX(v.member_id=%s), 0) AS mine
                FROM vote_options o LEFT JOIN votes v ON v.vote_option_id=o.vote_option_id
                WHERE o.block_id IN ({_in(block_ids)})
                GROUP BY o.vote_option_id, o.block_id, o.option_name
                ORDER BY o.vote_option_id""",  # noqa: S608 - placeholders only
                (member_id, *block_ids),
            )
            rows = cursor.fetchall()
        polls = {block_id: [] for block_id in block_ids}
        for row in rows:
            row["mine"] = bool(row["mine"])
            polls[row["block_id"]].append(row)
        return polls


class Vote:
    def check_vote(member_id, block_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "SELECT * FROM votes where member_id=%s and vote_option_id IN (SELECT vote_option_id FROM vote_options WHERE block_id=%s)",
                (member_id, block_id),
            )
            data = cursor.fetchone()
            connection.commit()
        return {"count": result, "data": data}

    def do_vote(member_id, vote_option_id, block_id):
        # The option must belong to the post checked by check_vote, or a member could
        # vote again by pairing an option with some other post's id.
        with connection.cursor() as cursor:
            result = cursor.execute(
                """INSERT INTO votes(member_id, vote_option_id)
                SELECT %s, vote_option_id FROM vote_options WHERE vote_option_id=%s AND block_id=%s""",
                (member_id, vote_option_id, block_id),
            )
            connection.commit()
        if not result:
            return {"error": "no such option on this post"}
        return {"ok": True}

    def get_vote(block_id):
        with connection.cursor() as cursor:
            cursor.execute(
                """
            SELECT * FROM votes WHERE vote_option_id IN (SELECT vote_option_id FROM vote_options WHERE block_id=%s)
            """,
                (block_id,),
            )
            data = cursor.fetchall()
            connection.commit()
        return data

    def change_vote():
        return

    def del_vote():
        return


class Tag_info:
    def get_tag_info(tag_name):
        with connection.cursor() as cursor:
            cursor.execute(
                """
            SELECT brick_id,(SELECT account FROM member WHERE member.member_id=bricks.member_id)AS account,tag_id,title,classifi,popularity,feedbacks,time FROM bricks WHERE tag_id=(SELECT tag_id FROM tag WHERE name=%s) ORDER BY time DESC
            """,
                (tag_name,),
            )
            data = cursor.fetchall()
            connection.commit()
        return data

    def post_tag_info(data):
        with connection.cursor() as cursor:
            result = cursor.execute(
                """INSERT INTO bricks(
                member_id,
                tag_id,
                title,
                content,
                classifi,
                time
            )VALUES(%s,(SELECT tag_id FROM tag WHERE name=%s),%s,%s,%s,%s)
            """,
                (
                    data["member_id"],
                    data["tag_name"],
                    data["title"],
                    data["content"],
                    data["classifi"],
                    data["time"],
                ),
            )
            connection.commit()
        return result

    def modify_tag_info(brick_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "UPDATE bricks SET popularity=popularity+1 WHERE brick_id=%s", (brick_id,)
            )
            connection.commit()
            return result


class Level:
    """Exp bookkeeping for module/levels.py, which decides who gets what.

    Exp is awarded by the server for actions it has already verified, never by
    client-sent amounts."""

    def count_today(member_id, action, day):
        """Counts one more `action` today and returns today's count, this one included."""
        with connection.cursor() as cursor:
            cursor.execute(
                """INSERT INTO exp_daily (member_id, day, action, count) VALUES (%s, %s, %s, 1)
                   ON DUPLICATE KEY UPDATE count = count + 1""",
                (member_id, day, action),
            )
            cursor.execute(
                "SELECT count FROM exp_daily WHERE member_id=%s AND day=%s AND action=%s",
                (member_id, day, action),
            )
            count = cursor.fetchone()["count"]
        connection.commit()
        return count

    def add_exp(member_id, exp):
        """Adds exp; returns (exp before, exp after, account)."""
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT exp, account FROM member WHERE member_id=%s FOR UPDATE", (member_id,)
            )
            row = cursor.fetchone()
            before = row["exp"] or 0
            cursor.execute("UPDATE member SET exp=%s WHERE member_id=%s", (before + exp, member_id))
        connection.commit()
        return before, before + exp, row["account"]

    def last_visit(member_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT last_active_day, streak FROM member WHERE member_id=%s", (member_id,)
            )
            row = cursor.fetchone()
        return (row["last_active_day"], row["streak"] or 0) if row else (None, 0)

    def set_visit(member_id, day, streak):
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE member SET last_active_day=%s, streak=%s WHERE member_id=%s",
                (day, streak, member_id),
            )
        connection.commit()

    def exps(member_ids):
        """{member_id: exp} for several members, for level badges."""
        ids = [i for i in set(member_ids) if i]
        if not ids:
            return {}
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT member_id, exp FROM member WHERE member_id IN ({_in(ids)})",  # noqa: S608 - placeholders only
                ids,
            )
            return {row["member_id"]: row["exp"] or 0 for row in cursor.fetchall()}

    def posts_since(member_id, since):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS n FROM block WHERE member_id=%s AND build_time >= %s",
                (member_id, since),
            )
            return cursor.fetchone()["n"]

    def purge(before):
        """Daily counts only matter for today."""
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM exp_daily WHERE day < %s", (before,))
        connection.commit()


class Bricks:
    def getting_brick(brick_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT brick_id,(SELECT account FROM member WHERE bricks.member_id=member.member_id)AS account,tag_id,title,content,classifi,feedbacks,popularity,time FROM bricks WHERE brick_id=%s",
                (brick_id,),
            )
            result = cursor.fetchall()
            connection.commit()
        return result

    def getting_brick_discuss(brick_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT (SELECT account FROM member WHERE member.member_id=brick_discuss.member_id)AS account,content,time FROM brick_discuss WHERE brick_id=%s ORDER BY time DESC",
                (brick_id,),
            )
            datas = cursor.fetchall()
            connection.commit()
            return datas

    def posting_brick_discuss(datas):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "INSERT INTO brick_discuss(member_id,brick_id,content,time)VALUES(%s,%s,%s,%s)",
                (datas["member_id"], datas["brick_id"], datas["content"], datas["time"]),
            )
            connection.commit()
            return result

    def patching_brick_discuss(brick_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "UPDATE bricks SET feedbacks=feedbacks+1 WHERE brick_id=%s", (brick_id,)
            )
            connection.commit()
            return result
