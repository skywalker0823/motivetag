import traceback
from data.data import Message
from flask import request, session
from . import api_message



#GET取得該文章的留言
##以後務必增加隱私與安全
@api_message.route("/api/message", methods=["GET"])
def getting_message():
    block_id = request.args.get("block_id")
    result = Message.get_message_of_a_block(block_id)
    return {"ok": result}


#POST新增留言
#接受message統一規格{block_id,內容,時間,分數(+-5)}
##接受圖片上傳
@api_message.route("/api/message", methods=["POST"])
def posting_message():
    message = request.get_json()
    member_id = session.get("member_id")
    result = Message.post_message(member_id,message)
    result["account"] = session.get("account")
    result["member_id"] = member_id
    return result


@api_message.route("/api/message", methods=["PATCH"])
def nice_message():
    data = request.get_json()
    message_id = data["message_id"]
    member_id = session.get("member_id")
    checker = Message.nice_message_checker(member_id,message_id)
    if checker == 0:
        return {"error": "you pressed this good message before"}
    result = Message.nice_message(message_id)
    return result
