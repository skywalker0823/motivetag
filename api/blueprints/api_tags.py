from data.data import Member_tags,Tag
from flask import request, session
from . import api_tags


@api_tags.route("/api/member_tags", methods=["GET"])
def get_tags():
    member_id = session.get("member_id")
    tag = request.args.get("tag")
    result = Member_tags.getting_member_tags(member_id)
    return {"ok":True,"tag":result["all_tags"]}


@api_tags.route("/api/find_member_tags", methods=["GET"])
def check_tags():
    member_id = session.get("member_id")
    tag = request.args.get("tag")
    result = Member_tags.find_member_tags(member_id,tag)
    if result != 0:
        return {"error":"already have this tag"}
    return {"ok": True}


@api_tags.route("/api/member_tags", methods=["PATCH"])
def append_tags():
    data = request.get_json()
    member_id = session.get("member_id")
    tag = data["tag"]
    result = Member_tags.add_member_tag(member_id, tag)
    if result["result"] == 0:
        return {"error": "already have this tag"}
    return {"ok": True,"member_tag_id":result["data"]["member_tag_id"],"tag":tag}


@api_tags.route("/api/member_tags", methods=["DELETE"])
def del_tags():
    data = request.get_json()
    member_tag_id = data["tag"]
    member_id = session.get("member_id")
    result = Member_tags.del_member_tag(member_id,member_tag_id)
    if result["ok"] and result["count"]==1:
        return {"ok": True}
    return {"error":"Deletion on tag fail or no data"}




@api_tags.route("/api/tag", methods=["GET"])
def get_tags_global():
    result = Tag.getting_tags_global()
    return {"ok": True, "hot_tags": result}


@api_tags.route("/api/tag", methods=["PATCH"])
def upgrade_global_tag():
    data = request.get_json()
    tag = data["tag"]
    member_id = session.get("member_id")
    tag_global_update = Tag.upping_global_tag(tag, member_id)
    return {"msg": tag_global_update}


@api_tags.route("/api/tag", methods=["DELETE"])
def down_tag():
    data = request.get_json()
    tag = data["tag"]
    tag_update = Tag.downing_global_tag(tag)
    if(tag_update==1):
        return {"ok":tag_update}
    return {"error":"dowing failed"}



