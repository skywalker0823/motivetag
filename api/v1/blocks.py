"""Blocking members (App Store Guideline 1.2; ADR 0014).

Blocking someone ends any friendship or invitation between us. After that I no longer
see their posts and comments, and neither of us can message, invite or notify the
other. They are not told; to them I simply stop answering.
"""

from flask import session

from data.data import Member, MemberBlock
from module.clock import taipei_datetime

from . import error, login_required, v1


def _time(value):
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


@v1.route("/blocks", methods=["GET"])
@login_required
def blocked_members():
    """The members I blocked: [{member_id, account, blocked_at}], most recent first."""
    return {
        "data": [
            {
                "member_id": row["member_id"],
                "account": row["account"],
                "blocked_at": _time(row["created_at"]),
            }
            for row in MemberBlock.blocked_by(session["member_id"])
        ]
    }


def _target(account):
    member_id = Member.id_for(account)
    if member_id is None:
        return None, error("no_such_member", "找不到這個帳號", 404)
    if member_id == session["member_id"]:
        return None, error("self", "不能封鎖自己", 400)
    return member_id, None


@v1.route("/blocks/<account>", methods=["PUT"])
@login_required
def block(account):
    """Blocks `account` (doing it twice is fine)."""
    member_id, failure = _target(account)
    if failure:
        return failure
    MemberBlock.block(session["member_id"], member_id, taipei_datetime())
    return {"data": {"account": account, "blocked": True}}


@v1.route("/blocks/<account>", methods=["DELETE"])
@login_required
def unblock(account):
    member_id, failure = _target(account)
    if failure:
        return failure
    MemberBlock.unblock(session["member_id"], member_id)
    return {"data": {"account": account, "blocked": False}}
