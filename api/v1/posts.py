from flask import request, session

from api.blueprints.api_blocks import with_extras
from data.data import Block, Message
from module import levels, rules

from . import error, login_required, v1


@v1.route("/posts/explore", methods=["GET"])
@login_required
def explore():
    """Everyone's newest public and anonymous posts, for members whose own feed is quiet.

    Same post shape as GET /api/blocks; page with ?offset=<posts already shown>.
    """
    offset = rules.integer(request.args.get("offset", "0"))
    if offset is None or offset < 0:
        return error("bad_offset", "offset 需為 0 以上的整數", 400)
    posts = Block.explore(offset, session["member_id"])
    return {"data": with_extras(posts, session["member_id"])}


REACTIONS = {"like", "dislike", None}


@v1.route("/posts/<int:block_id>/reaction", methods=["PUT"])
@login_required
def react(block_id):
    """{reaction: "like" | "dislike" | null}: one of 讚 and 爛 at most; null takes it back.

    Answers {data: {reaction, good, bad}}. A like earns exp once per post a day, so
    tapping it on and off earns nothing more.
    """
    reaction = (request.get_json(silent=True) or {}).get("reaction")
    if reaction not in REACTIONS:
        return error("bad_reaction", "reaction 需為 like、dislike 或 null", 400)
    me = session["member_id"]
    if not Block.visible(me, block_id):
        return error("not_found", "找不到這篇貼文", 404)
    previous, good, bad = Block.set_reaction(me, block_id, reaction)
    if reaction == "like" and previous != "like" and levels.once_today(me, f"like:{block_id}"):
        levels.award(me, "like_given")
        author = Block.author(block_id)
        if author != me:
            levels.award(author, "like_received")
    return {"data": {"reaction": reaction, "good": good, "bad": bad}}


@v1.route("/comments/<int:comment_id>/like", methods=["PUT"])
@login_required
def like_comment(comment_id):
    """{liked: true | false} → {data: {liked, likes}}; a second tap takes the like back."""
    liked = (request.get_json(silent=True) or {}).get("liked")
    if not isinstance(liked, bool):
        return error("bad_liked", "liked 需為 true 或 false", 400)
    me = session["member_id"]
    comment = Message.comment(comment_id)
    if not comment or not Block.visible(me, comment["block_id"]):
        return error("not_found", "找不到這則留言", 404)
    before, likes = Message.set_like(me, comment_id, liked)
    if liked and not before and levels.once_today(me, f"clike:{comment_id}"):
        levels.award(me, "like_given")
        if comment["member_id"] != me:
            levels.award(comment["member_id"], "comment_like_received")
    return {"data": {"liked": liked, "likes": likes}}
