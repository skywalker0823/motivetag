"""NASA's Astronomy Picture of the Day, posted once a day by the member NASA_APOD.

scripts/apod.py runs `post_today()` from a systemd timer (deploy/systemd/
motivetag-apod.timer). The bot is an ordinary member nobody can sign in as (a random
password that is never stored), so its posts show in 探索 and under #APOD, and can be
liked, commented on and reported like any other.

Pictures: NASA's own are public domain and are copied to our bucket like an uploaded
photo. Many APOD pictures belong to their photographers (the `copyright` field); those
posts carry the credit and the link only, unless APOD_COPYRIGHTED_IMAGES=1.
Videos post their link.
"""

import json
import os
import secrets
import urllib.parse
import urllib.request

from data.data import Block, Block_tags, Member
from module import rules
from module.clock import taipei_datetime, taipei_now

BOT_ACCOUNT = "NASA_APOD"
BOT_EMAIL = "nasa_apod@bots.motivetag.com"
BOT_MOOD = "每天自動分享 NASA 每日天文圖（APOD）🔭"
API = "https://api.nasa.gov/planetary/apod"
TAGS = ["APOD", "天文", "NASA"]
IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
TIMEOUT = 30


def _get(url, limit=None):
    if not url.startswith("https://"):
        raise ValueError(f"not an https URL: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "MotiveTag APOD bot"})  # noqa: S310 - https only
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 - https only
        body = response.read(limit + 1 if limit else -1)
        return body, response.headers.get_content_type()


def fetch():
    """Today's APOD entry: {date, title, explanation, media_type, url, copyright?...}."""
    key = os.getenv("NASA_API_KEY") or "DEMO_KEY"  # DEMO_KEY: 30 calls an hour per IP
    body, _ = _get(f"{API}?{urllib.parse.urlencode({'api_key': key, 'thumbs': 'true'})}")
    return json.loads(body)


def page_url(date):
    """The APOD page for a YYYY-MM-DD date, e.g. https://apod.nasa.gov/apod/ap261005.html."""
    return f"https://apod.nasa.gov/apod/ap{date[2:4]}{date[5:7]}{date[8:10]}.html"


def compose(entry):
    """The post's text, within the site's length limit."""
    copyright = " ".join((entry.get("copyright") or "").split())
    credit = f"📷 {copyright}" if copyright else "📷 NASA（公有領域）"
    if entry.get("media_type") == "video":
        credit = f"🎬 這天是影片，請點連結觀看\n{credit}"
    elif copyright and not copyrighted_images():
        credit += "\n（圖片版權屬於攝影者，請點連結觀看）"
    head = f"🌌 NASA 每日天文圖 {entry['date']}\n{entry['title'].strip()}\n\n"
    tail = f"\n\n{credit}\n🔗 {page_url(entry['date'])}\n" + " ".join(f"#{t}" for t in TAGS)
    explanation = " ".join((entry.get("explanation") or "").split())
    room = rules.POST_MAX - len(head) - len(tail)
    if len(explanation) > room:
        explanation = explanation[: room - 1].rstrip() + "…"
    return head + explanation + tail


def copyrighted_images():
    return os.getenv("APOD_COPYRIGHTED_IMAGES") == "1"


def bot_id():
    """The bot's member_id, creating the account the first time."""
    member_id = Member.id_for(BOT_ACCOUNT)
    if member_id is not None:
        return member_id
    today = taipei_now()[:10]
    result = Member.sign_up(BOT_ACCOUNT, secrets.token_urlsafe(32), BOT_EMAIL, "2000-01-01", today)
    if result != "ok":
        raise RuntimeError(f"could not create {BOT_ACCOUNT}: {result}")
    member_id = Member.id_for(BOT_ACCOUNT)
    Member.mark_verified(member_id, taipei_datetime())
    Member.patch_user_data(member_id, "mood", BOT_MOOD)
    return member_id


def attach_image(block_id, entry):
    """Copies the picture to our bucket as the post's photo; False if it is skipped."""
    from api.blueprints.api_images import BUCKET_NAME, forget_signed, s3

    if entry.get("media_type") != "image" or not BUCKET_NAME:
        return False
    if entry.get("copyright") and not copyrighted_images():
        return False
    url = entry.get("url") or ""
    if not url.startswith("https://"):
        return False
    body, content_type = _get(url, MAX_IMAGE_BYTES)
    if len(body) > MAX_IMAGE_BYTES or content_type not in IMAGE_TYPES:
        return False
    key = f"block_{block_id}"
    s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=body, ContentType=content_type)
    forget_signed(key)
    Block.modify_block(block_id, key)
    return True


def post_today(entry=None):
    """Posts the current APOD unless the bot already has; returns what happened."""
    entry = entry or fetch()
    member_id = bot_id()
    page = page_url(entry["date"])
    if Block.posted_with(member_id, page):
        return {"posted": False, "date": entry["date"], "reason": "already posted"}
    content = compose(entry)
    result = Block.create_my_block(
        member_id, {"type": "PUBLIC", "content": content, "time": taipei_now()}
    )
    if result["msg"] != "ok":
        raise RuntimeError("could not create the post")
    block_id = result["content"]["block_id"]
    Block_tags.tag_into_block(TAGS, block_id, member_id)
    try:
        image = attach_image(block_id, entry)
    except Exception as exc:  # noqa: BLE001 - the text post stands without its picture
        print(f"APOD image skipped: {exc}")
        image = False
    return {"posted": True, "date": entry["date"], "block_id": block_id, "image": image}
