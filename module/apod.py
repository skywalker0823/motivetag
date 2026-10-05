"""NASA's Astronomy Picture of the Day, posted once a day by the member NASA_APOD.

scripts/apod.py runs `post_today()` from a systemd timer (deploy/systemd/
motivetag-apod.timer). The bot is an ordinary member nobody can sign in as (a random
password that is never stored), so its posts show in 探索 and under #APOD, and can be
liked, commented on and reported like any other.

The day's page on apod.nasa.gov is read directly. (api.nasa.gov's APOD API scrapes the
same page and broke on 2026-10-05: title "NASA Science", NASA's logo as the picture,
and no copyright for a photographer's picture.) APOD's pictures always live under
apod.nasa.gov/apod/image/, and its credit line says "Copyright" when the picture
belongs to the photographer.

Pictures without a copyright are copied to our bucket like an uploaded photo; a
photographer's picture posts the credit and link only, unless
APOD_COPYRIGHTED_IMAGES=1. When the credit cannot be read, the picture counts as
copyrighted. Videos post their link.
"""

import html
import os
import re
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

from data.data import Block, Block_tags, Member
from module import rules
from module.clock import taipei_datetime, taipei_now

BOT_ACCOUNT = "NASA_APOD"
BOT_EMAIL = "nasa_apod@bots.motivetag.com"
BOT_MOOD = "每天自動分享 NASA 每日天文圖（APOD）🔭"
SITE = "https://apod.nasa.gov/apod/"
APOD_ZONE = ZoneInfo("America/New_York")  # APOD's day changes at midnight there
TAGS = ["APOD", "天文", "NASA"]
IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
TIMEOUT = 30

IMAGE = re.compile(
    r"""<img[^>]+src\s*=\s*["']?((?:https://apod\.nasa\.gov/apod/)?image/\d{4}/[^"'\s>]+)""", re.I
)
IMAGE_LINK = re.compile(
    r"""href\s*=\s*["']?((?:https://apod\.nasa\.gov/apod/)?image/\d{4}/[^"'\s>]+\.(?:jpe?g|png|gif))""",
    re.I,
)
IFRAME = re.compile(r"""<iframe[^>]+src\s*=\s*["']?([^"'\s>]+)""", re.I)
BOLD = re.compile(r"<b>(.*?)</b>", re.I | re.S)
TITLE_TAG = re.compile(r"<title>\s*APOD:[^<]*?-\s*(.*?)\s*</title>", re.I | re.S)
EXPLANATION = re.compile(r"Explanation\s*:?\s*(?:</b>)?(.*)", re.I | re.S)
EXPLANATION_END = re.compile(
    r"<p>\s*<center>|Tomorrow(?:'|&#0?39;|&rsquo;|’)s picture|Your Sky Surprise", re.I
)
CREDIT_LABEL = re.compile(
    r"^(?:image|video|illustration|animation|data)?[\s,&]*credits?[\w\s,&]*?:\s*", re.I
)
NOT_TITLES = re.compile(r"credit|copyright|explanation|tomorrow|^nasa science$", re.I)


class _Missing(Exception):
    """The day's page does not exist (yet)."""


