from flask import request, session

from data.data import Block, Vote, Vote_table
from module import rules
from module.auth import login_required

from . import api_vote


def poll(member_id, block_id):
    """Counts per option and which one I chose; never who voted for what."""
    return Vote_table.summary(member_id, [block_id])[block_id]


@api_vote.route("/api/vote", methods=["GET"])
@login_required
def checking_vote_result():
    member_id = session.get("member_id")
    block_id = rules.integer(request.args.get("block_id"))
    if block_id is None or not Block.visible(member_id, block_id):
        return {"error": "block not found or not yours"}, 404
    return {"ok": True, "data": poll(member_id, block_id)}


@api_vote.route("/api/vote", methods=["POST"])
@login_required
def doing_vote():
    data = request.get_json(silent=True) or {}
    member_id = session.get("member_id")
    vote_option_id = rules.integer(data.get("vote_option_id"))
    block_id = rules.integer(data.get("block_id"))
    if block_id is None or vote_option_id is None or not Block.visible(member_id, block_id):
        return {"error": "block not found or not yours"}, 404
    check = Vote.check_vote(member_id, block_id)
    if check["count"] != 0:
        return {"error": "You have voted before!", "data": poll(member_id, block_id)}
    result = Vote.do_vote(member_id, vote_option_id, block_id)
    if result.get("ok"):
        result["data"] = poll(member_id, block_id)
    return result
