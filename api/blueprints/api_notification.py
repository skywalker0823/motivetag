from flask import request, session

from data.data import Notification
from module.auth import login_required

from . import api_notification


@api_notification.route("/api/notifi", methods=["GET"])
def getting_notifi():
    member_id = session.get("member_id")
    if member_id is None:
        return {"error": "Please reload to get notifi"}
    result = Notification.get_notifi(member_id)
    return result


@api_notification.route("/api/notifi", methods=["POST"])
@login_required
def posting_notifi():
    data = request.get_json()
    me = session.get("member_id")
    who = data["who"]
    time = data["time"]
    content = data["content"]
    result = Notification.post_notifi(me, who, content, time)
    return result


@api_notification.route("/api/notifi", methods=["DELETE"])
@login_required
def reading_notifi():
    member_id = session.get("member_id")
    result = Notification.delete_notifi(member_id)
    return result
