import traceback

from flask import request, session

from data.data import Block, Block_tags, Level, Message, Vote_table
from module import rules, tag_filter
from module.auth import login_required
from module.clock import taipei_now

from . import api_blocks


def with_extras(posts, member_id):
    """Adds tags, comments, poll results and my reactions, so the feed needs one request."""
    ids = [post["block_id"] for post in posts]
    comments = Message.for_blocks(member_id, ids)
    polls = Vote_table.summary(member_id, ids)
    liked, disliked = Block.my_reactions(member_id, ids)
    for post in posts:
        # Anonymous posts hide their author from everyone but the author.
        if post["content_type"] == "Anonymous" and post["member_id"] != member_id:
            post["account"] = None
            post["member_id"] = None
        post["tags"] = tag_filter.filter(post["content"])
        if post["content_type"] == "Anonymous":
            post["tags"].append("Anonymous")
        post["comments"] = comments.get(post["block_id"], [])
        post["votes"] = polls.get(post["block_id"], [])
        post["liked"] = post["block_id"] in liked
        post["disliked"] = post["block_id"] in disliked
    return posts


@api_blocks.route("/api/blocks", methods=["GET"])
@login_required
def check_blocks():
    page = rules.integer(request.args.get("page")) or 0
    key = request.args.get("key")
    member_id = session.get("member_id")
    result = Block.get_block(member_id, max(page, 0), key)
    if result["msg"] == "No blocks found":
        return {"error": "No Blocks"}
    if result["msg"] == "ok":
        return {"ok": True, "data": with_extras(result["datas"], member_id)}
    return {"error": True, "msg": result["msg"]}


def post_error(block):
    if block.get("type") == "Normal":  # the 2022 frontend's name for a public post
        block["type"] = "PUBLIC"
    if block.get("type") not in rules.POST_TYPES:
        return "unknown post type"
    if not rules.text(block.get("content"), rules.POST_MAX):
        return f"貼文需為 1–{rules.POST_MAX} 個字"
    options = block.get("vote_box") or []
    if not isinstance(options, list):
        return "投票選項格式不正確"
    if options and not rules.POLL_MIN <= len(options) <= rules.POLL_MAX:
        return f"投票需要 {rules.POLL_MIN}–{rules.POLL_MAX} 個選項"
    if any(not rules.text(option, rules.POLL_OPTION_MAX) for option in options):
        return f"每個投票選項需為 1–{rules.POLL_OPTION_MAX} 個字"
    return None


@api_blocks.route("/api/blocks", methods=["POST"])
@login_required
def build_blocks():
    block = request.get_json(silent=True) or {}
    error = post_error(block)
    if error:
        return {"error": error}, 400
    member_id = session.get("member_id")
    block["content"] = block["content"].strip()
    block["time"] = taipei_now()
    tags = tag_filter.filter(block["content"])
    if block["type"] == "Anonymous" and "Anonymous" not in tags:
        tags.append("Anonymous")
    result = Block.create_my_block(member_id, block)
    if result["msg"] != "ok":
        return {"error": "發文失敗，請稍後再試"}, 500
    post = result["content"]
    Block_tags.tag_into_block(tags, post["block_id"], member_id)
    options = [option.strip() for option in block.get("vote_box") or []]
    if options:
        Vote_table.create_vote(post["block_id"], options)
    Level.reward(member_id, "block_creater")
    return {"ok": True, "data": with_extras([post], member_id)}


def react(checker, counter, error_before):
    try:
        data = request.get_json(silent=True) or {}
        block_id = rules.integer(data.get("block_id"))
        member_id = session.get("member_id")
        if block_id is None or not Block.visible(member_id, block_id):
            return {"error": "block not found or not yours"}, 404
        if checker(member_id, block_id) == 0:
            return {"error": error_before}
        result = counter(block_id)
        Level.reward(member_id, "good_bad")
        return result
    except Exception as e:
        print("type error: " + str(e))
        print(traceback.format_exc())
        return {"error": True, "msg": "block reaction error"}


@api_blocks.route("/api/blocks", methods=["PATCH"])
@login_required
def gooding_blocks():
    return react(Block.good_block_checker, Block.good_block, "you pressed this good before")


@api_blocks.route("/api/blocks", methods=["PUT"])
@login_required
def bading_blocks():
    return react(Block.bad_block_checker, Block.bad_block, "you pressed this boo before")


@api_blocks.route("/api/blocks", methods=["DELETE"])
@login_required
def delete_blocks():
    try:
        data = request.get_json()
        block_id = data["block_id"]
        member_id = session.get("member_id")
        if Block.delete_block(member_id, block_id) != 1:
            return {"error": True, "msg": "block not found or not yours"}, 403
        Level.reward(member_id, "block_destroy")
        return {"ok": True, "msg": str(block_id) + " delete complete"}
    except Exception as e:
        print("type error: " + str(e))
        print(traceback.format_exc())
        return {"error": True, "msg": "block delete error"}
