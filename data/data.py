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

        Returns the S3 keys of their images (avatar and post images) for the caller to
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
                   GROUP BY m.member_id, m.account, m.mood, m.last_signin
                   ORDER BY shared_count DESC, m.last_signin DESC
                   LIMIT %s""",  # noqa: S608 - placeholders only
                (member_id, *NEUTRAL_TAGS, member_id, member_id, limit),
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


class Block:
    def get_block(member_id, page, obseve_key=None, order_by=None):
        page = int(page)
        # sql_me=None
        # sql_by_score = None
        sql_observe_key = """SELECT account,block_id, block.member_id, content_type, content, build_time,good,bad,block_img
                                FROM block RIGHT JOIN member ON member.member_id=block.member_id
                                WHERE block_id IN(SELECT block_id FROM block_tag WHERE tag_id=(SELECT tag_id FROM tag WHERE name=%s))
                                AND (content_type <> "SECRET" OR block.member_id=%s)
                                ORDER BY build_time DESC LIMIT %s,%s"""
        sql_all = """SELECT account,block_id, block.member_id, content_type, content, build_time,good,bad,block_img
                                FROM block RIGHT JOIN member ON member.member_id=block.member_id
                                WHERE block.member_id IN
                                (
                                    SELECT request_from AS ids FROM friendship WHERE status="0" 
                                    AND(request_from=%s OR request_to=%s) 
                                    UNION
                                    SELECT request_to AS ids FROM friendship WHERE status="0" AND(request_from=%s OR request_to=%s)) AND content_type <> "SECRET" AND content_type <> "Anonymous"
                                    UNION
                                    SELECT (SELECT account FROM member WHERE member_id=block.member_id)AS account,block_id, block.member_id, content_type, content, build_time,good,bad,block_img FROM block WHERE member_id=%s
                                    UNION
                                    SELECT (SELECT account FROM member WHERE member_id=block.member_id)AS account,block_id,block.member_id,content_type,content,build_time,good,bad,block_img FROM block WHERE block_id IN(SELECT block_id FROM block_tag WHERE tag_id IN(SELECT tag_id FROM member_tags WHERE member_id=%s)
                                ) AND content_type <> "SECRET"
                                ORDER BY build_time DESC
                                LIMIT %s,%s"""
        with connection.cursor() as cursor:
            if obseve_key is None:
                got = cursor.execute(
                    sql_all,
                    (*[member_id] * 6, page, FEED_PAGE),
                )
                # got = cursor.execute(sql_all_altered, (member_id, member_id, member_id, member_id, member_id,member_id,page,5))
            else:
                got = cursor.execute(sql_observe_key, (obseve_key, member_id, page, FEED_PAGE))
            result = cursor.fetchall()
            connection.commit()
            if got == 0:
                return {"msg": "No blocks found"}
            return {"msg": "ok", "datas": result}

    def explore(offset):
        """Everyone's newest posts except secret ones; anonymous authors are hidden later."""
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT account, block_id, block.member_id, content_type, content, build_time,
                          good, bad, block_img
                   FROM block JOIN member ON member.member_id=block.member_id
                   WHERE content_type <> 'SECRET'
                   ORDER BY build_time DESC, block_id DESC LIMIT %s,%s""",
                (offset, FEED_PAGE),
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

    def good_block(block_id):
        with connection.cursor() as cursor:
            result = cursor.execute("UPDATE block SET good=good+1 WHERE block_id=%s", (block_id,))
            connection.commit()
            return {"ok": result}

    def good_block_checker(member_id, block_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "INSERT INTO goods(member_id,block_id) SELECT * FROM (SELECT %s,%s) AS tmp WHERE NOT exists (SELECT member_id,block_id FROM goods WHERE member_id=%s AND block_id=%s) LIMIT 1;",
                (member_id, block_id, member_id, block_id),
            )
            connection.commit()
            return result

    def bad_block(block_id):
        with connection.cursor() as cursor:
            result = cursor.execute("UPDATE block SET bad=bad+1 WHERE block_id=%s", (block_id,))
            connection.commit()
            return {"ok": result}

    def bad_block_checker(member_id, block_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "INSERT INTO bads(member_id,block_id) SELECT * FROM (SELECT %s,%s) AS tmp WHERE NOT exists (SELECT member_id,block_id FROM bads WHERE member_id=%s AND block_id=%s) LIMIT 1;",
                (member_id, block_id, member_id, block_id),
            )
            connection.commit()
            return result

    def visible(member_id, block_id):
        """Whether this member may see the post: it exists and is not someone else's secret."""
        with connection.cursor() as cursor:
            got = cursor.execute(
                "SELECT 1 FROM block WHERE block_id=%s AND (content_type<>'SECRET' OR member_id=%s)",
                (block_id, member_id),
            )
            return got != 0

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
        """Comments of several posts at once, oldest first, each with whether I liked it."""
        if not block_ids:
            return {}
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT c.comment_id, c.block_id, c.member_id, m.account, c.content,
                    c.build_time, c.nice_comment, c.given_score,
                    EXISTS(SELECT 1 FROM c_goods g
                           WHERE g.comment_id=c.comment_id AND g.member_id=%s) AS liked
                FROM block_comment c JOIN member m ON m.member_id=c.member_id
                WHERE c.block_id IN ({_in(block_ids)}) ORDER BY c.comment_id""",  # noqa: S608 - placeholders only
                (member_id, *block_ids),
            )
            rows = cursor.fetchall()
        comments = {block_id: [] for block_id in block_ids}
        for row in rows:
            row["liked"] = bool(row["liked"])
            comments[row["block_id"]].append(row)
        return comments

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
    def get_current_exp(member_id):
        return

    # Exp is awarded by the server for actions it has already verified, never by client-sent amounts.
    EXP_REWARDS = {
        "block_creater": 50,
        "block_destroy": -50,  # takes back the creation reward, so posting and deleting earns nothing
        "good_bad": 5,
        "good_message": 5,
        "message": 3,
    }

    def exp_up(member_id, exp):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "UPDATE member SET exp=exp+%s WHERE member_id=%s", (exp, member_id)
            )
            connection.commit()
        return result

    def reward(member_id, action):
        return Level.exp_up(member_id, Level.EXP_REWARDS[action])

    def exp_down(member_id, exp):
        return


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
