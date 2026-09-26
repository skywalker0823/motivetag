from flask import request, session

from data.data import Bricks
from module.auth import login_required

from . import api_bricks


@api_bricks.route("/api/bricks", methods=["GET"])
@login_required
def get_brick():
    brick_id = request.args.get("brick_id")
    data = Bricks.getting_brick(brick_id)
    return {"ok": True, "data": data}


@api_bricks.route("/api/get_brick_discuss", methods=["GET"])
@login_required
def get_discuss():
    brick_id = request.args.get("brick_id")
    datas = Bricks.getting_brick_discuss(brick_id)
    return {"ok": True, "data": datas}


@api_bricks.route("/api/bricks", methods=["POST"])
@login_required
def post_brick_discuss():
    data = request.get_json()
    data["member_id"] = session.get("member_id")
    data["account"] = session.get("account")
    result = Bricks.posting_brick_discuss(data)
    if result != 1:
        return {"error": "post brick fail"}
    patch = Bricks.patching_brick_discuss(data["brick_id"])
    if patch != 1:
        return {"error": "patch brick fail"}
    return {"ok": True, "datas": data}
