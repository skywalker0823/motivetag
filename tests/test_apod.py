"""The daily NASA APOD post (module/apod.py). NASA and S3 are faked."""

import pytest

from module import apod, rules

PUBLIC = {
    "date": "2026-10-05",
    "title": "The Pillars of Creation",
    "explanation": "Stars are forming in the Eagle Nebula. " * 10,
    "media_type": "image",
    "url": "https://apod.nasa.gov/apod/image/2610/pillars.jpg",
    "hdurl": "https://apod.nasa.gov/apod/image/2610/pillars_big.jpg",
    "service_version": "v1",
}


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
    monkeypatch.setattr(apod, "_get", lambda url, limit=None: (b"\xff\xd8jpeg-bytes", "image/jpeg"))
    query("DELETE FROM member WHERE account=%s", apod.BOT_ACCOUNT)
    with app.app_context():
        yield s3
    query("DELETE FROM member WHERE account=%s", apod.BOT_ACCOUNT)


def post_of(query, block_id):
    return query("SELECT content, block_img, content_type FROM block WHERE block_id=%s", block_id)[
        0
    ]


def test_public_domain_picture_is_posted_once_with_its_photo(nasa, query):
    result = apod.post_today(dict(PUBLIC))
    assert result["posted"] and result["image"]
    post = post_of(query, result["block_id"])
    assert post["content_type"] == "PUBLIC"
    assert post["content"].startswith("🌌 NASA 每日天文圖 2026-10-05\nThe Pillars of Creation")
    assert "https://apod.nasa.gov/apod/ap261005.html" in post["content"]
    assert "NASA（公有領域）" in post["content"]
    assert len(post["content"]) <= rules.POST_MAX
    assert post["block_img"] == f"block_{result['block_id']}"
    assert nasa.objects[post["block_img"]][1] == "image/jpeg"
    tags = query(
        "SELECT t.name FROM block_tag bt JOIN tag t ON t.tag_id = bt.tag_id WHERE bt.block_id=%s",
        result["block_id"],
    )
    assert {t["name"] for t in tags} == {"APOD", "天文", "NASA"}

    again = apod.post_today(dict(PUBLIC))
    assert again == {"posted": False, "date": "2026-10-05", "reason": "already posted"}


def test_bot_account_cannot_be_signed_into_or_taken(nasa, query, client):
    apod.post_today(dict(PUBLIC))
    bot = query("SELECT email_verified_at, mood FROM member WHERE account=%s", apod.BOT_ACCOUNT)[0]
    assert bot["email_verified_at"] and bot["mood"] == apod.BOT_MOOD
    body = {
        "account": "nasa_apod",
        "password": "long-enough-pw",
        "email": "someone@example.com",
        "birthday": "1990-1-1",
    }
    assert client.post("/api/member", json=body).status_code == 400


def test_copyrighted_picture_posts_credit_and_link_only(nasa, query, monkeypatch):
    monkeypatch.delenv("APOD_COPYRIGHTED_IMAGES", raising=False)
    entry = {**PUBLIC, "date": "2026-10-06", "copyright": "\nJane   Doe\n"}
    result = apod.post_today(entry)
    assert result["posted"] and not result["image"]
    post = post_of(query, result["block_id"])
    assert "📷 Jane Doe" in post["content"] and "版權屬於攝影者" in post["content"]
    assert post["block_img"] is None and not nasa.objects

    monkeypatch.setenv("APOD_COPYRIGHTED_IMAGES", "1")
    result = apod.post_today({**entry, "date": "2026-10-07"})
    assert result["image"]


def test_video_days_post_the_link(nasa, query):
    entry = {
        **PUBLIC,
        "date": "2026-10-08",
        "media_type": "video",
        "url": "https://www.youtube.com/embed/x",
    }
    result = apod.post_today(entry)
    assert result["posted"] and not result["image"]
    assert "影片" in post_of(query, result["block_id"])["content"]


def test_a_failed_download_keeps_the_text_post(nasa, query, monkeypatch):
    def broken(url, limit=None):
        raise OSError("network down")

    monkeypatch.setattr(apod, "_get", broken)
    result = apod.post_today({**PUBLIC, "date": "2026-10-09"})
    assert result["posted"] and not result["image"]


def test_long_explanations_are_cut_to_fit():
    text = apod.compose({**PUBLIC, "explanation": "word " * 1000})
    assert len(text) == rules.POST_MAX and "…" in text and text.endswith("#APOD #天文 #NASA")
