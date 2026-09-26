import os
import re
import traceback

import boto3
from botocore.config import Config
from flask import abort, redirect, request, session

from data.data import Block, Images
from module.auth import login_required

from . import api_images

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Credentials come from the EC2 instance role; the bucket stays private and
# images are served through short-lived presigned URLs.
BUCKET_NAME = os.getenv("IMAGE_BUCKET")
IMAGE_KEY = re.compile(r"^(avatar|block)_\d+$")
s3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_REGION"),
    config=Config(signature_version="s3v4"),
)


@api_images.route("/images/<key>")
def show_img(key):
    if not BUCKET_NAME or not IMAGE_KEY.match(key):
        abort(404)
    url = s3.generate_presigned_url(
        "get_object", Params={"Bucket": BUCKET_NAME, "Key": key}, ExpiresIn=3600
    )
    return redirect(url)


@api_images.route("/api/images", methods=["GET"])
def get_imgs():
    return None


@api_images.route("/api/images", methods=["POST"])
@login_required
def post_imgs():
    try:
        img = request.files["image"]
        member_id = session.get("member_id")
        type = request.form["type"]
        target_id = request.form["target_id"]
        if not allowed_file(img.filename):
            return {"error": "file type not allowed"}, 400
        if type == "avatar":
            id = member_id
        elif type == "block":
            if not Block.is_owner(member_id, target_id):
                return {"error": "block not found or not yours"}, 403
            id = int(target_id)
        else:
            return {"error": "unknown image type"}, 400
        key = type + "_" + str(id)
        # Stream straight to S3 instead of writing a user-named file to the working directory.
        s3.upload_fileobj(img.stream, BUCKET_NAME, key)
        if type == "avatar":
            result = Images.post_image(member_id, "avatar_" + str(member_id))
        else:
            result = Block.modify_block(id, "block_" + str(id))
        return {"ok": result}

    except Exception as e:
        print("type error: " + str(e))
        print(traceback.format_exc())
        return {"error": "image upload error"}, 500


@api_images.route("/api/images", methods=["PATCH"])
def change_imgs():
    return None


@api_images.route("/api/images", methods=["DELETE"])
def delete_imgs():
    return None
