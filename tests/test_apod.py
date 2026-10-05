"""The daily NASA APOD post (module/apod.py). apod.nasa.gov and S3 are faked."""

from pathlib import Path

import pytest

from module import apod, rules

# The real page for 2026-10-05 (a photographer's picture), and variants of it.
REAL = (Path(__file__).parent / "fixtures" / "apod_2026-10-05.html").read_text()
# A picture without a copyright, on 2026-10-06.
FREE = (
    REAL.replace("October 5, 2026", "October 6, 2026")
    .replace("Credit &amp; Copyright", "Credit")
    .replace("Engelbert Vollmer</a>", "NASA</a>, ESA, CSA, STScI")
)
# A video day on 2026-10-07.
VIDEO = (
    REAL.replace("October 5, 2026", "October 7, 2026")
    .replace(
        '<figure class="hds-media-inner',
        '<iframe width="960" height="540" src="https://www.youtube.com/embed/abc123"></iframe><figure class="x',
    )
    .replace("<img width=", "<span width=")
)


def test_reads_the_real_page():
    entry = apod.parse(REAL, "2026-10-05")
    assert entry["title"] == "M104: The Sombrero Galaxy's Tidal Streams"
    assert entry["url"].startswith(
        "https://assets.science.nasa.gov/dynamicimage/assets/science/cds/apod/apod/2026/october/M104_Vollmer_4222.jpg?"
    )
    assert entry["link"] == (
        "https://science.nasa.gov/image-article/apod-2026-october-5-m104-the-sombrero-galaxys-tidal-streams/"
    )
    assert entry["media_type"] == "image"
    assert entry["copyright"] is True and entry["credit"] == "Engelbert Vollmer"
    assert entry["explanation"].startswith(
        "A deep image of the Sombrero galaxy reveals surprises. M104"
    )
    assert entry["explanation"].endswith("taken over seven days in mid-2026 from Namibia.")
    assert "Your Sky Surprise" not in entry["explanation"]


def test_a_page_showing_another_day_is_not_up_yet():
    assert apod.parse(REAL, "2026-10-06") is None


def test_free_picture_and_video_variants():
    free = apod.parse(FREE, "2026-10-06")
    assert free["copyright"] is False and free["credit"] == "NASA, ESA, CSA, STScI"
    video = apod.parse(VIDEO, "2026-10-07")
    assert video["media_type"] == "video" and video["url"] == "https://www.youtube.com/embed/abc123"


def test_unreadable_credit_counts_as_copyrighted():
    page = FREE.replace(">Credit<", ">Source<")
    assert apod.parse(page, "2026-10-06")["copyright"] is True


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, Bucket, Key, Body, ContentType):  # noqa: N803 - boto3's names
        self.objects[Key] = (Body, ContentType)


@pytest.fixture()
def nasa(monkeypatch, app, query):
    """Fake picture downloads and S3; a fresh bot each test."""
    from api.blueprints import api_images as images

    s3 = FakeS3()
    monkeypatch.setattr(images, "s3", s3)
    monkeypatch.setattr(apod, "_get", lambda url, limit=None: (b"\x89PNG-bytes", "image/png"))
    monkeypatch.delenv("APOD_COPYRIGHTED_IMAGES", raising=False)
    query("DELETE FROM member WHERE account=%s", apod.BOT_ACCOUNT)
    with app.app_context():
        yield s3
    query("DELETE FROM member WHERE account=%s", apod.BOT_ACCOUNT)


def post_of(query, block_id):
    return query("SELECT content, block_img, content_type FROM block WHERE block_id=%s", block_id)[
        0
    ]


