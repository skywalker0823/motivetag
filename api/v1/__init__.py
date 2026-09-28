"""API v1: the contract the web app and a future mobile app share (docs/adr/0010).

Unlike the older /api endpoints, v1 answers with real HTTP status codes and reports
every failure as {"error": {"code": "...", "message": "..."}}, where `code` is stable
for programs and `message` is ready to show to people.
"""

from functools import wraps

from flask import Blueprint, session

v1 = Blueprint("v1", __name__, url_prefix="/api/v1")


def error(code, message, status):
    return {"error": {"code": code, "message": message}}, status


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("member_id") is None:
            return error("not_signed_in", "請先登入", 401)
        return view(*args, **kwargs)

    return wrapped


from . import account, members, posts  # noqa: E402,F401 - registers the routes on v1
