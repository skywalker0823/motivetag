"""A member's personal card (colours for everyone, a cover photo from Lv 5) and their
look for the whole site (mode, accent colour, text size), kept with the account so it
follows them to every device.

The card: {accent, cover_from, cover_to, name_color, cover}; colours are "#rrggbb" or
null for the default, `cover` is the photo's URL or null. The cover photo is uploaded
like an avatar (POST /api/images/upload with type "cover", then POST /api/images).
"""

import re

from flask import request, session

from data.data import Level, Profile
from module import levels
from module.clock import taipei_datetime

from . import error, login_required, v1
from .account import remove_images

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
# Shown as a small icon next to the name (static/js/lib/gender.js); null shows nothing.
GENDERS = {"male", "female", "nonbinary"}
CARD_FIELDS = {
    "accent": "card_accent",
    "cover_from": "cover_from",
    "cover_to": "cover_to",
    "name_color": "name_color",
}
# The choices the settings offer; static/css/base.css has what each looks like.
UI_CHOICES = {
    "mode": ("ui_mode", {"dark", "light", "black"}),
    "accent": ("ui_accent", {"sky", "violet", "green", "pink", "orange", "gold"}),
    "text": ("ui_text", {"normal", "large"}),
}


def card_of(member_id, profile=None):
    profile = profile or Profile.get(member_id)
    cover = None
    if profile["cover_img"]:
        # A new photo keeps its key, so the version makes browsers fetch it again.
        version = int(profile["updated_at"].timestamp()) if profile["updated_at"] else 0
        cover = f"/images/{profile['cover_img']}?v={version}"
    return {
        **{name: profile[column] for name, column in CARD_FIELDS.items()},
        "cover": cover,
        "gender": profile["gender"],
    }


def ui_of(profile):
    return {name: profile[column] for name, (column, _) in UI_CHOICES.items()}


def settings_of(member_id):
    """{card, ui, cover_level} for my own page."""
    profile = Profile.get(member_id)
    return {
        "card": card_of(member_id, profile),
        "ui": ui_of(profile),
        "cover_level": levels.COVER_LEVEL,
    }


@v1.route("/me/profile", methods=["GET"])
@login_required
def my_profile():
    return {"data": settings_of(session["member_id"])}


@v1.route("/me/card", methods=["PUT"])
@login_required
def update_card():
    """Any of {accent, cover_from, cover_to, name_color}: "#rrggbb", or null to reset."""
    body = request.get_json(silent=True) or {}
    values = {}
    for name, column in CARD_FIELDS.items():
        if name not in body:
            continue
        value = body[name]
        if value is not None and not (isinstance(value, str) and HEX.match(value)):
            return error("bad_color", "顏色格式需為 #rrggbb", 400)
        values[column] = value.lower() if value else None
    Profile.update(session["member_id"], values, taipei_datetime())
    return {"data": card_of(session["member_id"])}


@v1.route("/me/card/cover", methods=["DELETE"])
@login_required
def remove_cover():
    me = session["member_id"]
    key = Profile.get(me)["cover_img"]
    if key:
        Profile.update(me, {"cover_img": None}, taipei_datetime())
        remove_images([key])
    return {"data": card_of(me)}


@v1.route("/me/ui", methods=["PUT"])
@login_required
def update_ui():
    """Any of {mode: dark|light|black, accent: sky|violet|green|pink|orange|gold,
    text: normal|large}."""
    body = request.get_json(silent=True) or {}
    values = {}
    for name, (column, allowed) in UI_CHOICES.items():
        if name in body:
            if body[name] not in allowed:
                return error("bad_choice", f"{name} 的選項無效", 400)
            values[column] = body[name]
    me = session["member_id"]
    Profile.update(me, values, taipei_datetime())
    return {"data": ui_of(Profile.get(me))}


@v1.route("/me/gender", methods=["PUT"])
@login_required
def update_gender():
    """{gender: "male" | "female" | "nonbinary" | null}; null shows no icon."""
    gender = (request.get_json(silent=True) or {}).get("gender")
    if gender is not None and gender not in GENDERS:
        return error("bad_gender", "性別選項無效", 400)
    me = session["member_id"]
    Profile.update(me, {"gender": gender}, taipei_datetime())
    return {"data": {"gender": gender}}


def may_have_cover(member_id):
    return levels.level_of(Level.exps([member_id]).get(member_id)) >= levels.COVER_LEVEL
