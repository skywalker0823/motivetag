
from flask import request, session
from . import api_vote
from data.data import Vote


@api_vote.route("/api/vote", methods=["GET"])
def checking_vote_result():
    block_id = request.args.get("block_id")
    result = Vote.get_vote(block_id)
    return {"ok": True, "data": result}


@api_vote.route("/api/vote", methods=["POST"])
def doing_vote():
    data = request.get_json()
    member_id = session.get("member_id")
    vote_option_id = data["vote_option_id"]
    block_id = data["block_id"]
    check = Vote.check_vote(member_id, block_id)
    if check["count"] != 0:
        return {"error": "You have voted before!", "data": check["data"]}
    result = Vote.do_vote(member_id, vote_option_id)
    return result
