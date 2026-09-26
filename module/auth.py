from functools import wraps
from flask import session


def login_required(view):
    """Reject the request unless the session belongs to a signed-in member."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("member_id") is None:
            return {"error": "not loged in"}, 401
        return view(*args, **kwargs)
    return wrapped
