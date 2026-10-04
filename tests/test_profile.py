"""Personal cards and the site look (api/v1/profile.py)."""

import importlib

import pytest

api_images = importlib.import_module("api.blueprints.api_images")


def test_card_colours_are_saved_and_shown_to_others(member):
    alice, alice_id, _ = member()
    bob, _, _ = member()
    saved = alice.put("/api/v1/me/card", json={"accent": "#FF6FB5", "name_color": "#ffffff"})
    assert saved.status_code == 200
    assert saved.get_json()["data"] == {
        "accent": "#ff6fb5",
        "cover_from": None,
        "cover_to": None,
        "name_color": "#ffffff",
        "cover": None,
    }
    card = bob.get(f"/api/get_user_sp?member_id={alice_id}").get_json()["card"]
    assert card["accent"] == "#ff6fb5" and card["name_color"] == "#ffffff"
    # Leaving a field out keeps it; null resets it.
    alice.put("/api/v1/me/card", json={"cover_from": "#000000"})
    reset = alice.put("/api/v1/me/card", json={"accent": None}).get_json()["data"]
    assert reset["accent"] is None and reset["cover_from"] == "#000000"


@pytest.mark.parametrize("value", ["red", "#fff", "#12345g", "url(x)", 5])
def test_only_hex_colours(member, value):
    alice, _, _ = member()
    assert alice.put("/api/v1/me/card", json={"accent": value}).status_code == 400


def test_new_members_have_the_default_card(member):
    alice, alice_id, _ = member()
    data = alice.get("/api/v1/me/profile").get_json()["data"]
    assert data["card"]["cover"] is None and data["ui"] == {
        "mode": None,
        "accent": None,
        "text": None,
    }
    assert data["cover_level"] == 5
    assert alice_id


def test_look_is_saved_and_sent_with_the_page(member):
    alice, _, account = member()
    assert alice.put("/api/v1/me/ui", json={"mode": "light", "accent": "pink"}).status_code == 200
    assert alice.put("/api/v1/me/ui", json={"text": "large"}).get_json()["data"] == {
        "mode": "light",
        "accent": "pink",
        "text": "large",
    }
    assert alice.put("/api/v1/me/ui", json={"mode": "neon"}).status_code == 400
    page = alice.get(f"/{account}").get_data(as_text=True)
    assert 'data-mode="light"' in page and 'data-accent="pink"' in page
    assert 'data-text="large"' in page


@pytest.fixture()
def uploaded(monkeypatch):
    monkeypatch.setattr(api_images.s3, "head_object", lambda **kw: {"ContentType": "image/webp"})


def test_cover_photo_needs_level_five(member, query, uploaded):
    alice, alice_id, _ = member()
    sign = {"type": "cover", "content_type": "image/webp"}
    assert alice.post("/api/images/upload", json=sign).status_code == 403
    query("UPDATE member SET exp=800 WHERE member_id=%s", alice_id)  # Lv 5
    signed = alice.post("/api/images/upload", json=sign).get_json()
    assert signed["fields"]["key"] == f"cover_{alice_id}"
    assert alice.post("/api/images", json={"type": "cover"}).get_json()["ok"]
    cover = alice.get("/api/v1/me/profile").get_json()["data"]["card"]["cover"]
    assert cover.startswith(f"/images/cover_{alice_id}?v=")
    assert alice.get(f"/images/cover_{alice_id}").status_code == 302


def test_removing_the_cover(member, query, uploaded, monkeypatch):
    alice, alice_id, account = member()
    query("UPDATE member SET exp=800 WHERE member_id=%s", alice_id)
    alice.post("/api/images", json={"type": "cover"})
    removed = []
    monkeypatch.setattr("api.v1.profile.remove_images", lambda keys: removed.extend(keys))
    assert alice.delete("/api/v1/me/card/cover").get_json()["data"]["cover"] is None
    assert removed == [f"cover_{alice_id}"]
    assert alice.get(f"/images/cover_{alice_id}").status_code == 404
    # And deleting the account takes the cover along.
    alice.post("/api/images", json={"type": "cover"})
    gone = []
    monkeypatch.setattr("api.v1.account.remove_images", lambda keys: gone.extend(keys))
    alice.delete("/api/v1/account", json={"password": account + "-pw"})
    assert f"cover_{alice_id}" in gone
