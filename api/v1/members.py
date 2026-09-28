from flask import session

from data.data import Member

from . import login_required, v1


@v1.route("/members/suggested", methods=["GET"])
@login_required
def suggested():
    """People who subscribe to the same tags as me and are not yet my friends.

    Each item: member_id, account, mood, last_signin, shared_count and shared (tag
    names, most popular first).
    """
    return {"data": Member.suggested(session["member_id"])}
