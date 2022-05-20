
import pymysql
import os, traceback
from dbutils.pooled_db import PooledDB
from dotenv import load_dotenv




load_dotenv()
POOL = PooledDB(
    creator=pymysql,  # Which DB module to use
    maxconnections=7,# Allowed max connection, 0 and None means no limitations.
    mincached=3,  # Least connection when created, 0 means don't.
    blocking=True,    # Queue when there is no connection avaliable. True = wait；False = No waits, and report error.
    ping=0,  # Check if Mysql service is avaliable # if：0 = None = never, 1 = default = whenever it is requested, 2 = when a cursor is created, 4 = when a query is executed, 7 = always
    host=os.getenv("AWS_motivetag_DB"),
    port=3306,
    user='root',
    password=os.getenv("DB_PASS"),
    database='motivetag',
    charset='utf8',
    cursorclass=pymysql.cursors.DictCursor
)
connection = POOL.connection()



#新註冊者幫他開一個friend_<account>的table
class Member:
    def get_member(account):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM member WHERE account=%s", (account,))
            result = cursor.fetchone()
            connection.commit()
            return result
    def sign_up(account,password,email,birthday,first_signup):
        #註冊
        try:
            with connection.cursor() as cursor:
                account_check = cursor.execute("""SELECT * FROM member WHERE account=%s""", (account,))
                email_check = cursor.execute("""SELECT * FROM member WHERE email=%s""", (email,))
                connection.commit()
                if account_check != 0:
                    return "Already registed"
                elif email_check != 0:
                    return "Same email used"
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO 
                    member(
                        account,
                        password,
                        email,
                        birthday,
                        first_signup
                    )VALUES(%s,%s,%s,%s,%s)""",
                    (account,password,email,birthday,first_signup,))
                connection.commit()
                return "ok"
        except Exception as e:
            print("type error: " + str(e))
            print(traceback.format_exc())
            return "sign up database error"
        #登入
    def sign_in(account,password):
        # try:
        with connection.cursor() as cursor:
            got=cursor.execute("SELECT * FROM member WHERE account=%s", (account,))
            result = cursor.fetchone()
            connection.commit()
            if got==0:
                return {"msg":"account not find"}
            else:
                if password == result["password"]:
                    return {"msg":"ok","data":result}
                else:
                    return {"msg":"wrong password"}

    def delete(account):
        #刪除
        return None


class Block:
  #預設內容 自己all+朋友all+tag內容
    def get_block(member_id,page,member_tags=None):
        page=int(page)
        with connection.cursor() as cursor:
            #此Query已經可以完整抓出自己與好友的貼文 時間排序 limit10 
            #大哥拜託齁 找時間把這個query拆開來看一下
            #最後的query專注在取出此使用者關注tag的所有文章
            #分拆Query 依照每次要求來組合Query UNION為分界點
            sql_me=None
            sql_key=None
            sql_friend=None
            sql_all = """SELECT account,block_id, block.member_id, content_type, content, build_time,good,bad,block_img
                                 FROM block RIGHT JOIN member ON member.member_id=block.member_id
                                 WHERE block.member_id IN(
                                     SELECT request_from AS ids FROM friendship WHERE status="0" 
                                     AND(request_from=%s OR request_to=%s) 
                                                               UNION
                                                               SELECT request_to AS ids FROM friendship WHERE status="0" AND(request_from=%s OR request_to=%s)) AND content_type <> "SECRET"
                                                               UNION
                                                               SELECT (SELECT account FROM member WHERE member_id=block.member_id)AS account,block_id,block.member_id,content_type,content,build_time,good,bad,block_img FROM block WHERE block_id IN(SELECT block_id FROM block_tag WHERE tag_id IN(SELECT tag_id FROM member_tags WHERE member_id=%s))
                                 ORDER BY build_time DESC
                                 LIMIT %s,%s"""
            got = cursor.execute(sql_all, (member_id, member_id,  member_id, member_id,member_id,page,5))
            result = cursor.fetchall()
            connection.commit()
            if got == 0:
                return {"msg":"No blocks found"}
            else:
                return {"msg":"ok","datas":result}
    #發文
    def create_my_block(member_id,block):
        try:
            # block = {title: title, content: content, time: time}
            type=block["type"]
            content=block["content"]
            time=block["time"]
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO
                    block(
                        member_id,
                        content_type,
                        content,
                        build_time
                    )VALUES(%s,%s,%s,%s)
                    """,(member_id,type,content,time)
                )
                connection.commit()
                cursor.execute("""SELECT account, block_id, block.member_id, content_type, content, build_time,good,bad,block_img
                               FROM block RIGHT JOIN member ON member.member_id=block.member_id
                               WHERE build_time=%s AND block.member_id=%s""", (time, member_id))
                result = cursor.fetchone()
                connection.commit()
            # 取得最新block並回傳
            return {"msg":"ok","content":result}
        except Exception as e:
            print("type error: " + str(e))
            print(traceback.format_exc())
            return {"msg":"block create database error"}
    def good_block(block_id):
        with connection.cursor() as cursor:
            result=cursor.execute("UPDATE block SET good=good+1 WHERE block_id=%s",(block_id))
            connection.commit()
            return {"ok":result}

    def bad_block(block_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "UPDATE block SET bad=bad+1 WHERE block_id=%s", (block_id))
            connection.commit()
            return {"ok": result}
    def modify_block(key,value):
        with connection.cursor() as cursor:
            result = cursor.execute("UPDATE block SET block_img=%s WHERE block_id=%s",(value,key))
            connection.commit()
            return {"ok":result}
    #刪文
    def delete_block(block_id):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM block WHERE block_id=%s",(block_id))
            connection.commit()
        return {"msg":block_id+" delete complete"}



