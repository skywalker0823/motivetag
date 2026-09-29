from flask import request, session

from data.data import Block, Message
from module import levels, rules
from module.auth import login_required, verified_required
from module.clock import taipei_now

from . import api_message


@api_message.route("/api/message", methods=["GET"])
@login_required
def getting_message():
    block_id = rules.integer(request.args.get("block_id"))
    member_id = session.get("member_id")
    if block_id is None or not Block.visible(member_id, block_id):
        return {"error": "block not found or not yours"}, 404
    comments = Message.for_blocks(member_id, [block_id])[block_id]
    for comment in comments:
        comment["level"] = levels.level_of(comment.pop("exp", 0))
    return {"ok": comments}


@api_message.route("/api/message", methods=["POST"])
@verified_required
def posting_message():
    data = request.get_json(silent=True) or {}
    member_id = session.get("member_id")
    block_id = rules.integer(data.get("block_id"))
    content = rules.text(data.get("message"), rules.COMMENT_MAX)
    score = rules.integer(data.get("score", 0))
    if content is None:
        return {"error": f"留言需為 1–{rules.COMMENT_MAX} 個字"}, 400
    if score is None or not rules.SCORE_MIN <= score <= rules.SCORE_MAX:
        return {"error": f"評分需在 {rules.SCORE_MIN} 到 {rules.SCORE_MAX} 之間"}, 400
    if block_id is None or not Block.visible(member_id, block_id):
        return {"error": "block not found or not yours"}, 404
    time = taipei_now()
    result = Message.post_message(
        member_id, {"block_id": block_id, "message": content, "time": time, "score": score}
    )
    if "ok" in result:
        levels.award(member_id, "comment")
        author = Block.author(block_id)
        if author != member_id:
            levels.award(author, "comment_received")
        result["comment"] = {
            "comment_id": result["ok"]["LAST_INSERT_ID()"],
            "block_id": block_id,
            "member_id": member_id,
            "account": session.get("account"),
            "content": content,
            "build_time": time,
            "nice_comment": 0,
            "given_score": score,
            "liked": False,
        }
    result["account"] = session.get("account")
    result["member_id"] = member_id
    return result


@api_message.route("/api/message", methods=["PATCH"])
@login_required
def nice_message():
    data = request.get_json(silent=True) or {}
    message_id = rules.integer(data.get("message_id"))
    if message_id is None:
        return {"error": "comment not found"}, 404
    member_id = session.get("member_id")
    try:
        checker = Message.nice_message_checker(member_id, message_id)
    except Exception:
        return {"error": "comment not found"}, 404
    if checker == 0:
        return {"error": "you pressed this good message before"}
    result = Message.nice_message(message_id)
    levels.award(member_id, "like_given")
    author = Message.author(message_id)
    if author != member_id:
        levels.award(author, "comment_like_received")
    return result
