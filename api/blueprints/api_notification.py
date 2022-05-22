#基本概念如同郵箱，將新訊息都備忘至此
#提醒內容一 好友成立，好友絕交，好友拒絕
#提醒內容二 新block
#提醒內容三 留言comment
#提醒內容三 聊天新訊息

#將由websocket+Mysql來實作
from crypt import methods
from flask import request, session
from data.data import Notification
from . import api_notification


#務必追求連線的乾淨簡潔


#取得通知 前端每十秒打一次取得
#查看read time = Null的個人方塊
#沒點擊就積蓄累積
#點擊就打一個fetch PATCH將這些訊息都加上時間戳
#老通知(已有時間戳)不會再出現
@api_notification.route("/api/notifi",methods=["GET"])
def getting_notifi():
    member_id = session.get("member_id")
    account = session.get("account")
    if member_id==None:
        return {"error":"Please reload to get notifi"}
    result = Notification.get_notifi(member_id)
    return result



#發出通知
@api_notification.route("/api/notifi", methods=["POST"])
def posting_notifi():
    data = request.get_json()
    me = data["me"]
    who = data["who"]
    type = data["type"]
    time = data["time"]
    content = data["content"]
    print("抓到時間",time)
    result = Notification.post_notifi(me,who,content,time)
    return result


#打開通知 就刪除舊的
@api_notification.route("/api/notifi", methods=["DELETE"])
def reading_notifi():
    member_id = session.get("member_id")
    result = Notification.delete_notifi(member_id)
    return result
