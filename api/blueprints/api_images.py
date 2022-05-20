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

@api_images.route("/api/images",methods=["GET"])
def get_imgs():
    return None

@api_images.route("/api/images",methods=["POST"])
def post_imgs():
    try:
        #預設檔案名稱會是使用者的account+_head_img ex.skywalker_head_img
        img = request.files["image"]
        member_id = session.get("member_id")
        type = request.form["type"]
        target_id = request.form["target_id"]
        if type=='avatar':
            id = member_id
        else:
            id = target_id
        key = type+"_"+str(id)
        #檔案儲存方式 頭像:avatar_5000 文章照片:block_文章id(目前容許一張)
        filename = secure_filename(img.filename)#注意此行會對上傳檔案名稱做必要更改
        img.save(filename)
        s3.upload_file(
            Bucket = BUCKET_NAME,
            Filename = filename,
            Key = key
        )
        if type=="avatar":
            result = Images.post_image(member_id, "avatar_"+str(member_id))
        else:
            result = Block.modify_block(target_id,"block_"+str(target_id))
        os.remove(filename)
        return {"ok":result}
        
    except Exception as e:
        print("type error: " + str(e))
        print(traceback.format_exc())

@api_images.route("/api/images", methods=["PATCH"])
def change_imgs():
    return None


@api_images.route("/api/images", methods=["DELETE"])
def delete_imgs():
    return None
