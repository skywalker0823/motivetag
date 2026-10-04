import re
from datetime import date

from flask import current_app, request, session

from api.metrics import auth_event
from data.data import Friend, Member, Member_tags, MemberBlock, Notification
from module import email_verification, invites, lockout, rules, suspension, turnstile
from module.auth import login_required
from module.clock import taipei_now
from module.disposable import is_disposable

from . import api_member
from .api_chat import push_to


def with_verification(member):
    """Replaces the raw timestamp with the flag the page needs."""
    if member:
        verified_at = member.pop("email_verified_at", None)
        member["email_verified"] = verified_at is not None or not email_verification.required()
    return member


def client_ip():
    # nginx appends the visitor's address (from CF-Connecting-IP) last.
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.rsplit(",", 1)[-1].strip() or request.remote_addr


@api_member.route("/api/member", methods=["GET"])
def check_member():
    if session.get("account"):
        account = session.get("account")
        data = with_verification(Member.get_member(account))
        return {"ok": True, "data": data}
    elif request.args.get("account_check"):
        account = request.args.get("account_check")
        # Only reveal whether the name is taken; null means it is available.
        return {"ok": True if Member.account_exists(account) else None}
    return {"error": "not loged in"}


# Letters (any language), digits and _; the name becomes the member's page at
# /<account>, so it must not shadow the site's own paths.
ACCOUNT = re.compile(r"^\w{3,20}$")
RESERVED = {
    "api",
    "tag",
    "images",
    "healthz",
    "js",
    "css",
    "img",
    "admin",
    "metrics",
    "privacy",
    "terms",
}
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 8
MIN_AGE = 18


def age_on(birthday, today):
    return today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))


def signup_error(data):
    """Why this sign-up is invalid, or None."""
    fields = ("account", "password", "email", "birthday")
    if not all(isinstance(data.get(f), str) for f in fields):
        return "missing fields"
    if not ACCOUNT.match(data["account"]) or data["account"].lower() in RESERVED:
        return "帳號需為 3-20 個字母、數字或底線"
    # An admin name nobody holds yet must not be taken by someone else.
    if data["account"].lower() in {a.lower() for a in current_app.config["ADMIN_ACCOUNTS"]}:
        return "這個帳號已經有人使用"
    if len(data["password"]) < MIN_PASSWORD:
        return f"密碼至少 {MIN_PASSWORD} 個字元"
    if len(data["email"]) > 254 or not EMAIL.match(data["email"]):
        return "Email 格式不正確"
    if is_disposable(data["email"]):
        return "請使用常用的 Email，不接受拋棄式信箱"
    try:
        birthday = date(*map(int, data["birthday"].split("-")))
    except (TypeError, ValueError):
        return "生日格式不正確"
    if not date(1900, 1, 1) <= birthday <= date.today():
        return "生日格式不正確"
    if age_on(birthday, date.today()) < MIN_AGE:
        return f"需年滿 {MIN_AGE} 歲才能註冊"
    return None


@api_member.route("/api/member", methods=["POST"])
def sign_up_member():
    data = request.get_json(silent=True) or {}
    error = signup_error(data)
    if error:
        auth_event("signup_refused")
        return {"error": error}, 400
    if not turnstile.passed(data.get("turnstile_token"), client_ip()):
        auth_event("signup_refused")
        return {"error": "人機驗證沒有通過，請再試一次"}, 400
    account = data["account"]
    password = data["password"]
    email = data["email"]
    birthday = data["birthday"]
    first_signup = taipei_now()[:10]
    session["FIRST_TIME"] = "YES"
    result = Member.sign_up(account, password, email, birthday, first_signup)
    if result != "ok":
        auth_event("signup_refused")
        return {"error": result}
    auth_event("signup_ok")
    member = Member.get_member(account)
    join_inviter(member, data.get("invite"))
    if email_verification.required():
        try:
            email_verification.send_link(member["member_id"], account, email)
        except Exception as exc:  # noqa: BLE001 - the account exists; they can resend
            current_app.logger.warning("verification e-mail to %s failed: %s", email, exc)
    return {"ok": True}


def join_inviter(member, token):
    """Signed up through someone's invite link: friends at once, and they are told."""
    inviter = invites.inviter(token)
    if inviter is None or inviter["member_id"] == member["member_id"]:
        return
    Friend.connect(inviter["member_id"], member["member_id"])
    Notification.post_notifi(
        member["member_id"],
        inviter["account"],
        f"{member['account']} 透過你的邀請連結加入了，你們已經是好友",
        taipei_now(),
    )
    push_to(inviter["account"], "notification", {})
    auth_event("signup_invited")


@api_member.route("/api/member", methods=["PUT"])
def sign_in_member():
    data = request.get_json(silent=True) or {}
    account = data.get("account")
    password = data.get("password")
    time = taipei_now()
    if not all(isinstance(v, str) for v in (account, password)):
        return {"error": "wrong account or password"}, 400
    wait = lockout.locked(account)
    if wait:
        auth_event("login_locked")
        minutes = (wait + 59) // 60
        return {"error": {"msg": f"密碼錯誤次數太多，請 {minutes} 分鐘後再試"}}, 429
    result = Member.sign_in(account, password, time)
    if result["msg"] != "ok":
        lockout.failed(account)
    else:
        lockout.succeeded(account)
    if session.get("FIRST_TIME") and session["FIRST_TIME"] == "YES" and result["msg"] == "ok":
        Member_tags.new_bie_tag(result["data"]["member_id"], "新手引導")
        session["FIRST_TIME"] = "NO"
    if result["msg"] == "ok":
        state = suspension.current(result["data"]["member_id"])
        if state:
            auth_event("login_suspended")
            return {"error": {"msg": suspension.message(state)}}
    auth_event("login_ok" if result["msg"] == "ok" else "login_failed")
    if result["msg"] == "ok":
        result = result["data"]
        session.clear()
        session["account"] = account
        session["member_id"] = result["member_id"]
        return {"ok": True, "data": result}
    return {"error": result}


@api_member.route("/api/member", methods=["PATCH"])
@login_required
def modify_member():
    data = request.get_json(silent=True) or {}
    member_id = session.get("member_id")
    if data.get("category") != "mood":
        return {"error": "unknown field"}, 400
    mood = rules.text(data.get("content"), rules.MOOD_MAX)
    if mood is None:
        return {"error": f"心情需為 1–{rules.MOOD_MAX} 個字"}, 400
    result = Member.patch_user_data(member_id, "mood", mood)
    if result != 1:
        return {"error": "update user data fail"}
    return {"ok": "Update data success"}


@api_member.route("/api/member", methods=["DELETE"])
def sign_out_member():
    session["account"] = None
    session.clear()
    return {"ok": True}


@api_member.route("/api/get_user_sp", methods=["GET"])
@login_required
def get_user_sp():
    target_id = request.args.get("member_id")
    member_id = session.get("member_id")
    from api.v1.profile import card_of  # v1 imports the blueprints

    user_basic_data = Member.getting_data_without_private(target_id)
    checker = Friend.friend_ship_checker(member_id, target_id)
    return {
        "card": card_of(int(target_id)) if user_basic_data else None,
        "ok": True,
        "data": user_basic_data,
        "is_friend": checker,
        "shared_tags": Member.shared_tags(member_id, target_id) if user_basic_data else [],
        "blocked": bool(user_basic_data) and MemberBlock.has_blocked(member_id, target_id),
    }
