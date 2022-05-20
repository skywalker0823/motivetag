
from data.data import Block,Block_tags
from module import tag_filter
from flask import request, session
import traceback
from . import api_blocks


@api_blocks.route("/api/blocks", methods=["GET"])
def check_blocks():
    page = request.args.get("page")
    member_id = session.get("member_id")
    result = Block.get_block(member_id,page)
    if result["msg"]=="No blocks found":
        return {"error":"No Blocks"}
    for a_block in result["datas"]:
        tags = tag_filter.filter(a_block["content"])
        a_block["tags"]=tags
    if result["msg"] == "ok":
        return {"ok":True,"data":result["datas"]}
    else:
        return {"error":True,"msg":result["msg"]}


@api_blocks.route("/api/blocks", methods=["POST"])
def build_blocks():
    block = request.get_json()
    member_id = session.get("member_id")
    tags = tag_filter.filter(block["content"])
    result = Block.create_my_block(member_id,block)
    result_block_tags = Block_tags.tag_into_block(tags,result["content"]["block_id"],member_id)
    if result["msg"] and result_block_tags["msg"] == "ok":
        result["content"]["tags"]=tags
        return {"ok":True,"data":[result["content"]]}
    else:
        return {"error":True,"msg":result["msg"],"msg2":result_block_tags["msg"]}


@api_blocks.route("/api/blocks", methods=["PATCH"])
def gooding_blocks():
    try:
        data = request.get_json()
        block_id = data["block_id"]
        result = Block.good_block(block_id)
        return result
    except Exception as e:
        print("type error: " + str(e))
        print(traceback.format_exc())
        return {"error": True, "msg": "block good error"}


@api_blocks.route("/api/blocks", methods=["PUT"])
def bading_blocks():
    try:
        data = request.get_json()
        block_id = data["block_id"]
        result = Block.bad_block(block_id)
        return result
    except Exception as e:
        print("type error: " + str(e))
        print(traceback.format_exc())
        return {"error": True, "msg": "block bad error"}


#刪除貼文DELETE
@api_blocks.route("/api/blocks", methods=["DELETE"])
def delete_blocks():
    try:
        data = request.get_json()
        block_id = data["block_id"]
        result = Block.delete_block(block_id)
        return {"ok":True,"msg":result["msg"]}
    except Exception as e:
        print("type error: " + str(e))
        print(traceback.format_exc())
        return {"error":True,"msg":"block delete error"}