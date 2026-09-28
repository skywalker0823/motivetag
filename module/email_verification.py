"""Confirming that a member owns their e-mail address, with a one-time link.

Required only when e-mail can be sent (EMAIL_FROM is set). Until a member clicks the
link they can sign in and read, but not post, comment, invite or chat
(`verified_required` in module/auth.py).

Limits keep both abuse and the SES bill small: one link a minute and five a day per
member, and DAILY_LIMIT links a day for the whole site. At US$0.10 per 1,000 e-mails,
500 a day is at most about US$1.50 a month.
"""

import hashlib
import html
import math
import secrets
from datetime import timedelta

from flask import current_app, request

from data.data import EmailToken, Member
from module import mailer
from module.clock import taipei_datetime

LINK_VALID = timedelta(hours=24)
RESEND_AFTER = timedelta(seconds=60)
PER_MEMBER_DAILY = 5
DAILY_LIMIT = 500
VERIFY_PATH = "/api/v1/email/verify"


class TooSoon(Exception):
    def __init__(self, seconds):
        super().__init__(f"請等 {seconds} 秒後再重寄")
        self.seconds = seconds


class LimitReached(Exception):
    pass


def required():
    return bool(current_app.config.get("EMAIL_FROM"))


def verified(member_id):
    return not required() or Member.is_verified(member_id)


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _base_url():
    # nginx talks plain HTTP to the app and says the visitor used HTTPS in this header.
    scheme = request.headers.get("X-Forwarded-Proto", request.scheme)
    return f"{scheme}://{request.host}"


def send_link(member_id, account, email):
    """Creates a link and e-mails it; raises TooSoon or LimitReached instead."""
    now = taipei_datetime()
    last = EmailToken.last_sent(member_id)
    if last and now - last < RESEND_AFTER:
        raise TooSoon(math.ceil((RESEND_AFTER - (now - last)).total_seconds()))
    midnight = now.replace(hour=0, minute=0, second=0)
    if EmailToken.sent_since(midnight, member_id) >= PER_MEMBER_DAILY:
        raise LimitReached("今天已經寄了很多次，請明天再試")
    if EmailToken.sent_since(midnight) >= DAILY_LIMIT:
        current_app.logger.warning("daily e-mail limit of %s reached", DAILY_LIMIT)
        raise LimitReached("今天的驗證信已達上限，請明天再試")
    EmailToken.purge(now)

    token = secrets.token_urlsafe(32)
    EmailToken.create(member_id, _hash(token), now, now + LINK_VALID)
    link = f"{_base_url()}{VERIFY_PATH}?token={token}"
    mailer.send(email, "請確認你的 MotiveTag Email", _text(account, link), _html(account, link))
    return link


def confirm(token):
    """Marks the link's member verified; returns their id, or None for a bad link."""
    if not isinstance(token, str) or not token:
        return None
    now = taipei_datetime()
    member_id = EmailToken.member_for(_hash(token), now)
    if member_id is not None:
        Member.mark_verified(member_id, now)
    return member_id


def _text(account, link):
    return (
        f"{account} 你好，\n\n"
        "請點下面的連結確認這是你的 Email，確認後就能發文、留言和交朋友：\n\n"
        f"{link}\n\n"
        "連結 24 小時內有效。如果你沒有註冊 MotiveTag，請忽略這封信。\n\n"
        "MotiveTag\n"
    )


def _html(account, link):
    name, url = html.escape(account), html.escape(link)
    return f"""<!doctype html>
<html lang="zh-TW"><body style="margin:0;padding:24px;background:#f4f6fb;font-family:sans-serif;color:#1b2140">
<table role="presentation" width="100%" style="max-width:480px;margin:auto;background:#fff;border-radius:12px;padding:32px">
<tr><td>
<h1 style="margin:0 0 16px;font-size:20px">確認你的 Email</h1>
<p style="line-height:1.6">{name} 你好，請按下面的按鈕確認這是你的 Email。確認後就能發文、留言和交朋友。</p>
<p style="margin:24px 0"><a href="{url}" style="display:inline-block;padding:12px 24px;border-radius:999px;background:#1cbfff;color:#04121b;font-weight:bold;text-decoration:none">確認 Email</a></p>
<p style="font-size:13px;color:#5b6385;line-height:1.6">按鈕沒反應的話，把這個網址貼到瀏覽器：<br><a href="{url}" style="color:#0a84c6;word-break:break-all">{url}</a></p>
<p style="font-size:13px;color:#5b6385">連結 24 小時內有效。如果你沒有註冊 MotiveTag，請忽略這封信。</p>
</td></tr></table>
</body></html>"""
