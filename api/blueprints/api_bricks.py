from flask import request, session
from . import api_bricks
from data.data import Bricks


@api_bricks.route("/api/bricks",methods=["GET"])
def get_brick():
    brick_id = request.args.get("brick_id")
    data = Bricks.getting_brick(brick_id)
    return {"ok":True,"data":data}


@api_bricks.route("/api/get_brick_discuss",methods=["GET"])
def get_discuss():
    brick_id = request.args.get("brick_id")
    datas = Bricks.getting_brick_discuss(brick_id)
    return {"ok":True,"data":datas}


@api_bricks.route("/api/bricks", methods=["POST"])
def post_brick_discuss():
    data = request.get_json()
    data["member_id"] = session.get("member_id")
    data["account"] = session.get("account")
    result = Bricks.posting_brick_discuss(data)
    if result==1:
        patch = Bricks.patching_brick_discuss(data["brick_id"])
        if patch==1:
            return {"ok":True,"datas":data}
        return {"error":"patch brick fail"}
    return {"error":"post brick fail"}
