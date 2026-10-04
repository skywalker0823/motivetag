"""The /admin page: reviewing reports, suspending accounts, site numbers, looking up
members (level, e-mail verification, a notice), announcements and a log of it all. Anyone who is not an admin gets 404, so the
endpoints do not reveal that they exist."""

from datetime import timedelta
from functools import wraps

from flask import current_app, request, session

from data.data import AdminData, Member, Moderation, Report, Suspension
from module import admin as admin_rights
from module import levels, push, suspension
from module.clock import taipei_datetime, taipei_now

from . import error, v1
from .account import remove_images
from .reports import REASONS

STATUSES = {"open", "resolved", "dismissed"}


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not admin_rights.is_admin():
            return error("not_found", "Not Found", 404)
        return view(*args, **kwargs)

    return wrapped


def _is_admin_account(account):
    admins = {a.lower() for a in current_app.config["ADMIN_ACCOUNTS"]}
    return bool(account) and account.lower() in admins


def _log(action, target, detail):
    AdminData.log(
        session["account"], action, target, (detail or None) and detail[:500], taipei_datetime()
    )


def _time(value):
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


@v1.route("/admin/reports", methods=["GET"])
@admin_required
def reports():
    """Reports grouped by what they point at, newest first: ?status=open (default),
    resolved or dismissed. Each group: type, id, author, the reported text as it was,
    whether the post is hidden, and the reports (reason, detail, reporter, time)."""
    status = request.args.get("status", "open")
    if status not in STATUSES:
        return error("bad_status", "status 需為 open、resolved 或 dismissed", 400)
    groups = {}
    for row in Report.listing(status):
        key = (row["target_type"], row["target_id"])
        if key not in groups:
            post = Moderation.post(row["target_id"]) if row["target_type"] == "post" else None
            message = (
                Moderation.message(row["target_id"]) if row["target_type"] == "message" else None
            )
            groups[key] = {
                "type": row["target_type"],
                "id": row["target_id"],
                "author": _author(row["target_member_id"], row["target_account"]),
                "snapshot": row["snapshot"],
                "image": bool(post and post["block_img"]),
                # A chat photo is only reachable here; admins may open it (api_images).
                "photo": f"/images/{message['image']}" if message and message["image"] else None,
                "hidden": bool(post and post["hidden"]),
                "exists": row["target_type"] == "member" or _exists(*key),
                "weight": 0,
                "reports": [],
            }
        group = groups[key]
        group["weight"] += row["weight"]
        group["reports"].append(
            {
                "id": row["report_id"],
                "reason": row["reason"],
                "reason_text": REASONS.get(row["reason"], row["reason"]),
                "detail": row["detail"],
                "reporter": row["reporter"],
                "created_at": _time(row["created_at"]),
                "handled_at": _time(row["handled_at"]),
            }
        )
    return {"data": list(groups.values()), "open": Report.open_count()}


def _author(member_id, account):
    state = suspension.current(member_id) if account else None
    return {
        "member_id": member_id,
        "account": account,
        "suspended": state is not None,
        "suspended_until": _until(state["until"]) if state else None,
        "admin": _is_admin_account(account),
    }


def _until(value):
    """The end of a suspension; None means for good."""
    return None if suspension.is_permanent(value) else _time(value)


def _exists(kind, target_id):
    lookup = {"post": Moderation.post, "comment": Moderation.comment, "message": Moderation.message}
    return lookup[kind](target_id) is not None


@v1.route("/admin/reports/<kind>/<int:target_id>", methods=["POST"])
@admin_required
def decide(kind, target_id):
    """{action: "remove"} deletes the post, comment or message and resolves its reports;
    {action: "dismiss"} keeps it (and shows a hidden post again)."""
    action = (request.get_json(silent=True) or {}).get("action")
    if kind not in {"post", "comment", "message", "member"}:
        return error("bad_type", "未知的類型", 400)
    now = taipei_datetime()
    if action == "dismiss":
        if kind == "post":
            Moderation.set_hidden(target_id, False)
        closed = Report.close_all(kind, target_id, "dismissed", now)
        _log("dismiss", None, f"{kind} {target_id}")
        return {"data": {"closed": closed}}
    if action == "remove":
        if kind == "member":
            return error("cannot_remove", "帳號無法從這裡刪除", 400)
        removed, image = Moderation.remove(kind, target_id)
        if image:
            remove_images([image])
        closed = Report.close_all(kind, target_id, "resolved", now)
        _log("remove", None, f"{kind} {target_id}")
        return {"data": {"closed": closed, "removed": bool(removed)}}
    return error("bad_action", "action 需為 remove 或 dismiss", 400)


