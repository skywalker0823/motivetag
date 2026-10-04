"""Reviewing reports and suspending accounts (the /admin page). Anyone who is not an admin gets 404, so the
endpoints do not reveal that they exist."""

from functools import wraps

from flask import current_app, request

from data.data import Member, Moderation, Report, Suspension
from module import admin as admin_rights
from module import suspension
from module.clock import taipei_datetime

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
        "admin": account in current_app.config["ADMIN_ACCOUNTS"],
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
        return {"data": {"closed": closed}}
    if action == "remove":
        if kind == "member":
            return error("cannot_remove", "帳號無法從這裡刪除", 400)
        removed, image = Moderation.remove(kind, target_id)
        if image:
            remove_images([image])
        closed = Report.close_all(kind, target_id, "resolved", now)
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
    if account in current_app.config["ADMIN_ACCOUNTS"]:
        return error("cannot_suspend_admin", "管理員帳號不能停權", 400)
    until = suspension.suspend(member_id, days, reason.strip() or None)
    from api.blueprints.api_chat import end_sessions  # the blueprints import v1

    end_sessions(account)
    closed = Report.close_all("member", member_id, "resolved", taipei_datetime())
    return {"data": {"account": account, "until": _until(until), "closed": closed}}


@v1.route("/admin/members/<account>/suspension", methods=["DELETE"])
@admin_required
def lift(account):
    member_id = Member.id_for(account)
    if member_id is None:
        return error("no_such_member", "找不到這個帳號", 404)
    suspension.lift(member_id)
    return {"data": {"account": account}}
