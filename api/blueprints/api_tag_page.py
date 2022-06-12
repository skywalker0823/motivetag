
from flask import request,session
from . import api_tag_page
from data.data import Tag_info


@api_tag_page.route("/api/tag_page",methods=["GET"])
def get_tag_datas():
    key = request.args.get("keyword")
    result = Tag_info.get_tag_info(key)
    return {"ok":"Fetch success","data":result}


@api_tag_page.route("/api/tag_page",methods=["POST"])
def post_discuss():
    data = request.get_json()
    member_id = session.get("member_id")
    data["member_id"]=member_id
    result = Tag_info.post_tag_info(data)
    if result!=1:
        return {"error":"tag post fail"}
    return {"ok":"tag post success"}


@api_tag_page.route("/api/tag_page",methods=["PATCH"])
def modify_discuss():
    data = request.get_json()
    member_id = session.get("member_id")
    brick_id = data["brick_id"]
    result = Tag_info.modify_tag_info(brick_id)
    if result != 1:
        return {"error": "tag modify fail"}
    return {"ok": "tag modify success"}
