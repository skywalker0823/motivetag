"""The daily NASA APOD post (module/apod.py). apod.nasa.gov and S3 are faked."""

import pytest

from module import apod, rules

# APOD's long-standing page layout (copyrighted picture by a photographer).
CLASSIC = """<html><head><title> APOD: 2026 October 5 - The Sombrero Galaxy's Hairy Past
</title></head><body>
<center><h1> Astronomy Picture of the Day </h1>
<p><a href="archivepix.html">Discover the cosmos!</a></p>
<p>2026 October 5<br>
<a href="image/2610/Sombrero_Lopez_4000.jpg">
<IMG SRC="image/2610/Sombrero_Lopez_1080.jpg" alt="The Sombrero galaxy" style="max-width:100%"></a>
</center>
<center>
<b> The Sombrero Galaxy's Hairy Past </b> <br>
<b> Image Credit &amp;
<a href="lib/about_apod.html#srapply">Copyright</a>: </b>
<a href="https://example.com/">Ana L&oacute;pez</a>
</center> <p>
<b> Explanation: </b> A deep image of the Sombrero galaxy reveals surprises.
M104 is named the <a href="https://en.wikipedia.org/wiki/Sombrero">Sombrero</a> galaxy.
<p> <center>
<b> Your Sky Surprise: </b> What picture did APOD feature on your birthday?
<b> Tomorrow's picture: </b> a smile
</center></body></html>"""

# The same page with a NASA Science header and logo above it (what broke api.nasa.gov),
# and a NASA picture without a copyright.
WITH_HEADER = """<html><head><title>NASA Science</title></head><body>
<header><img src="https://science.nasa.gov/wp-content/themes/nasa-child/assets/images/nasa-logo@2x.png">
<b>NASA Science</b></header>
<center><p>2026 October 6<br>
<a href="image/2610/Pillars_Webb_2048.png"><img src="image/2610/Pillars_Webb_1024.png"></a></center>
<center><b> Pillars of Creation </b><br>
<b> Image Credit: </b> <a href="https://www.nasa.gov/">NASA</a>, ESA, CSA, STScI</center>
<p><b> Explanation: </b> Stars are forming in the Eagle Nebula.
Tomorrow&#039;s picture: open space
</body></html>"""

VIDEO = """<html><head><title> APOD: 2026 October 7 - A Total Eclipse </title></head><body>
<center><p>2026 October 7<br>
<iframe width="960" height="540" src="https://www.youtube.com/embed/abc123"></iframe></center>
<center><b> A Total Eclipse </b><br><b> Video Credit: </b> NASA</center>
<p><b> Explanation: </b> The Moon covers the Sun.
<p> <center> <b> Tomorrow's picture: </b> x </center></body></html>"""


def test_reads_apods_classic_page():
    entry = apod.parse(CLASSIC, "2026-10-05")
    assert entry["title"] == "The Sombrero Galaxy's Hairy Past"
    assert entry["url"] == "https://apod.nasa.gov/apod/image/2610/Sombrero_Lopez_1080.jpg"
    assert entry["media_type"] == "image"
    assert entry["copyright"] is True and entry["credit"] == "Ana López"
    assert entry["explanation"] == (
        "A deep image of the Sombrero galaxy reveals surprises. M104 is named the Sombrero galaxy."
    )


def test_ignores_the_nasa_science_header():
    entry = apod.parse(WITH_HEADER, "2026-10-06")
    assert entry["title"] == "Pillars of Creation"
    assert entry["url"] == "https://apod.nasa.gov/apod/image/2610/Pillars_Webb_1024.png"
    assert entry["copyright"] is False and entry["credit"] == "NASA, ESA, CSA, STScI"
    assert entry["explanation"] == "Stars are forming in the Eagle Nebula."


def test_video_days():
    entry = apod.parse(VIDEO, "2026-10-07")
    assert entry["media_type"] == "video" and entry["url"] == "https://www.youtube.com/embed/abc123"
    assert entry["title"] == "A Total Eclipse" and entry["copyright"] is False


def test_unreadable_credit_counts_as_copyrighted():
    page = CLASSIC.replace("Explanation:", "Story:")
    entry = apod.parse(page, "2026-10-05")
    assert entry["copyright"] is True and entry["explanation"] == ""


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
    entry = apod.parse(WITH_HEADER, "2026-10-06")
    result = apod.post_today(entry)
    assert result["posted"] and result["image"]
    post = post_of(query, result["block_id"])
    assert post["content_type"] == "PUBLIC"
    assert post["content"].startswith("🌌 NASA 每日天文圖 2026-10-06\nPillars of Creation\n\n")
    assert (
        "📷 NASA, ESA, CSA, STScI\n🔗 https://apod.nasa.gov/apod/ap261006.html" in post["content"]
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
    entry = apod.parse(CLASSIC, "2026-10-05")
    result = apod.post_today(entry)
    assert result["posted"] and not result["image"]
    post = post_of(query, result["block_id"])
    assert "📷 Ana López（版權屬於攝影者）\n請點連結觀看照片" in post["content"]
    assert post["block_img"] is None and not nasa.objects

    monkeypatch.setenv("APOD_COPYRIGHTED_IMAGES", "1")
    assert apod.post_today(entry, replace=True)["image"]


def test_only_apod_pictures_are_copied(nasa):
    entry = {**apod.parse(WITH_HEADER, "2026-10-06"), "url": "https://science.nasa.gov/logo.png"}
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
    result = apod.post_today(apod.parse(WITH_HEADER, "2026-10-06"))
    assert result["posted"] and not result["image"]


def test_bot_account_cannot_be_taken(nasa, query, client):
    apod.post_today(apod.parse(WITH_HEADER, "2026-10-06"))
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
    entry = {**apod.parse(WITH_HEADER, "2026-10-06"), "explanation": "word " * 1000}
    text = apod.compose(entry)
    assert (
        rules.POST_MAX - 2 <= len(text) <= rules.POST_MAX
        and "…" in text
        and text.endswith("#APOD #天文 #NASA")
    )
