from flask import session

from module import invites

from . import login_required, v1


@v1.route("/invites/mine", methods=["GET"])
@login_required
def my_invite():
    """The signed-in member's personal invite link (the same every time)."""
    return {"url": invites.link_for(session["member_id"])}
