"""Invite links: a member shares https://motivetag.com/?invite=<token>, and whoever
signs up through it becomes their friend straight away (sharing the link is the
inviter's consent). The token is the inviter's id signed with SECRET_KEY, so nobody
can make a link in someone else's name.
"""

from flask import current_app
from itsdangerous import BadSignature, URLSafeSerializer

from data.data import Member
from module.urls import public_base_url


def _serializer():
    return URLSafeSerializer(current_app.config["SECRET_KEY"], salt="invite")


def link_for(member_id):
    return f"{public_base_url()}/?invite={_serializer().dumps(member_id)}"


def inviter(token):
    """{"member_id", "account"} of the member who shared the link, or None."""
    if not isinstance(token, str) or not token or len(token) > 200:
        return None
    try:
        member_id = _serializer().loads(token)
    except BadSignature:
        return None
    if not isinstance(member_id, int):
        return None
    member = Member.getting_data_without_private(member_id)
    return {"member_id": member_id, "account": member["account"]} if member else None
