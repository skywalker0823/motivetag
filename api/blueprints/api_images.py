import traceback
from data.data import Block
from config import Config_dev
from werkzeug.utils import secure_filename
from flask import request, session
import boto3
from data.data import Images
import os
from . import api_images

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


s3 = boto3.client("s3",
                  aws_access_key_id=Config_dev.ACCESS_KEY_ID,
                  aws_secret_access_key=Config_dev.ACCESS_SECRET_ID
                  )


BUCKET_NAME = "motivetag"


@api_images.route("/api/images", methods=["GET"])
def get_imgs():
    return None


@api_images.route("/api/images", methods=["POST"])
def post_imgs():
    try:
        img = request.files["image"]
        member_id = session.get("member_id")
        type = request.form["type"]
        target_id = request.form["target_id"]
        if type == 'avatar':
            id = member_id
        else:
            id = target_id
        key = type + "_" + str(id)
        filename = secure_filename(img.filename)
        img.save(filename)
        s3.upload_file(
            Bucket=BUCKET_NAME,
            Filename=filename,
            Key=key
        )
        if type == "avatar":
            result = Images.post_image(member_id, "avatar_" + str(member_id))
        else:
            result = Block.modify_block(target_id, "block_" + str(target_id))
        os.remove(filename)
        return {"ok": result}

    except Exception as e:
        print("type error: " + str(e))
        print(traceback.format_exc())


@api_images.route("/api/images", methods=["PATCH"])
def change_imgs():
    return None


@api_images.route("/api/images", methods=["DELETE"])
def delete_imgs():
    return None
