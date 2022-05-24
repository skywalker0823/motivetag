from data.data import Member,Member_tags
from flask import request, session
import random
from datetime import datetime
from . import api_member
# import googleapiclient.discovery


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
    session["FIRST_TIME"]="YES"
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
    if session.get("FIRST_TIME") and session["FIRST_TIME"] == "YES" and result["msg"] == "ok":
        #給予使用者教學標籤 確保辦完帳號只會被執行一次~
        Member_tags.new_bie_tag(result["data"]["member_id"],"新手引導")
        session["FIRST_TIME"]="NO"
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
    session.clear()
    return {"ok":True}



#GOOGLE OAUTH2.0
@api_member.route("/api/google_sign_in",methods=["POST"])
def g_login():
    data = request.get_json()
    account = data["user_data"]["given_name"]+data["user_data"]["sub"][0:5]
    account_check = Member.get_member(account)
    if account_check==None:
        #1.account 2.password 3.email 4.birthday(直接default) 5.first_sign
        password = str(random.randint(10000,999999))
        email = data["user_data"]["email"]
        birthday = datetime.date(datetime.now())
        first_signup = datetime.date(datetime.now())
        print("辦新帳號!")
        result = Member.sign_up(account,password,email,birthday,first_signup)
        if result == "ok":
            return {"ok": "again"}
        else:
            return {"error":result}
    else:
        print("已有帳號 紀錄session後直接登入!")
        session["member_id"] = account_check["member_id"]
        session["account"] = account_check["account"]
    #GOOGLE登入若註冊直接為使用者產生亂數密碼 並當作登入 反正不會用到這組密碼
    #首先判斷這個帳號有無註冊過 有就直接登入 畢竟是谷歌
    #先判斷此使用者登入過否?
    #別忘記session很重要 account 與 member_id
        return {"ok": "let_in", "account": account_check["account"]}

