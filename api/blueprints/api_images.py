import os
import re
import time

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from flask import abort, redirect, request, session

from data.data import Block, Images
from module.auth import login_required

from . import api_images

# Browsers upload straight to S3 with a presigned POST (docs/adr/0007); the app only
# signs the upload and records the key afterwards, so image bytes never pass through
# nginx or gunicorn.
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
UPLOAD_EXPIRES = 300

# Credentials come from the EC2 instance role; the bucket stays private and
# images are served through short-lived presigned URLs.
BUCKET_NAME = os.getenv("IMAGE_BUCKET")
REGION = os.getenv("AWS_REGION")
IMAGE_KEY = re.compile(r"^(avatar|block)_\d+$")
s3 = boto3.client(
    "s3",
    region_name=REGION,
    # The regional endpoint: the global one does not serve buckets in opt-in regions
    # such as ap-east-2, and browsers do not follow its redirects on a CORS POST.
    endpoint_url=f"https://s3.{REGION}.amazonaws.com" if REGION else None,
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)


def image_key(member_id, kind, target_id):
    """The S3 key this member may write for kind/target_id, or an error response."""
    if kind == "avatar":
        return f"avatar_{member_id}", None
    if kind == "block":
        try:
            block_id = int(target_id)
        except (TypeError, ValueError):
            return None, ({"error": "block not found or not yours"}, 403)
        if not Block.is_owner(member_id, block_id):
            return None, ({"error": "block not found or not yours"}, 403)
        return f"block_{block_id}", None
    return None, ({"error": "unknown image type"}, 400)


DEFAULT_AVATAR = "/img/avatar.svg"
# Browsers keep the redirect for a while, so a feed full of the same avatars does not
# ask again on every page. Shorter than the presigned URL's hour so it never goes stale.
REDIRECT_CACHE = "private, max-age=600"

# A presigned URL is handed out again for half its lifetime. Browsers cache images by
# URL, and a fresh signature on every request would make each one a new download; it
# also saves a database lookup per image. In memory is fine: one worker (ADR 0008).
SIGNED_LIFETIME = 3600
SIGNED_REUSE = SIGNED_LIFETIME // 2
_signed = {}  # {key: (url, signed_at)}


def _recently_signed(key):
    cached = _signed.get(key)
    return cached is not None and time.monotonic() - cached[1] < SIGNED_REUSE


def signed_image_url(key):
    """A presigned GET for `key`, the same one while it has at least half its life left."""
    if _recently_signed(key):
        return _signed[key][0]
    now = time.monotonic()
    url = s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": BUCKET_NAME,
            "Key": key,
            # S3 sends this header back, so the browser caches the image itself too;
            # never longer than the URL stays valid.
            "ResponseCacheControl": f"private, max-age={SIGNED_REUSE}",
        },
        ExpiresIn=SIGNED_LIFETIME,
    )
    if len(_signed) > 10_000:  # drop expired entries now and then
        for stale in [k for k, (_, at) in _signed.items() if now - at >= SIGNED_REUSE]:
            del _signed[stale]
    _signed[key] = (url, now)
    return url


def forget_signed(key):
    """A new image was uploaded under `key`: the next request signs a new URL."""
    _signed.pop(key, None)


@api_images.route("/images/<key>")
def show_img(key):
    if not IMAGE_KEY.match(key):
        abort(404)
    kind, _, ident = key.partition("_")
    # A secret post's image is as private as the post (block ids are easy to guess).
    if kind == "block" and not Block.visible(session.get("member_id"), int(ident)):
        abort(404)
    if _recently_signed(key):  # so it existed a moment ago; skip the lookup
        url = signed_image_url(key)
    elif kind == "avatar" and (not BUCKET_NAME or not Images.has_avatar(int(ident))):
        response = redirect(DEFAULT_AVATAR)
        response.headers["Cache-Control"] = REDIRECT_CACHE
        return response
    elif kind == "block" and (not BUCKET_NAME or not Images.has_block_image(int(ident))):
        abort(404)
    else:
        url = signed_image_url(key)
    response = redirect(url)
    response.headers["Cache-Control"] = REDIRECT_CACHE
    return response


@api_images.route("/api/images/upload", methods=["POST"])
@login_required
def sign_upload():
    """Step 1: return a presigned POST the browser sends the file to."""
    body = request.get_json(silent=True) or {}
    content_type = body.get("content_type")
    if content_type not in ALLOWED_TYPES:
        return {"error": "file type not allowed"}, 400
    if not BUCKET_NAME:
        return {"error": "image uploads are disabled"}, 503
    key, error = image_key(session["member_id"], body.get("type"), body.get("target_id"))
    if error:
        return error
    post = s3.generate_presigned_post(
        BUCKET_NAME,
        key,
        Fields={"Content-Type": content_type},
        Conditions=[
            {"Content-Type": content_type},
            ["content-length-range", 1, MAX_IMAGE_BYTES],
        ],
        ExpiresIn=UPLOAD_EXPIRES,
    )
    return {"ok": True, "url": post["url"], "fields": post["fields"]}


@api_images.route("/api/images", methods=["POST"])
@login_required
def finish_upload():
    """Step 2: after the browser's upload succeeded, point the avatar or block at it."""
    body = request.get_json(silent=True) or {}
    member_id = session["member_id"]
    key, error = image_key(member_id, body.get("type"), body.get("target_id"))
    if error:
        return error
    try:
        head = s3.head_object(Bucket=BUCKET_NAME, Key=key)
    except ClientError:
        return {"error": "upload not found"}, 400
    if head.get("ContentType") not in ALLOWED_TYPES:
        return {"error": "file type not allowed"}, 400
    forget_signed(key)
    if key.startswith("avatar_"):
        result = Images.post_image(member_id, key)
    else:
        result = Block.modify_block(int(key.removeprefix("block_")), key)
    return {"ok": result}
