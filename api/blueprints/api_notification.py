from flask import request, session

from data.data import Member, MemberBlock, Notification
from module.auth import login_required
from module.clock import taipei_now

from . import api_notification
from .api_chat import push_to

# The server writes the text, so a member can only send these, signed with their name.
MESSAGES = {
    "friend_invite": "{me} 想加你為好友",
    "friend_accept": "{me} 接受了你的好友邀請",
    "friend_decline": "{me} 婉拒了你的好友邀請",
    "chat_missed": "{me} 想找你聊天，但你不在線上",
}


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
    data = request.get_json(silent=True) or {}
    template = MESSAGES.get(data.get("type"))
    who = data.get("who")
    if template is None or not isinstance(who, str):
        return {"error": "unknown notification"}, 400
    recipient = Member.id_for(who)
    if recipient is not None and MemberBlock.has_blocked(recipient, session.get("member_id")):
        return {"ok": "Notification send"}  # they blocked me; they are not told either way
    content = template.format(me=session.get("account"))
    result = Notification.post_notifi(session.get("member_id"), who, content, taipei_now())
    if "ok" in result:
        push_to(who, "notification", {})  # their open tabs fetch it now, not at the next poll
    return result


@api_notification.route("/api/notifi", methods=["DELETE"])
@login_required
def reading_notifi():
    member_id = session.get("member_id")
    result = Notification.delete_notifi(member_id)
    return result
