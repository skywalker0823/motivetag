from data.data import Member,Member_tags,Friend
from flask import request, session
import random
from datetime import datetime
from . import api_member


@api_member.route("/api/member",methods=["GET"])
def check_member():
    if session.get("account"):
        account = session.get("account")
        data = Member.get_member(account)
        return {"ok":True,"data":data}
    elif request.args.get("account_check"):
        account = request.args.get("account_check")
        data = Member.get_member(account)
        return {"ok":data}
    return {"error":"not loged in"}


@api_member.route("/api/member", methods=["POST"])
def sign_up_member():
    data = request.get_json()
    account = data["account"]
    password = data["password"]
    email = data["email"]
    birthday = data["birthday"]
    first_signup = data["first_signup"]
    session["FIRST_TIME"]="YES"
    result = Member.sign_up(account,password,email,birthday,first_signup)
    if result == "ok":
        return {"ok": True}
    return {"error":result}


@api_member.route("/api/member", methods=["PUT"])
def sign_in_member():
    data = request.get_json()
    account = data["account"]
    password = data["password"]
    time = data["time"]
    result = Member.sign_in(account,password,time)
    if session.get("FIRST_TIME") and session["FIRST_TIME"] == "YES" and result["msg"] == "ok":
        Member_tags.new_bie_tag(result["data"]["member_id"],"新手引導")
        session["FIRST_TIME"]="NO"
    if result["msg"]=="ok":
        result = result["data"]
        session["account"] = account
        session["member_id"] = result["member_id"]
        return {"ok": True,"data":result}
    return {"error":result}


@api_member.route("/api/member", methods=["PATCH"])
def modify_member():
    data = request.get_json()
    member_id = session.get("member_id")
    content = data["content"]
    category = data["category"]
    result = Member.patch_user_data(member_id,category,content)
    if result!=1:
        return {"error":"update user data fail"}
    return {"ok":"Update data success"}


@api_member.route("/api/member",methods=["DELETE"])
def sign_out_member():
    session["account"] = None
    session.clear()
    return {"ok":True}


@api_member.route("/api/google_sign_in",methods=["POST"])
def g_login():
    data = request.get_json()
    account = data["user_data"]["given_name"]+data["user_data"]["sub"][0:5]
    account_check = Member.get_member(account)
    if account_check==None:
        password = str(random.randint(10000,999999))
        email = data["user_data"]["email"]
        birthday = datetime.date(datetime.now())
        first_signup = datetime.date(datetime.now())
        print("辦新帳號!")
        result = Member.sign_up(account,password,email,birthday,first_signup)
        if result == "ok":
            return {"ok": "again"}
        return {"error":result}
    session["member_id"] = account_check["member_id"]
    session["account"] = account_check["account"]
    return {"ok": "let_in", "account": account_check["account"]}


@api_member.route("/api/get_user_sp",methods=["GET"])
def get_user_sp():
    target_id = request.args.get("member_id")
    member_id = session.get("member_id")
    user_basic_data = Member.getting_data_without_private(target_id)
    checker = Friend.friend_ship_checker(member_id,target_id)
    return {"ok":True,"data":user_basic_data,"is_friend":checker}
