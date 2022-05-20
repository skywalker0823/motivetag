from data.data import Member
from flask import request, session
import traceback
from . import api_member



#狀態取得session 與使用者全資料
@api_member.route("/api/member",methods=["GET"])
def check_member():
    if session.get("account"):
        account = session.get("account")
        data = Member.get_member(account)
        return {"ok":True,"data":data}
    elif request.args.get("account_check"):

        account = request.args.get("account_check")
        print("檢查",account)
        data = Member.get_member(account)
        print("ok",data)
        return {"ok":data}
    else:
        print("no")
        return {"error":"not loged in"}

#註冊
@api_member.route("/api/member", methods=["POST"])
def sign_up_member():
    data = request.get_json()
    account = data["account"]
    password = data["password"]
    email = data["email"]
    birthday = data["birthday"]
    first_signup = data["first_signup"]
    result = Member.sign_up(account,password,email,birthday,first_signup)
    if result == "ok":
        return {"ok": True}
    else:
        return {"error":result}

#登入
@api_member.route("/api/member", methods=["PUT"])
def sign_in_member():
    data = request.get_json()
    account = data["account"]
    password = data["password"]
    result = Member.sign_in(account,password)
    if result["msg"]=="ok":
        result = result["data"]
        session["account"] = account
        session["member_id"] = result["member_id"]
        return {"ok": True,"data":result}
    else:
        return {"error":result}

#修改
@api_member.route("/api/member", methods=["PATCH"])
def modify_member():
    return None

#登出
@api_member.route("/api/member",methods=["DELETE"])
def sign_out_member():
    session["account"] = None
    return {"ok":True}


