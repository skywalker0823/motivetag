from urllib.parse import quote

from botocore.exceptions import BotoCoreError, ClientError
from flask import current_app, redirect, request, session

from data.data import Member
from module import email_verification

from . import error, login_required, v1


@v1.route("/email/verification", methods=["POST"])
@login_required
def resend_verification():
    """E-mails the signed-in member a new confirmation link."""
    if not email_verification.required():
        return error("not_required", "目前不需要驗證 Email", 409)
    member = Member.get_member(session["account"])
    if member is None:
        return error("not_found", "找不到這個帳號", 404)
    if member["email_verified_at"] is not None:
        return error("already_verified", "你的 Email 已經驗證過了", 409)
    try:
        email_verification.send_link(member["member_id"], member["account"], member["email"])
    except email_verification.TooSoon as exc:
        response = error("too_soon", str(exc), 429)
        return (*response, {"Retry-After": str(exc.seconds)})
    except email_verification.LimitReached as exc:
        return error("limit_reached", str(exc), 429)
    except (BotoCoreError, ClientError) as exc:
        current_app.logger.warning("verification e-mail failed: %s", exc)
        return error("send_failed", "寄信失敗，請稍後再試", 502)
    return {"sent": True, "email": member["email"]}


@v1.route("/email/verify", methods=["GET"])
def verify():
    """The link in the e-mail. Works in any browser, signed in or not."""
    member_id = email_verification.confirm(request.args.get("token"))
    mine = member_id is not None and member_id == session.get("member_id")
    if mine:
        return redirect(f"/{quote(session['account'])}?verified=1")
    if member_id is not None:
        return redirect("/?verified=1")
    if session.get("account"):
        return redirect(f"/{quote(session['account'])}?verify=invalid")
    return redirect("/?verify=invalid")