@v1.route("/admin/suspensions", methods=["GET"])
@admin_required
def suspensions():
    """Accounts suspended right now, the ones ending soonest first."""
    rows = Suspension.listing(taipei_datetime())
    return {
        "data": [
            {
                "account": row["account"],
                "until": _until(row["suspended_until"]),
                "reason": row["suspended_reason"],
            }
            for row in rows
        ]
    }


@v1.route("/admin/members/<account>/suspension", methods=["PUT"])
@admin_required
def suspend(account):
    """{days: 1 | 3 | 7 | 30 | null (for good), reason}. Ends the member's open
    sessions and resolves the open reports about the account."""
    body = request.get_json(silent=True) or {}
    days = body.get("days", 0)
    if days is not None and (isinstance(days, bool) or days not in suspension.DURATIONS):
        return error("bad_days", "days 需為 1、3、7、30 或 null（永久）", 400)
    reason = body.get("reason") or ""
    if not isinstance(reason, str) or len(reason.strip()) > suspension.REASON_MAX:
        return error("bad_reason", f"原因最多 {suspension.REASON_MAX} 個字", 400)
    member_id = Member.id_for(account)
    if member_id is None:
        return error("no_such_member", "找不到這個帳號", 404)
    if _is_admin_account(account):
        return error("cannot_suspend_admin", "管理員帳號不能停權", 400)
    until = suspension.suspend(member_id, days, reason.strip() or None)
    from api.blueprints.api_chat import end_sessions  # the blueprints import v1

    end_sessions(account)
    closed = Report.close_all("member", member_id, "resolved", taipei_datetime())
    _log("suspend", account, f"{days or '永久'}{' 天' if days else ''} {reason.strip()}".strip())
    return {"data": {"account": account, "until": _until(until), "closed": closed}}


@v1.route("/admin/members/<account>/suspension", methods=["DELETE"])
@admin_required
def lift(account):
    member_id = Member.id_for(account)
    if member_id is None:
        return error("no_such_member", "找不到這個帳號", 404)
    suspension.lift(member_id)
    _log("lift", account, None)
    return {"data": {"account": account}}


# ---------- Site numbers ----------

DAYS_CHARTED = 14


@v1.route("/admin/stats", methods=["GET"])
@admin_required
def site_stats():
    """Members, activity and content counts (today, last 7 days, all time), sign-ups
    and posts per day for two weeks, and who posts and levels the most."""
    now = taipei_datetime()
    today = now.date()
    week_start = today - timedelta(days=6)
    since = today - timedelta(days=DAYS_CHARTED - 1)
    numbers = AdminData.overview(now, today, week_start)
    numbers["online"] = len(_online())
    signups, posts = AdminData.daily(since)
    days = [since + timedelta(days=n) for n in range(DAYS_CHARTED)]
    return {
        "data": {
            **numbers,
            "daily": [
                {"day": day.isoformat(), "signups": signups.get(day, 0), "posts": posts.get(day, 0)}
                for day in days
            ],
            "top_posters": AdminData.top_posters(week_start),
            "top_levels": [
                {"account": r["account"], "exp": r["exp"], "level": levels.level_of(r["exp"])}
                for r in AdminData.top_levels()
            ],
        }
    }


# ---------- Members ----------

MAX_LEVEL = 50
NOTICE_MAX = 300


def _member(row):
    state = suspension.current(row["member_id"])
    return {
        "account": row["account"],
        "email": row["email"],
        "demo": row["email"].endswith(AdminData.DEMO_DOMAIN[1:]),
        "admin": _is_admin_account(row["account"]),
        "verified": row["email_verified_at"] is not None,
        "joined": row["first_signup"].isoformat() if row["first_signup"] else None,
        "last_signin": _time(row["last_signin"]),
        "last_active_day": row["last_active_day"].isoformat() if row["last_active_day"] else None,
        "exp": row["exp"] or 0,
        "level": levels.level_of(row["exp"]),
        "streak": row["streak"],
        "posts": row["posts"],
        "comments": row["comments"],
        "friends": row["friends"],
        "reported": row["reported"],
        "online": row["account"] in _online(),
        "suspended": state is not None,
        "suspended_until": _until(state["until"]) if state else None,
        "suspended_reason": state["reason"] if state else None,
    }


