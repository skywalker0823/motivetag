from data.data import Block,Block_tags,Vote_table
from module import tag_filter
from flask import request, session
import traceback
from . import api_blocks


@api_blocks.route("/api/blocks", methods=["GET"])
def check_blocks():
    page = request.args.get("page")
    key = request.args.get("key")
    member_id = session.get("member_id")
    result = Block.get_block(member_id,page,key)
    if result["msg"]=="No blocks found":
        return {"error":"No Blocks"}
    for a_block in result["datas"]:
        tags = tag_filter.filter(a_block["content"])
        a_block["votes"]=Vote_table.get_vote(a_block["block_id"])
        a_block["tags"]=tags
        if a_block["content_type"]=="Anonymous":
            a_block["tags"].append("Anonymous")
    if result["msg"] == "ok":
        return {"ok":True,"data":result["datas"]}
    return {"error":True,"msg":result["msg"]}


@api_blocks.route("/api/blocks", methods=["POST"])
def build_blocks():
    block = request.get_json()
    member_id = session.get("member_id")
    tags = tag_filter.filter(block["content"])
    if block["tags"] != None and block["type"]=="Anonymous":
        tags.append(block["tags"])
    result = Block.create_my_block(member_id,block)
    result_block_tags = Block_tags.tag_into_block(tags,result["content"]["block_id"],member_id)
    if result["msg"] and result_block_tags["msg"] == "ok":
        result["content"]["tags"]=tags
        result["content"]["votes"]=[]
    if block["vote_box"] != [] and block["vote_box"]!=None:
        vote_table_create = Vote_table.create_vote(result["content"]["block_id"],block["vote_box"])
        result["content"]["votes"]=vote_table_create["msg"]
    return {"ok":True,"data":[result["content"]]}


@api_blocks.route("/api/blocks", methods=["PATCH"])
def gooding_blocks():
    try:
        data = request.get_json()
        block_id = data["block_id"]
        member_id = session.get("member_id")
        checker = Block.good_block_checker(member_id,block_id)
        if checker==0:
            return {"error":"you pressed this good  before"}
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
        member_id = session.get("member_id")
        checker = Block.bad_block_checker(member_id, block_id)
        if checker == 0:
            return {"error": "you pressed this boo before"}
        result = Block.bad_block(block_id)
        return result
    except Exception as e:
        print("type error: " + str(e))
        print(traceback.format_exc())
        return {"error": True, "msg": "block bad error"}


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