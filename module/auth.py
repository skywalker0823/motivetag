from functools import wraps

from flask import session

from module import email_verification


def login_required(view):
    """Reject the request unless the session belongs to a signed-in member."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("member_id") is None:
            return {"error": "not loged in"}, 401
        return view(*args, **kwargs)

    return wrapped


def verified_required(view):
    """Like login_required, and the member must have confirmed their e-mail address
    (when verification is on; see module/email_verification.py)."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        member_id = session.get("member_id")
        if member_id is None:
            return {"error": "not loged in"}, 401
        if not email_verification.verified(member_id):
            return {"error": "email not verified"}, 403
        return view(*args, **kwargs)

    return wrapped
