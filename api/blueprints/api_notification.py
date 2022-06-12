
from flask import request, session
from data.data import Notification
from . import api_notification


@api_notification.route("/api/notifi",methods=["GET"])
def getting_notifi():
    member_id = session.get("member_id")
    account = session.get("account")
    if member_id==None:
        return {"error":"Please reload to get notifi"}
    result = Notification.get_notifi(member_id)
    return result


@api_notification.route("/api/notifi", methods=["POST"])
def posting_notifi():
    data = request.get_json()
    me = data["me"]
    who = data["who"]
    type = data["type"]
    time = data["time"]
    content = data["content"]
    result = Notification.post_notifi(me,who,content,time)
    return result


@api_notification.route("/api/notifi", methods=["DELETE"])
def reading_notifi():
    member_id = session.get("member_id")
    result = Notification.delete_notifi(member_id)
    return result
