from flask import request, session

from data.data import Level, Tag_info
from module import levels, rules
from module.auth import login_required, verified_required
from module.clock import taipei_now

from . import api_tag_page


@api_tag_page.route("/api/tag_page", methods=["GET"])
@login_required
def get_tag_datas():
    key = request.args.get("keyword")
    result = Tag_info.get_tag_info(key)
    return {"ok": "Fetch success", "data": result}


@api_tag_page.route("/api/tag_page", methods=["POST"])
@verified_required
def post_discuss():
    data = request.get_json(silent=True) or {}
    member_id = session.get("member_id")
    if levels.level_of(Level.exps([member_id]).get(member_id)) < levels.TOPICS_LEVEL:
        return {
            "error": f"升到 Lv {levels.TOPICS_LEVEL} 就能發起討論，先去發文、留言累積經驗值吧"
        }, 403
    title = rules.text(data.get("title"), rules.TOPIC_TITLE_MAX)
    content = rules.text(data.get("content"), rules.TOPIC_MAX)
    if title is None or content is None:
        return {"error": "請填寫標題和內容"}, 400
    classifi = data.get("classifi") if data.get("classifi") in {"閒聊", "問題", "其他"} else "閒聊"
    result = Tag_info.post_tag_info(
        {
            "member_id": session.get("member_id"),
            "tag_name": data.get("tag_name"),
            "title": title,
            "content": content,
            "classifi": classifi,
            "time": taipei_now(),
        }
    )
    if result != 1:
        return {"error": "tag post fail"}
    return {"ok": "tag post success"}


@api_tag_page.route("/api/tag_page", methods=["PATCH"])
@login_required
def modify_discuss():
    data = request.get_json()
    brick_id = data["brick_id"]
    result = Tag_info.modify_tag_info(brick_id)
    if result != 1:
        return {"error": "tag modify fail"}
    return {"ok": "tag modify success"}