def _online():
    from api.blueprints.api_chat import online  # the blueprints import v1

    return online


@v1.route("/admin/members", methods=["GET"])
@admin_required
def member_list():
    """?q= part of an account name or e-mail; without it, the newest members."""
    query = (request.args.get("q") or "").strip()[:100]
    return {"data": [_member(row) for row in AdminData.members(query)]}


def _target(account):
    member_id = Member.id_for(account)
    if member_id is None:
        return None, error("no_such_member", "找不到這個帳號", 404)
    return member_id, None


@v1.route("/admin/members/<account>/level", methods=["PUT"])
@admin_required
def set_level(account):
    """{level: 1-50} sets the exp to the start of that level; {exp: n} sets it exactly.
    The member's open pages move their level bar at once."""
    member_id, problem = _target(account)
    if problem:
        return problem
    body = request.get_json(silent=True) or {}
    level, exp = body.get("level"), body.get("exp")
    if isinstance(level, int) and not isinstance(level, bool) and 1 <= level <= MAX_LEVEL:
        exp = levels.exp_for(level)
    elif not (
        isinstance(exp, int)
        and not isinstance(exp, bool)
        and 0 <= exp <= levels.exp_for(MAX_LEVEL + 1)
    ):
        return error("bad_level", f"level 需為 1–{MAX_LEVEL}，或給 exp", 400)
    before = Member.get_member(account)["exp"] or 0
    AdminData.set_exp(member_id, exp)
    new_level = levels.level_of(exp)
    from api.blueprints.api_chat import push_to  # the blueprints import v1

    push_to(
        account,
        "exp",
        {
            "exp": exp,
            "level": new_level,
            "gained": exp - before,
            "action": "admin",
            "level_up": new_level > levels.level_of(before),
        },
    )
    _log("level", account, f"Lv {levels.level_of(before)} → Lv {new_level}（exp {before} → {exp}）")
    return {"data": {"account": account, "exp": exp, "level": new_level}}


@v1.route("/admin/members/<account>/verify", methods=["POST"])
@admin_required
def verify_email(account):
    """Marks the member's e-mail as confirmed (when the e-mail did not arrive)."""
    member_id, problem = _target(account)
    if problem:
        return problem
    Member.mark_verified(member_id, taipei_datetime())
    _log("verify", account, None)
    return {"data": {"account": account, "verified": True}}


def _notice_text(body):
    text = (body.get("message") or "") if isinstance(body.get("message"), str) else ""
    text = text.strip()
    if not 1 <= len(text) <= NOTICE_MAX:
        return None
    return text


@v1.route("/admin/members/<account>/notice", methods=["POST"])
@admin_required
def send_notice(account):
    """{message}: a bell notification (and a phone push) to one member."""
    member_id, problem = _target(account)
    if problem:
        return problem
    text = _notice_text(request.get_json(silent=True) or {})
    if text is None:
        return error("bad_message", f"訊息需為 1–{NOTICE_MAX} 個字", 400)
    from api.blueprints.api_chat import push_to  # the blueprints import v1
    from data.data import Notification

    Notification.post_notifi(session["member_id"], account, f"📢 管理員：{text}", taipei_now())
    push_to(account, "notification", {})
    push.notify(member_id, account, "MotiveTag 管理員", text)
    _log("notice", account, text)
    return {"data": {"account": account}}


@v1.route("/admin/announcements", methods=["POST"])
@admin_required
def announce():
    """{message}: a bell notification to every member (demo members excepted).
    No phone pushes: one announcement should not buzz every phone at once."""
    text = _notice_text(request.get_json(silent=True) or {})
    if text is None:
        return error("bad_message", f"公告需為 1–{NOTICE_MAX} 個字", 400)
    from api import socketio  # the app package imports this module

    sent = AdminData.broadcast(session["member_id"], f"📢 公告：{text}", taipei_now())
    socketio.emit("notification", {})
    _log("announce", None, f"{sent} 人：{text}")
    return {"data": {"sent": sent}}


@v1.route("/admin/logs", methods=["GET"])
@admin_required
def admin_logs():
    """The last 100 things admins did here, newest first."""
    return {
        "data": [
            {
                "admin": row["admin"],
                "action": row["action"],
                "target": row["target"],
                "detail": row["detail"],
                "at": _time(row["created_at"]),
            }
            for row in AdminData.logs()
        ]
    }
