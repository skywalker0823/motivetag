"""One-to-one chat between friends, stored so it reaches people wherever they are.

Messages are sent over HTTP (a status code for every failure, nothing lost while the
socket reconnects) and pushed over Socket.IO to every open tab of both members, the
way Messenger or Telegram behave: no "room" to open and no waiting for the other side
to join. Pushed events (api/blueprints/api_chat.py has the socket side):

- `chat:message` {message}: a new message, to the recipient and the sender's other tabs.
- `chat:read` {by, partner, up_to, read_at}: `by` read what `partner` sent up to `up_to`.
- `chat:typing` {from}: the other member is typing (sent by the browser over the socket).

A message: {id, from, to, content, image, sent_at, read_at}; `from` and `to` are
accounts, `image` is a photo's URL (/images/dm_…) or null, times are Taipei wall-clock
"YYYY-MM-DD HH:MM:SS" (see static/js/lib/time.js).

Photos go straight from the browser to S3 like post images (ADR 0007): the browser
asks POST …/images for a presigned upload, sends the file to S3, then sends the
message with the key it was given. Only the two members (and admins reviewing a
report) can open the photo.
"""

import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta

from flask import request, session

from api.blueprints.api_chat import online, push_to
from api.blueprints.api_images import (
    ALLOWED_TYPES,
    BUCKET_NAME,
    CHAT_KEY,
    presigned_post,
    uploaded,
)
from data.data import DirectMessage, Friend, Level, Member, MemberBlock, Profile
from module import email_verification, levels, push, rules
from module.clock import taipei_datetime

from . import error, login_required, v1

PAGE = 30


def _time(value):
    return value.strftime("%Y-%m-%d %H:%M:%S") if value else None


def _message(row, accounts):
    return {
        "id": row["message_id"],
        "from": accounts[row["sender_id"]],
        "to": accounts[row["recipient_id"]],
        "content": row["content"],
        "image": f"/images/{row['image']}" if row.get("image") else None,
        "sent_at": _time(row["sent_at"]),
        "read_at": _time(row["read_at"]),
    }


def _partner(account):
    """(member_id, error response) for the member at the other end of a conversation."""
    partner_id = Member.id_for(account)
    if partner_id is None:
        return None, error("no_such_member", "找不到這個帳號", 404)
    if partner_id == session["member_id"]:
        return None, error("self", "不能和自己聊天", 400)
    return partner_id, None


@v1.route("/chats", methods=["GET"])
@login_required
def conversations():
    """My conversations, newest first, and how many messages I have not read in all."""
    me, my_account = session["member_id"], session["account"]
    data = []
    for row in DirectMessage.conversations(me):
        accounts = {me: my_account, row["partner_id"]: row["partner"]}
        data.append(
            {
                "partner": {"member_id": row["partner_id"], "account": row["partner"]},
                "online": row["partner"] in online,
                "last": _message(row, accounts),
                "unread": row["unread"],
            }
        )
    return {"data": data, "unread": DirectMessage.unread_count(me)}


@v1.route("/chats/<account>/messages", methods=["GET"])
@login_required
def history(account):
    """Messages with `account`, oldest first; ?before=<id> pages back in time.

    Also says whether I may send (only to friends) and whether they are online.
    """
    partner_id, failure = _partner(account)
    if failure:
        return failure
    before = request.args.get("before")
    if before is not None:
        before = rules.integer(before)
        if before is None or before < 1:
            return error("bad_before", "before 需為正整數", 400)
    me = session["member_id"]
    rows = DirectMessage.history(me, partner_id, before, PAGE)
    accounts = {me: session["account"], partner_id: account}
    return {
        "data": [_message(row, accounts) for row in rows],
        "more": len(rows) == PAGE,
        "partner": {
            "member_id": partner_id,
            "account": account,
            "level": levels.level_of(Level.exps([partner_id]).get(partner_id)),
            "gender": Profile.genders([partner_id]).get(partner_id),
        },
        "online": account in online,
        "can_send": Friend.are_friends(me, partner_id) and not MemberBlock.between(me, partner_id),
        "blocked": MemberBlock.has_blocked(me, partner_id),
    }