class Block_tags:
    def get_all_tag_of_a_block():
        #GET all tag of a block
        return None
    

    def tag_into_block(tags,block_id,member_id):

        try:
            #POST tags into a block
            #先識別tag有無存在tag 才能取得tag_id 有加一 無新增
            #block_id會傳進來不用擔心
            # INSERT INTO tag(name, popularity, create_by)VALUES( %s, % s, % s) ON DUPLICATE KEY UPDATE popularity = popularity+1
            #直接新增+有加一 無新增 順帶將字轉查成tag_id
            sql1 = "INSERT INTO tag(name,popularity,create_by)VALUES(%s,%s,%s)ON DUPLICATE KEY UPDATE popularity = popularity+1"
            sql2 = "INSERT INTO block_tag(block_id,tag_id)VALUES(%s,(SELECT tag_id FROM tag WHERE name=%s))"
            with connection.cursor() as cursor:
                for tag in tags:
                    cursor.execute(sql1, (tag,1,member_id))
                    cursor.execute(sql2, (block_id,tag))
                    connection.commit()
            return {"msg":"ok"}
        except Exception as e:
            print("type error: " + str(e))
            print(traceback.format_exc())
            return {"msg": "tag into block database error"}

class Member_tags:
    #此項目可刪除!
    def getting_member_tags(member_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * from member_tags RIGHT JOIN tag ON member_tags.tag_id=tag.tag_id WHERE member_id=%s",(member_id,))
            result = cursor.fetchall()
            connection.commit()
            return {"msg":"ok","all_tags":result}

    def find_member_tags(member_id,tag):
        with connection.cursor() as cursor:
            count = cursor.execute("SELECT * FROM member_tags WHERE member_id=%s AND tag_id=(SELECT tag_id FROM tag WHERE name=%s)",(member_id,tag))
            return count
    def add_member_tag(member_id,tag):
        #使用者新增tag
            with connection.cursor() as cursor:

                cursor.execute("INSERT INTO member_tags(member_id,tag_id)VALUES(%s,(SELECT tag_id FROM tag WHERE name=%s))",(member_id,tag))
                result = cursor.execute("SELECT member_tag_id from member_tags WHERE member_id=%s AND tag_id=(SELECT tag_id from tag WHERE name=%s)",(member_id,tag))
                data = cursor.fetchone()
                connection.commit()
            return {"result":result,"data":data}

    def del_member_tag(member_id, member_tag_id):
        with connection.cursor() as cursor:
            result = cursor.execute("DELETE FROM member_tags WHERE member_tag_id=%s",(member_tag_id))
            connection.commit()
            return {"ok":True,"count":result}





class Tag:
    def getting_tags_global():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tag_id,name,popularity,create_date,create_by FROM tag ORDER BY popularity DESC LIMIT 10")
            result = cursor.fetchall()
            connection.commit()
            return result
    # def find_id_of(tag):
    #     with connection.cursor() as cursor:
    #         tag_count=cursor.execute("SELECT tag_id FROM tag WHERE name=%s",(tag,))
    #         connection.commit()
    #         if tag_count == 0:
    #             #首生tag 產生後取id
    #             with connection.cursor() as cursor:
    #                 cursor.execute("INSERT INTO tag (name) VALUES (%s)",(tag,))
    #                 cursor.execute("SELECT tag_id FROM tag WHERE name=%s",(tag,))
    #                 result = cursor.fetchone()
    #                 connection.commit()
    #                 return result
    #         else:
    #             #已出現tag +1後取id
    #             with connection.cursor() as cursor:
    #                 cursor.execute(
    #                     "UPDATE tag SET popularity=popularity+1 WHERE name=%s", (tag,))
    #                 cursor.execute(
    #                     "SELECT tag_id FROM tag WHERE name=%s", (tag,))
    #                 result = cursor.fetchone()
    #                 connection.commit()
    #                 return result

    def adjust_global_tag(tag,member_id):
        #自適應傳入tag若有重複將會增加pop 若無將會創新
        try:
            with connection.cursor() as cursor:
                result = cursor.execute("INSERT INTO tag(name,popularity,create_by)VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE popularity=popularity+1", (tag, 1, member_id))
                connection.commit()
                return result
        except Exception as e:
            print("type error: " + str(e))
            print(traceback.format_exc())
            return {"msg": "global tag adjust database error"}


class Friend:
    #已是朋友/已邀過就無法邀(但會送出通知)，邀請是[獨一無二]，整個friendship代表朋友網絡
    #若同時雙方皆有邀請，自動成為好友
    #A->B A<-B A<->B 三種狀態皆能認同是好友(只要有人送 另一人同意)
    #狀態0等於已經同意 1代表pending
    #1.檢查是否已是好友(A->B=0 or A<-B=0 滿足一者就是好友) 2.檢查對方是否有邀約 3.發邀請and檢查是否已發過
    #Status, 0=Is friend ,1 is pending
    def confrim_relationship(me,someone_else):
        if someone_else==None or someone_else=="" or someone_else==False or someone_else=="undefined":
            #GET ALL FRIEND
            with connection.cursor() as cursor:
                result = cursor.execute(
                    "SELECT friend_ship_id,(SELECT account FROM member WHERE request_from=member_id)AS req_from,(SELECT account FROM member WHERE request_to=member_id)AS req_to,status FROM friendship WHERE (request_from=%s OR request_to=%s)AND(status=%s OR status=%s)", (me, me, "0", "1"))
                data = cursor.fetchall()
                connection.commit()
            return {"data":data,"count":result,"msg":"friend status fetch"}
        else:
            #單一對象查詢 這裡採多段式判斷 足夠資料都可中途離開
            #時查詢是否有發過邀請+是否有重複送出?
            #關卡1查是否有此人？
            with connection.cursor() as cursor:
                result = cursor.execute("SELECT * FROM member WHERE account=%s",(someone_else))
                data = cursor.fetchall()
                connection.commit()
                if result==0:
                    return {"data":None,"count":0,"msg":"No such user"}
            with connection.cursor() as cursor:
                result = cursor.execute(
                    "SELECT * FROM friendship WHERE ((request_from=%s AND request_to=(SELECT member_id FROM member WHERE account=%s)) OR (request_from=(SELECT member_id FROM member WHERE account=%s) AND request_to=%s)) AND (status=%s OR status=%s)", (me, someone_else, someone_else, me, "0", "1"))
                data = cursor.fetchall()
                connection.commit()
                if result!=0:
                    return {"count": result, "data": data,"msg":"might be friends"}
                else:  
                    return {"msg":"no data","count":result}

    def send_friend_request(me, someone_else):
        try:
            #還要查詢是否已是好友
            with connection.cursor() as cursor:
                result = cursor.execute(
                    "SELECT * FROM friendship WHERE((request_from=%s and request_to=(SELECT member_id FROM member WHERE account=%s)) OR(request_from=(SELECT member_id FROM member WHERE account=%s) and request_to=%s))AND status=%s", (me, someone_else, someone_else, me, "0"))
                connection.commit()
                if result!=0:
                    return {"error":"Already friend"}
            #新增 若對方有寄送 則自動成為好友
            with connection.cursor() as cursor:
                result = cursor.execute("SELECT * FROM friendship WHERE request_from=(SELECT member_id FROM member WHERE account=%s) AND request_to=%s",(someone_else,me))
                data = cursor.fetchall()
                connection.commit()
                if result!=0:
                    return {"ok":"FAST","data":data}
            with connection.cursor() as cursor:
                result = cursor.execute("SELECT * FROM friendship WHERE request_from=%s AND request_to=(SELECT member_id FROM member WHERE account=%s)",(me,someone_else))
                connection.commit()
                if result!=0:
                    return {"error":"same invite found"}
            with connection.cursor() as cursor:
                cursor.execute("""INSERT INTO friendship(request_from,request_to,status)VALUES(%s,(SELECT member_id FROM member WHERE account=%s),%s)""",(me,someone_else,"1"))
                connection.commit()
                return {"ok": "friend request sent!","msg":"ok"}
        except Exception as e:
            print("type error: " + str(e))
            print(traceback.format_exc())
            return {"error": "friend requet error","msg":"already invite"}
    
    def forge_friend_request(target):
        with connection.cursor() as cursor:
            result = cursor.execute("UPDATE friendship SET status=%s WHERE friend_ship_id=%s",("0",target))
            connection.commit()
            return {"ok":"friendship updated","result":result}
    def delete_relation(target):
        with connection.cursor() as cursor:
            result = cursor.execute("DELETE FROM friendship WHERE friend_ship_id=%s",(target))
            connection.commit()
            if result!=1:
                return {"error":"Delete friend fail"}
            return {"ok":"Delete Frind success","result":result}




class Message:
    def get_message_of_a_block(block_id):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT (SELECT account FROM member WHERE block_comment.member_id=member.member_id)AS account,comment_id,member_id,content,build_time,nice_comment FROM block_comment WHERE block_id=%s
            """,(block_id))
            data = cursor.fetchall()
            connection.commit()
            return data
        #請回傳 account,message,time
    def post_message(member_id,message):
        with connection.cursor() as cursor:
            result = cursor.execute("""
                INSERT INTO block_comment(
                    member_id,
                    block_id,
                    content,
                    build_time
                )VALUES(%s,%s,%s,%s);
            """,(member_id,message["block_id"],message["message"],message["time"]))
            cursor.execute("SELECT LAST_INSERT_ID()")
            id = cursor.fetchone()
            connection.commit()
            if result==1:
                return {"ok":id}
            return {"error":"message POST Error"}

    def nice_block(comment_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "UPDATE block_comment SET nice_comment=nice_comment+1 WHERE comment_id=%s", (comment_id))
            connection.commit()
            return {"ok": result}





class Images:
    #未來會套用可在block上傳圖片
    def get_image():
        return None

    def post_image(member_id,filename):
        try:
            with connection.cursor() as cursor:
                result = cursor.execute("UPDATE member SET member_img=%s WHERE member_id=%s",(filename,member_id))
            connection.commit()
            return "ok"
        except Exception as e:
            print(e)
            return "upload error"

class Notification:
    def get_notifi(member_id):
        try:
            with connection.cursor() as cursor:
                result = cursor.execute("SELECT * FROM notifi WHERE reciever_id=%s",(member_id))
            data = cursor.fetchall()
            connection.commit()
            return {"ok": "Notification GET","data":data,"count":result}
        except Exception as e:
            print(e)
            return {"error": "GET notifi error"}


    def post_notifi(me,who,content):
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                INSERT INTO notifi(
                    sender_id,
                    reciever_id,
                    content
                )VALUES(%s,(SELECT member_id FROM member WHERE account=%s),%s)""", (me, who, content)
                )
            connection.commit()
            return {"ok":"Notification send"}
        except Exception as e:
            print(e)
            return {"error":"post notifi error"}


    def patch_notifi(member_id):
        return None
