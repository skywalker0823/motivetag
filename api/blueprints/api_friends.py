from flask import request, session, redirect
from flask import render_template as rt
from data.data import Friend
from . import api_friends



@api_friends.route("/<account>")
def to_member(account):
    if session.get("account") == account:
        return rt("member.html")
    else:

            # #以下是想拜訪好友
            # someone_else = account
            # me = session.get("member_id")
            # check = Friend.confrim_relationship(me,someone_else)
            # print(check)
            # if check["msg"]:
            #     if check["msg"]=="no data":
            #         return redirect("/")
            # elif check["redirect_to"][0]["status"]=="0":
            #     return rt("member.html")
            # else:
        return redirect("/")





#REST "4" friends :)
#有帶入變數->發好友邀請前確認關係 無變數->取全部朋友
@api_friends.route("/api/friend", methods=["GET"])
def checking_relationship():
    someone = request.args.get("who")
    if someone == session.get("account"):
        return {"error":"You cannot invite yourself!"}
    me = session.get("member_id")
    result = Friend.confrim_relationship(me,someone)
    if result["msg"]=="friend status fetch":
        return {"ok":result["data"]}
    elif result["msg"]=="No such user":
        return {"error":"no such user"}
    elif result["msg"]=="no data":
        return {"ok":"No records,you can send friend request"}
    elif result["msg"] == "might be friends":
        return {"ok":result["data"]}
    return {"error":"something bad at api/friend GET"}


@api_friends.route("/api/friend", methods=["POST"])
def waiting_relationship():
    #來這裡的資料只需要確認有無重複發送給對方，有則打通知，無新增
    data = request.get_json()
    someone_else = data["who"]
    me = session.get("member_id")
    result = Friend.send_friend_request(me, someone_else)
    result["me"] = me
    result["someone_else"] = someone_else
    return result


@api_friends.route("/api/friend", methods=["PATCH"])
def forgeing_relationship():
    data = request.get_json()
    target = data["friend_ship_id"]
    result = Friend.forge_friend_request(target)
    return {"ok":result["ok"],"data_changed":result["result"],"data":data}




@api_friends.route("/api/friend", methods=["DELETE"])
def deleting_relationship():
    data = request.get_json()
    target = data["friend_ship_id"]
    result = Friend.delete_relation(target)
    return {"ok": result["ok"], "data_changed": result["result"], "data": data}