def _get(url, limit=None):
    if not url.startswith("https://"):
        raise ValueError(f"not an https URL: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "MotiveTag APOD bot"})  # noqa: S310 - https only
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 - https only
            body = response.read(limit + 1 if limit else -1)
            return body, response.headers.get_content_type()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise _Missing(url) from exc
        raise


def apod_today():
    """Today's date in APOD's time zone, YYYY-MM-DD."""
    return datetime.now(APOD_ZONE).strftime("%Y-%m-%d")


def page_url(date):
    """The APOD page for a YYYY-MM-DD date, e.g. https://apod.nasa.gov/apod/ap261005.html."""
    return f"{SITE}ap{date[2:4]}{date[5:7]}{date[8:10]}.html"


def _text(fragment):
    """Visible text of an HTML fragment: tags dropped, entities decoded, spaces collapsed."""
    text = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", fragment)).split())
    return re.sub(r" ([,.;:!?)])", r"\1", text)  # "<a>NASA</a>, ESA" → "NASA, ESA"


def parse(page, date):
    """The entry for one APOD page: {date, title, explanation, media_type, url, credit,
    copyright}. `url` is the picture (only ever under apod.nasa.gov/apod/image/) or
    the video; `copyright` is True when the credit says so or cannot be read."""
    base = page_url(date)
    image = IMAGE.search(page) or IMAGE_LINK.search(page)
    start = image.end() if image else 0
    title, title_end = "", None
    for match in BOLD.finditer(page, start):
        text = _text(match.group(1))
        if text and not NOT_TITLES.search(text):
            title, title_end = text, match.end()
            break
    if not title:
        tag = TITLE_TAG.search(page)
        title = _text(tag.group(1)) if tag else ""
    explanation_match = EXPLANATION.search(page, title_end or start)
    explanation = ""
    credit_html = None
    if explanation_match:
        body = explanation_match.group(1)
        end = EXPLANATION_END.search(body)
        explanation = _text(body[: end.start()] if end else body)
        if title_end is not None:
            credit_html = page[title_end : explanation_match.start()]
    credit = _text(credit_html or "")
    copyrighted = credit_html is None or "copyright" in credit.lower() or "©" in credit
    credit = CREDIT_LABEL.sub("", credit).strip(" :")
    if image:
        media_type, url = "image", urllib.parse.urljoin(base, image.group(1))
    else:
        video = IFRAME.search(page)
        media_type, url = ("video", video.group(1)) if video else ("other", None)
    return {
        "date": date,
        "title": title,
        "explanation": explanation,
        "media_type": media_type,
        "url": url,
        "credit": credit,
        "copyright": copyrighted,
    }


def fetch(date=None):
    """The APOD entry for `date` (default: today in APOD's time zone), or None when
    that day's page is not up yet."""
    date = date or apod_today()
    try:
        body, _ = _get(page_url(date))
    except _Missing:
        return None
    return parse(body.decode("utf-8", "replace"), date)


def compose(entry):
    """The post's text, within the site's length limit."""
    credit = entry.get("credit") or ""
    if entry.get("copyright"):
        line = f"📷 {credit}（版權屬於攝影者）" if credit else "📷 版權屬於攝影者"
    else:
        line = f"📷 {credit or 'NASA'}"
    if entry.get("media_type") != "image":
        line = f"🎬 這天不是照片（可能是影片），請點連結觀看\n{line}"
    elif entry.get("copyright") and not copyrighted_images():
        line += "\n請點連結觀看照片"
    title = entry.get("title") or "（無標題）"
    head = f"🌌 NASA 每日天文圖 {entry['date']}\n{title}\n\n"
    tail = f"\n\n{line}\n🔗 {page_url(entry['date'])}\n" + " ".join(f"#{t}" for t in TAGS)
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
    if not url.startswith(SITE + "image/"):
        return False
    body, content_type = _get(url, MAX_IMAGE_BYTES)
    if len(body) > MAX_IMAGE_BYTES or content_type not in IMAGE_TYPES:
        return False
    key = f"block_{block_id}"
    s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=body, ContentType=content_type)
    forget_signed(key)
    Block.modify_block(block_id, key)
    return True


def post_today(entry=None, replace=False):
    """Posts the current APOD unless the bot already has; returns what happened.
    `replace` deletes the bot's post for that day first (to fix a bad one)."""
    entry = entry or fetch()
    if entry is None:
        return {"posted": False, "date": apod_today(), "reason": "not published yet"}
    if not entry["title"] or not entry["explanation"]:
        # The page looks nothing like APOD's: better no post than a wrong one.
        raise RuntimeError(f"could not read the APOD page for {entry['date']}")
    member_id = bot_id()
    page = page_url(entry["date"])
    if replace:
        from api.v1.account import remove_images  # the blueprints import v1

        for block_id, image in Block.with_text(member_id, page):
            Block.delete_block(member_id, block_id)
            if image:
                remove_images([image])
    elif Block.posted_with(member_id, page):
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
