from flask import request, session

from data.data import Member_tags, Tag
from module import rules
from module.auth import login_required

from . import api_tags


@api_tags.route("/api/member_tags", methods=["GET"])
@login_required
def get_tags():
    member_id = session.get("member_id")
    result = Member_tags.getting_member_tags(member_id)
    return {"ok": True, "tag": result["all_tags"]}


@api_tags.route("/api/find_member_tags", methods=["GET"])
@login_required
def check_tags():
    member_id = session.get("member_id")
    tag = request.args.get("tag")
    result = Member_tags.find_member_tags(member_id, tag)
    if result != 0:
        return {"error": "already have this tag"}
    return {"ok": True}


@api_tags.route("/api/member_tags", methods=["PATCH"])
@login_required
def append_tags():
    data = request.get_json(silent=True) or {}
    member_id = session.get("member_id")
    tag = data.get("tag").strip().lstrip("#") if isinstance(data.get("tag"), str) else ""
    if not rules.TAG_NAME.match(tag):
        return {"error": "標籤只能包含文字、數字或底線，最多 30 個字"}, 400
    result = Member_tags.add_member_tag(member_id, tag)
    if result["result"] == 0:
        return {"error": "already have this tag"}
    return {"ok": True, "member_tag_id": result["data"]["member_tag_id"], "tag": tag}


@api_tags.route("/api/member_tags", methods=["DELETE"])
@login_required
def del_tags():
    data = request.get_json()
    member_tag_id = data["tag"]
    member_id = session.get("member_id")
    result = Member_tags.del_member_tag(member_id, member_tag_id)
    if result["ok"] and result["count"] == 1:
        return {"ok": True}
    return {"error": "Deletion on tag fail or no data"}


@api_tags.route("/api/tag", methods=["GET"])
def get_tags_global():
    result = Tag.getting_tags_global()
    return {"ok": True, "hot_tags": result}