def test_free_picture_is_posted_once_with_its_photo(nasa, query):
    entry = apod.parse(FREE, "2026-10-06")
    result = apod.post_today(entry)
    assert result["posted"] and result["image"]
    post = post_of(query, result["block_id"])
    assert post["content_type"] == "PUBLIC"
    assert post["content"].startswith(
        "🌌 NASA 每日天文圖 2026-10-06\nM104: The Sombrero Galaxy's Tidal Streams\n\nA deep image"
    )
    assert (
        "📷 NASA, ESA, CSA, STScI\n🔗 https://science.nasa.gov/image-article/apod-2026-october-5-"
        in post["content"]
    )
    assert post["block_img"] == f"block_{result['block_id']}"
    assert nasa.objects[post["block_img"]][1] == "image/png"
    tags = query(
        "SELECT t.name FROM block_tag bt JOIN tag t ON t.tag_id = bt.tag_id WHERE bt.block_id=%s",
        result["block_id"],
    )
    assert {t["name"] for t in tags} == {"APOD", "天文", "NASA"}

    assert apod.post_today(entry)["reason"] == "already posted"

    again = apod.post_today(entry, replace=True)
    assert again["posted"] and again["block_id"] != result["block_id"]
    assert not query("SELECT 1 FROM block WHERE block_id=%s", result["block_id"])


def test_photographers_picture_posts_credit_and_link_only(nasa, query, monkeypatch):
    entry = apod.parse(REAL, "2026-10-05")
    result = apod.post_today(entry)
    assert result["posted"] and not result["image"]
    post = post_of(query, result["block_id"])
    assert "📷 Engelbert Vollmer（版權屬於攝影者）\n請點連結觀看照片" in post["content"]
    assert post["block_img"] is None and not nasa.objects

    monkeypatch.setenv("APOD_COPYRIGHTED_IMAGES", "1")
    assert apod.post_today(entry, replace=True)["image"]


def test_only_apod_pictures_are_copied(nasa):
    entry = {**apod.parse(FREE, "2026-10-06"), "url": "https://science.nasa.gov/logo.png"}
    assert apod.post_today(entry)["image"] is False and not nasa.objects


def test_video_days_post_the_link(nasa, query):
    result = apod.post_today(apod.parse(VIDEO, "2026-10-07"))
    assert result["posted"] and not result["image"]
    assert "不是照片" in post_of(query, result["block_id"])["content"]


def test_a_page_that_cannot_be_read_posts_nothing(nasa, query):
    with pytest.raises(RuntimeError):
        apod.post_today(apod.parse("<html>NASA Science</html>", "2026-10-08"))
    assert not query("SELECT 1 FROM member WHERE account=%s", apod.BOT_ACCOUNT)


def test_page_not_up_yet(monkeypatch, nasa):
    def missing(url, limit=None):
        raise apod._Missing(url)

    monkeypatch.setattr(apod, "_get", missing)
    assert apod.fetch("2026-10-09") is None
    assert apod.post_today(None)["reason"] == "not published yet"


def test_a_failed_download_keeps_the_text_post(nasa, monkeypatch):
    def broken(url, limit=None):
        raise OSError("network down")

    monkeypatch.setattr(apod, "_get", broken)
    result = apod.post_today(apod.parse(FREE, "2026-10-06"))
    assert result["posted"] and not result["image"]


def test_bot_account_cannot_be_taken(nasa, query, client):
    apod.post_today(apod.parse(FREE, "2026-10-06"))
    bot = query("SELECT email_verified_at, mood FROM member WHERE account=%s", apod.BOT_ACCOUNT)[0]
    assert bot["email_verified_at"] and bot["mood"] == apod.BOT_MOOD
    body = {
        "account": "nasa_apod",
        "password": "long-enough-pw",
        "email": "someone@example.com",
        "birthday": "1990-1-1",
    }
    assert client.post("/api/member", json=body).status_code == 400


def test_long_explanations_are_cut_to_fit():
    entry = {**apod.parse(FREE, "2026-10-06"), "explanation": "word " * 1000}
    text = apod.compose(entry)
    assert (
        rules.POST_MAX - 2 <= len(text) <= rules.POST_MAX
        and "…" in text
        and text.endswith("#APOD #天文 #NASA")
    )


def test_the_picture_is_fetched_resized(nasa, monkeypatch):
    asked = []

    def fake_get(url, limit=None):
        asked.append(url)
        return b"\xff\xd8jpeg", "image/jpeg"

    monkeypatch.setattr(apod, "_get", fake_get)
    assert apod.post_today(apod.parse(FREE, "2026-10-06"))["image"]
    assert asked == [
        "https://assets.science.nasa.gov/dynamicimage/assets/science/cds/apod/apod/2026/october/"
        "M104_Vollmer_4222.jpg?w=2048&fit=clip"
    ]
