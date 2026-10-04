"""Reviewing reports (the /admin page). Anyone who is not an admin gets 404, so the
endpoints do not reveal that they exist."""

from functools import wraps

from flask import request

from data.data import Moderation, Report
from module import admin as admin_rights
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
                "author": {"member_id": row["target_member_id"], "account": row["target_account"]},
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
