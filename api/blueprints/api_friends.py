from flask import request, session, redirect
from flask import render_template as rt
from data.data import Friend
from . import api_friends


@api_friends.route("/<account>")
def to_member(account):
    if session.get("account") == account:
        return rt("member.html")
    return redirect("/")


@api_friends.route("/api/friend", methods=["GET"])
def checking_relationship():
    someone = request.args.get("who")
    if someone == session.get("account"):
        return {"error": "You cannot invite yourself!"}
    me = session.get("member_id")
    result = Friend.confrim_relationship(me, someone)
    if result["msg"] == "friend status fetch":
        return {"ok": result["data"]}
    elif result["msg"] == "No such user":
        return {"error": "no such user"}
    elif result["msg"] == "no data":
        return {"ok": "No records,you can send friend request"}
    elif result["msg"] == "might be friends":
        return {"ok": result["data"]}
    return {"error": "something bad at api/friend GET"}


@api_friends.route("/api/friend", methods=["POST"])
def waiting_relationship():
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
    return {"ok": result["ok"], "data_changed": result["result"],
            "data": data, "datas": result["data"]}


@api_friends.route("/api/friend", methods=["DELETE"])
def deleting_relationship():
    data = request.get_json()
    target = data["friend_ship_id"]
    result = Friend.delete_relation(target)
    return {"ok": result["ok"], "data_changed": result["result"], "data": data}