def _may_message(account):
    """(partner_id, error response): may I send `account` anything right now?"""
    partner_id, failure = _partner(account)
    if failure:
        return None, failure
    me = session["member_id"]
    if not email_verification.verified(me):
        return None, error("email_not_verified", "請先到信箱完成 Email 驗證，才能開始聊天", 403)
    if MemberBlock.between(me, partner_id):
        return None, error("blocked", "無法傳訊息給這個帳號", 403)
    if not Friend.are_friends(me, partner_id):
        return None, error("not_friends", "成為好友後才能傳訊息", 403)
    return partner_id, None


PHOTO_UPLOADS = 20  # signed photo uploads per member …
PHOTO_WINDOW = 600  # … per ten minutes; in memory, one worker (ADR 0008)
_photo_uploads = defaultdict(deque)


def _upload_allowed(member_id):
    now = time.monotonic()
    recent = _photo_uploads[member_id]
    while recent and now - recent[0] > PHOTO_WINDOW:
        recent.popleft()
    if len(recent) >= PHOTO_UPLOADS:
        return False
    recent.append(now)
    return True


@v1.route("/chats/<account>/images", methods=["POST"])
@login_required
def sign_photo(account):
    """{content_type} → {data: {key, url, fields}}: where the browser posts a photo."""
    _, failure = _may_message(account)
    if failure:
        return failure
    content_type = (request.get_json(silent=True) or {}).get("content_type")
    if content_type not in ALLOWED_TYPES:
        return error("bad_type", "只能傳 PNG、JPEG、GIF 或 WebP 圖片", 400)
    if not BUCKET_NAME:
        return error("uploads_off", "目前無法傳圖片", 503)
    me = session["member_id"]
    if not _upload_allowed(me):
        return error("too_many", "圖片傳得太快了，請稍候再試", 429)
    key = f"dm_{me}_{secrets.token_hex(16)}"
    return {"data": {"key": key, **presigned_post(key, content_type)}}


@v1.route("/chats/<account>/messages", methods=["POST"])
@login_required
def send(account):
    """{content?, image?} → 201 with the stored message; `image` is a key from POST
    …/images, already uploaded. A message needs text, a photo or both."""
    partner_id, failure = _may_message(account)
    if failure:
        return failure
    me = session["member_id"]
    body = request.get_json(silent=True) or {}
    image = body.get("image")
    if image is not None:
        match = CHAT_KEY.match(image) if isinstance(image, str) else None
        # Only a photo I uploaded myself, used once, and really there.
        if not match or int(match.group(1)) != me or DirectMessage.image_used(image):
            return error("bad_image", "圖片無效，請重新選擇", 400)
        if not uploaded(image):
            return error("bad_image", "圖片還沒上傳完成，請再試一次", 400)
    text = body.get("content")
    if image and (text is None or (isinstance(text, str) and not text.strip())):
        content = ""  # a photo on its own
    else:
        content = rules.text(body.get("content"), rules.CHAT_MESSAGE_MAX)
        if content is None:
            return error("bad_content", f"訊息需為 1–{rules.CHAT_MESSAGE_MAX} 個字", 400)
    now = taipei_datetime()
    if DirectMessage.sent_since(me, now - timedelta(minutes=1)) >= rules.CHAT_PER_MINUTE:
        return error("too_many", "訊息傳得太快了，請稍候再試", 429)
    row = DirectMessage.send(me, partner_id, content, now, image)
    message = _message(row, {me: session["account"], partner_id: account})
    push_to(account, "chat:message", message)
    push_to(session["account"], "chat:message", message)  # my other tabs and devices
    preview = f"📷 {content or '照片'}" if image else content
    push.notify(
        partner_id, account, session["account"], preview, f"/{account}?chat={session['account']}"
    )
    return {"data": message}, 201


@v1.route("/chats/<account>/read", methods=["POST"])
@login_required
def mark_read(account):
    """Marks what `account` sent me, up to message `up_to`, as read (read receipts)."""
    partner_id, failure = _partner(account)
    if failure:
        return failure
    up_to = rules.integer((request.get_json(silent=True) or {}).get("up_to"))
    if up_to is None or up_to < 1:
        return error("bad_up_to", "up_to 需為正整數", 400)
    now = taipei_datetime()
    count = DirectMessage.mark_read(session["member_id"], partner_id, up_to, now)
    if count:
        receipt = {
            "by": session["account"],
            "partner": account,
            "up_to": up_to,
            "read_at": _time(now),
        }
        push_to(account, "chat:read", receipt)  # they see "已讀"
        push_to(session["account"], "chat:read", receipt)  # my other tabs clear the badge
    return {"data": {"read": count}}
