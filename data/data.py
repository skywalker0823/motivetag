
import pymysql
import os, traceback
from dbutils.pooled_db import PooledDB
from dotenv import load_dotenv

load_dotenv()

hosts = [
    os.getenv("AWS_motivetag_DB"),
    os.getenv("DB_BK1"),
    os.getenv("DB_BK2")
]

def get_connection():
    for host in hosts:
        print(f"try to connect to host:{host}")
        try:
            POOL = PooledDB(
                    creator=pymysql,
                    maxconnections=7,
                    mincached=3,
                    blocking=True,
                    ping=0,
                    host=host,
                    port=3306,
                    user='root',
                    password=os.getenv("DB_PASSWORD"),
                    database='motivetag',
                    charset='utf8',
                    cursorclass=pymysql.cursors.DictCursor
                )
            connection = POOL.connection()
            print(f"Connect to host:{host} success")
            return connection
        except pymysql.Error as e:
            print(f"Connect to host:{host} failed: {e}")
    raise Exception("All DB's host are down")

connection = get_connection()

class Member:
    def get_member(account):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM member WHERE account=%s", (account,))
            result = cursor.fetchone()
            connection.commit()
            return result

    def sign_up(account,password,email,birthday,first_signup):
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

    def sign_in(account,password,time):
        with connection.cursor() as cursor:
            cursor.execute("UPDATE member SET last_signin=%s WHERE account=%s",(time,account))
            got=cursor.execute("SELECT * FROM member WHERE account=%s", (account,))
            result = cursor.fetchone()
            connection.commit()
            if got==0:
                return {"msg":"account not find"}
            if password == result["password"]:
                return {"msg":"ok","data":result}
            return {"msg":"wrong password"}

    def patch_user_data(member_id,category,content):
        if category=="mood":
            with connection.cursor() as cursor:
                result = cursor.execute("UPDATE member SET mood=%s WHERE member_id=%s",(content,member_id))
                connection.commit()
            return result

    def delete(account):
        return None

    def getting_data_without_private(member_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT account,birthday,first_signup,last_signin,mood,exp FROM member WHERE member_id=%s",(member_id))
            data = cursor.fetchone()
            return data


class Block:
    def get_block(member_id,page,obseve_key=None,order_by=None):
        page=int(page)
        # sql_me=None
        # sql_by_score = None
        sql_observe_key = """SELECT account,block_id, block.member_id, content_type, content, build_time,good,bad,block_img
                                FROM block RIGHT JOIN member ON member.member_id=block.member_id
                                WHERE block_id IN(SELECT block_id FROM block_tag WHERE tag_id=(SELECT tag_id FROM tag WHERE name=%s))ORDER BY build_time DESC LIMIT %s,%s"""
        sql_all = """SELECT account,block_id, block.member_id, content_type, content, build_time,good,bad,block_img
                                FROM block RIGHT JOIN member ON member.member_id=block.member_id
                                WHERE block.member_id IN
                                (
                                    SELECT request_from AS ids FROM friendship WHERE status="0" 
                                    AND(request_from=%s OR request_to=%s) 
                                    UNION
                                    SELECT request_to AS ids FROM friendship WHERE status="0" AND(request_from=%s OR request_to=%s)) AND content_type <> "SECRET" AND content_type <> "Anonymous"
                                    UNION
                                    SELECT (SELECT account FROM member WHERE member_id=block.member_id)AS account,block_id, block.member_id, content_type, content, build_time,good,bad,block_img FROM block WHERE member_id=%s
                                    UNION
                                    SELECT (SELECT account FROM member WHERE member_id=block.member_id)AS account,block_id,block.member_id,content_type,content,build_time,good,bad,block_img FROM block WHERE block_id IN(SELECT block_id FROM block_tag WHERE tag_id IN(SELECT tag_id FROM member_tags WHERE member_id=%s)
                                )
                                ORDER BY build_time DESC
                                LIMIT %s,%s"""
        sql_all_altered = """"""
        with connection.cursor() as cursor:
            if obseve_key==None:
                got = cursor.execute(sql_all, (member_id, member_id, member_id, member_id, member_id,member_id,page,5))
                # got = cursor.execute(sql_all_altered, (member_id, member_id, member_id, member_id, member_id,member_id,page,5))
            else:
                got = cursor.execute(sql_observe_key,(obseve_key,page,5))
            result = cursor.fetchall()
            connection.commit()
            if got == 0:
                return {"msg":"No blocks found"}
            return {"msg":"ok","datas":result}

    def create_my_block(member_id,block):
        try:
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

    def good_block_checker(member_id,block_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "INSERT INTO goods(member_id,block_id) SELECT * FROM (SELECT %s,%s) AS tmp WHERE NOT exists (SELECT member_id,block_id FROM goods WHERE member_id=%s AND block_id=%s) LIMIT 1;", (member_id, block_id, member_id, block_id))
            connection.commit()
            return result

    def bad_block(block_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "UPDATE block SET bad=bad+1 WHERE block_id=%s", (block_id))
            connection.commit()
            return {"ok": result}

    def bad_block_checker(member_id,block_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "INSERT INTO bads(member_id,block_id) SELECT * FROM (SELECT %s,%s) AS tmp WHERE NOT exists (SELECT member_id,block_id FROM bads WHERE member_id=%s AND block_id=%s) LIMIT 1;", (member_id, block_id, member_id, block_id))
            connection.commit()
            return result

    def modify_block(key,value):
        with connection.cursor() as cursor:
            result = cursor.execute("UPDATE block SET block_img=%s WHERE block_id=%s",(value,key))
            connection.commit()
            return {"ok":result}

    def delete_block(block_id):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM block WHERE block_id=%s",(block_id))
            connection.commit()
        return {"msg":block_id+" delete complete"}


class Block_tags:
    def get_all_tag_of_a_block():
        return None
    
    def tag_into_block(tags,block_id,member_id):
        try:
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

    def new_bie_tag(member_id, tag):
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO member_tags(member_id,tag_id)VALUES(%s,(SELECT tag_id FROM tag WHERE name=%s))",(member_id,tag))
            connection.commit()
            return None


class Tag:
    def getting_tags_global():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT tag_id,name,popularity,create_date,create_by FROM tag ORDER BY popularity DESC LIMIT 10")
            result = cursor.fetchall()
            connection.commit()
            return result

    def upping_global_tag(tag,member_id):
        try:
            with connection.cursor() as cursor:
                result = cursor.execute("INSERT INTO tag(name,popularity,create_by)VALUES(%s,%s,%s) ON DUPLICATE KEY UPDATE popularity=popularity+1", (tag, 1, member_id))
                connection.commit()
                return result
        except Exception as e:
            print("type error: " + str(e))
            print(traceback.format_exc())
            return {"msg": "global tag adjust database error"}

    def downing_global_tag(tag):
        with connection.cursor() as cursor:
            result = cursor.execute("UPDATE tag SET popularity=popularity-1 WHERE name=%s",(tag))
            connection.commit()
            return result


class Friend:
    def confrim_relationship(me,someone_else):
        if someone_else==None or someone_else=="" or someone_else==False or someone_else=="undefined":
            with connection.cursor() as cursor:
                result = cursor.execute(
                    "SELECT friend_ship_id,request_from AS req_from_id,request_to AS req_to_id,(SELECT account FROM member WHERE request_from=member_id)AS req_from,(SELECT account FROM member WHERE request_to=member_id)AS req_to,status FROM friendship WHERE (request_from=%s OR request_to=%s)AND(status=%s OR status=%s)", (me, me, "0", "1"))
                data = cursor.fetchall()
                connection.commit()
            return {"data":data,"count":result,"msg":"friend status fetch"}
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
            return {"msg":"no data","count":result}

    def send_friend_request(me, someone_else):
        try:
            with connection.cursor() as cursor:
                result = cursor.execute(
                    "SELECT * FROM friendship WHERE((request_from=%s and request_to=(SELECT member_id FROM member WHERE account=%s)) OR(request_from=(SELECT member_id FROM member WHERE account=%s) and request_to=%s))AND status=%s", (me, someone_else, someone_else, me, "0"))
                connection.commit()
                if result!=0:
                    return {"error":"Already friend"}
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
            cursor.execute("SELECT * FROM friendship WHERE friend_ship_id=%s",(target))
            data = cursor.fetchone()
            connection.commit()
            return {"ok":"friendship updated","result":result,"data":data}
            
    def delete_relation(target):
        with connection.cursor() as cursor:
            result = cursor.execute("DELETE FROM friendship WHERE friend_ship_id=%s",(target))
            connection.commit()
            if result!=1:
                return {"error":"Delete friend fail"}
            return {"ok":"Delete Frind success","result":result}

    def friend_ship_checker(member_id,target_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM friendship WHERE (request_from=%s AND request_to=%s)OR(request_from=%s AND request_to=%s)",(member_id,target_id,target_id,member_id))
            result = cursor.fetchone()
        return result


class Message:
    def get_message_of_a_block(block_id):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT (SELECT account FROM member WHERE block_comment.member_id=member.member_id)AS account,comment_id,member_id,content,build_time,nice_comment,given_score FROM block_comment WHERE block_id=%s
            """,(block_id))
            data = cursor.fetchall()
            connection.commit()
            return data

    def post_message(member_id,message):
        with connection.cursor() as cursor:
            result = cursor.execute("""
                INSERT INTO block_comment(
                    member_id,
                    block_id,
                    content,
                    build_time,
                    given_score
                )VALUES(%s,%s,%s,%s,%s);
            """,(member_id,message["block_id"],message["message"],message["time"],message["score"]))
            cursor.execute("SELECT LAST_INSERT_ID()")
            id = cursor.fetchone()
            connection.commit()
            if result==1:
                return {"ok":id}
            return {"error":"message POST Error"}

    def nice_message(comment_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "UPDATE block_comment SET nice_comment=nice_comment+1 WHERE comment_id=%s", (comment_id))
            connection.commit()
            return {"ok": result}

    def nice_message_checker(member_id,message_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "INSERT INTO c_goods(member_id,comment_id) SELECT * FROM (SELECT %s,%s) AS tmp WHERE NOT exists (SELECT member_id,comment_id FROM c_goods WHERE member_id=%s AND comment_id=%s) LIMIT 1;", (member_id, message_id, member_id, message_id))
            connection.commit()
            return result


class Images:
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


    def post_notifi(me,who,content,time):
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                INSERT INTO notifi(
                    sender_id,
                    reciever_id,
                    content,
                    send_time
                )VALUES(%s,(SELECT member_id FROM member WHERE account=%s),%s,%s)""", (me, who, content,time)
                )
            connection.commit()
            return {"ok":"Notification send"}
        except Exception as e:
            print(e)
            return {"error":"post notifi error"}

    def patch_notifi(member_id):
        return None

    def delete_notifi(member_id):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM notifi WHERE reciever_id=%s",(member_id))
            connection.commit()
            return {"ok":"notifi read"}


class Vote_table:
    def get_vote(block_id):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM vote_options WHERE block_id=%s", (block_id))
            data = cursor.fetchall()
            connection.commit()
        return data

    def create_vote(block_id,votes):
        try:
            with connection.cursor() as cursor:
                for vote in votes:
                    cursor.execute("""
                    INSERT INTO vote_options(
                        block_id,
                        option_name
                    )VALUES(%s,%s)""", (block_id,vote)
                    )
                cursor.execute("SELECT * FROM vote_options WHERE block_id=%s",(block_id))
                data = cursor.fetchall()
                connection.commit()
            return {"msg":data}
        except Exception as e:
            print(e)
            return {"msg":"vote create error"}

class Vote:
    def check_vote(member_id,block_id):
        with connection.cursor() as cursor:
            result = cursor.execute(
                "SELECT * FROM votes where member_id=%s and vote_option_id IN (SELECT vote_option_id FROM vote_options WHERE block_id=%s)", (member_id,block_id))
            data = cursor.fetchone()
            connection.commit()
        return {"count":result,"data":data}

    def do_vote(member_id,vote_option_id):
        with connection.cursor() as cursor:
            cursor.execute("""INSERT INTO votes(
                member_id,
                vote_option_id
            )VALUES(%s,%s)""",(member_id,vote_option_id))
            connection.commit()
        return  {"ok":True}

    def get_vote(block_id):
        with connection.cursor() as cursor:
            cursor.execute("""
            SELECT * FROM votes WHERE vote_option_id IN (SELECT vote_option_id FROM vote_options WHERE block_id=%s)
            """,(block_id))
            data = cursor.fetchall()
            connection.commit()
        return data

    def change_vote():
        return

    def del_vote():
        return

class Tag_info:
    def get_tag_info(tag_name):
        with connection.cursor() as cursor:
            cursor.execute("""
            SELECT brick_id,(SELECT account FROM member WHERE member.member_id=bricks.member_id)AS account,tag_id,title,classifi,popularity,feedbacks,time FROM bricks WHERE tag_id=(SELECT tag_id FROM tag WHERE name=%s) ORDER BY time DESC
            """,(tag_name))
            data = cursor.fetchall()
            connection.commit()
        return data

    def post_tag_info(data):
        with connection.cursor() as cursor:
            result = cursor.execute("""INSERT INTO bricks(
                member_id,
                tag_id,
                title,
                content,
                classifi,
                time
            )VALUES(%s,(SELECT tag_id FROM tag WHERE name=%s),%s,%s,%s,%s)
            """,(data["member_id"],data["tag_name"],data["title"],data["content"],data["classifi"],data["time"]))
            connection.commit()
        return result

    def modify_tag_info(brick_id):
                with connection.cursor() as cursor:
                    result = cursor.execute("UPDATE bricks SET popularity=popularity+1 WHERE brick_id=%s",(brick_id))
                    connection.commit()
                    return result


class Level:
    def get_current_exp(member_id):
        return

    def exp_up(member_id,exp):
        with connection.cursor() as cursor:
            result = cursor.execute("UPDATE member SET exp=exp+%s WHERE member_id=%s",(exp,member_id))
            connection.commit()
        return result

    def exp_down(member_id,exp):
        return


class Bricks:
    def getting_brick(brick_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT brick_id,(SELECT account FROM member WHERE bricks.member_id=member.member_id)AS account,tag_id,title,content,classifi,feedbacks,popularity,time FROM bricks WHERE brick_id=%s",(brick_id))
            result = cursor.fetchall()
            connection.commit()
        return result

    def getting_brick_discuss(brick_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT (SELECT account FROM member WHERE member.member_id=brick_discuss.member_id)AS account,content,time FROM brick_discuss WHERE brick_id=%s ORDER BY time DESC",(brick_id))
            datas = cursor.fetchall()
            connection.commit()
            return datas

    def posting_brick_discuss(datas):
        with connection.cursor() as cursor:
            result = cursor.execute("INSERT INTO brick_discuss(member_id,brick_id,content,time)VALUES(%s,%s,%s,%s)",(datas["member_id"],datas["brick_id"],datas["content"],datas["time"]))
            connection.commit()
            return result

    def patching_brick_discuss(brick_id):
        with connection.cursor() as cursor:
            result = cursor.execute("UPDATE bricks SET feedbacks=feedbacks+1 WHERE brick_id=%s",(brick_id))
            connection.commit()
            return result
