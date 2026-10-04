"""Reporting posts, comments, members and chat messages (App Store Guideline 1.2; ADR 0014).

What I report disappears from my own view at once. A post whose open reports weigh 3
or more (a Lv 10 member's report counts twice) is hidden from everyone but its author
until the owner reviews it on /admin. The owner hears about new reports through the
bell (every account in ADMIN_ACCOUNTS gets a notification).
"""

from datetime import timedelta

from flask import current_app, request, session

from api.blueprints.api_chat import push_to
from api.metrics import REPORTS
from data.data import Block, Level, Member, Moderation, Notification, Report
from module import levels, rules
from module.clock import taipei_datetime, taipei_now

from . import error, login_required, v1

REASONS = {
    "spam": "垃圾訊息或廣告",
    "harassment": "騷擾或霸凌",
    "sexual": "色情或性騷擾",
    "violence": "暴力或威脅",
    "hate": "仇恨言論",
    "scam": "詐騙",
    "other": "其他",
}
DETAIL_MAX = 500
PER_DAY = 20
HIDE_AT = 3  # open-report weight that hides a post until it is reviewed


def _target(kind, target_id, me):
    """(author member_id, text to keep with the report) or an error response."""
    missing = error("not_found", "找不到要檢舉的內容", 404)
    if kind == "post":
        post = Moderation.post(target_id)
        if not post or not Block.visible(me, target_id):
            return None, missing
        return (post["member_id"], post["content"]), None
    if kind == "comment":
        comment = Moderation.comment(target_id)
        if not comment or not Block.visible(me, comment["block_id"]):
            return None, missing
        return (comment["member_id"], comment["content"]), None
    if kind == "message":
        message = Moderation.message(target_id)
        # Only messages I received: what I sent is mine to delete, not to report.
        if not message or message["recipient_id"] != me:
            return None, missing
        snapshot = message["content"] or ""
        if message["image"]:
            snapshot = f"{snapshot}\n[圖片 {message['image']}]".strip()
        return (message["sender_id"], snapshot), None
    if kind == "member":
        if not Member.getting_data_without_private(target_id):
            return None, missing
        return (target_id, None), None
    return None, error("bad_type", "type 需為 post、comment、message 或 member", 400)


@v1.route("/reports", methods=["POST"])
@login_required
def report():
    """{type, id, reason, detail?} → 201 {data: {id, hidden}}; 409 if I already reported it."""
    body = request.get_json(silent=True) or {}
    me = session["member_id"]
    kind = body.get("type")
    target_id = rules.integer(body.get("id"))
    if target_id is None or target_id < 1:
        return error("bad_id", "id 需為正整數", 400)
    if body.get("reason") not in REASONS:
        return error("bad_reason", "請選擇檢舉原因", 400)
    detail = body.get("detail")
    if detail is not None and (not isinstance(detail, str) or len(detail) > DETAIL_MAX):
        return error("bad_detail", f"補充說明最多 {DETAIL_MAX} 個字", 400)
    found, failure = _target(kind, target_id, me)
    if failure:
        return failure
    author, snapshot = found
    if author == me:
        return error("own_content", "不能檢舉自己", 400)
    now = taipei_datetime()
    if Report.made_since(me, now - timedelta(days=1)) >= PER_DAY:
        return error("too_many", "今天的檢舉次數已達上限，請明天再試", 429)
    my_level = levels.level_of(Level.exps([me]).get(me))
    weight = levels.TRUSTED_REPORT_WEIGHT if my_level >= levels.TRUSTED_LEVEL else 1
    report_id = Report.create(
        {
            "reporter_id": me,
            "target_type": kind,
            "target_id": target_id,
            "target_member_id": author,
            "reason": body["reason"],
            "detail": (detail or "").strip() or None,
            "weight": weight,
            "snapshot": snapshot,
            "created_at": now,
        }
    )
    if report_id is None:
        return error("already_reported", "你已經檢舉過了，我們會盡快處理", 409)
    REPORTS.labels(kind).inc()
    hidden = kind == "post" and Report.open_weight("post", target_id) >= HIDE_AT
    if hidden:
        Moderation.set_hidden(target_id, True)
    for admin in current_app.config["ADMIN_ACCOUNTS"]:
        result = Notification.post_notifi(me, admin, "有一則新的檢舉待處理（/admin）", taipei_now())
        if "ok" in result:
            push_to(admin, "notification", {})
    return {"data": {"id": report_id, "hidden": hidden}}, 201
