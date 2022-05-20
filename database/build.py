import pymysql
import os
from dotenv import load_dotenv

#創建database
def build_database(conn):
    cursor.execute("DROP DATABASE IF EXISTS motivetag")
    cursor.execute("CREATE DATABASE motivetag")
    cursor.execute("USE motivetag")
    conn.commit()

#創建 會員 Table id1000起跳
def build_member(conn):
    cursor.execute("DROP TABLE IF EXISTS member")
    sql = """CREATE TABLE member(
        member_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        account varchar(50) UNIQUE KEY NOT NULL,
        password varchar(50) NOT NULL,
        email varchar(100) NOT NULL,
        birthday DATE NOT NULL,
        first_signup DATE NOT NULL,
        last_signin DATETIME,
        member_img varchar(100)
    )"""
    cursor.execute(sql)
    conn.commit()

#創建 tag FK: create_by(member_id)OK
def build_global_tag(conn):
    cursor.execute("DROP TABLE IF EXISTS tag")
    sql = """CREATE TABLE tag(
        tag_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        name varchar(100) UNIQUE KEY,
        popularity INT,
        create_date DATE,
        create_by INT NOT NULL
    )"""
    cursor.execute(sql)
    conn.commit()


#會員訂閱tag FK:member_id tag_id OK
def build_member_tags(conn):
    cursor.execute("DROP TABLE IF EXISTS member_tags")
    sql = """CREATE TABLE member_tags(
        member_tag_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        member_id INT NOT NULL,
        tag_id INT NOT NULL
    )"""
    cursor.execute(sql)
    conn.commit()

#創建 好友 Table FK:req_from req_to OK
def build_friendship(conn):
    cursor.execute("DROP TABLE IF EXISTS friendship")
    sql = """CREATE TABLE friendship(
        friend_ship_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        request_from INT NOT NULL,
        request_to INT NOT NULL,
        status varchar(10)
    )"""
    cursor.execute(sql)
    conn.commit()


#創建 block (單篇文章) FK:member_id OK
def build_table_block(conn):
    cursor.execute("DROP TABLE IF EXISTS block")
    sql = """CREATE TABLE block(
        block_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        member_id INT NOT NULL,
        content_type varchar(25),
        content TEXT,
        build_time DATETIME,
        good INT DEFAULT 0,
        bad INT DEFAULT 0,
        block_img varchar(100)
    )"""
    cursor.execute(sql)
    conn.commit()

#block本身所攜帶的tag FK:block_id tag_id
def build_table_block_tag(conn):
    cursor.execute("DROP TABLE IF EXISTS block_tag")
    sql = """CREATE TABLE block_tag(
        block_tag_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        block_id INT NOT NULL,
        tag_id INT NOT NULL
    )"""
    cursor.execute(sql)
    conn.commit()

#創建 block的 comment(文章下的留言) FK:block_id ,member_id
def build_table_block_comment(conn):
    cursor.execute("DROP TABLE IF EXISTS block_comment")
    sql = """CREATE TABLE block_comment(
        comment_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        member_id INT NOT NULL,
        block_id INT NOT NULL,
        content TEXT,
        build_time DATETIME,
        nice_comment INT DEFAULT 0
    )"""
    cursor.execute(sql)
    conn.commit()

#通知
def build_table_nofiti(conn):
    cursor.execute("DROP TABLE IF EXISTS notifi")
    sql = """CREATE TABLE notifi(
        notifi_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        sender_id INT NOT NULL,
        reciever_id INT NOT NULL,
        content TEXT,
        read_time DATETIME
    )"""
    cursor.execute(sql)
    conn.commit()




#references
def build_foreign_key_ref(conn):
    sql1 = """ALTER TABLE tag
    ADD FOREIGN KEY (create_by) REFERENCES member(member_id)
    """
    sql2 = """ALTER TABLE member_tags
    ADD FOREIGN KEY (member_id) REFERENCES member(member_id),
    ADD FOREIGN KEY (tag_id) REFERENCES tag(tag_id)
    """
    sql3 = """ALTER TABLE friendship
    ADD FOREIGN KEY (request_from) REFERENCES member(member_id),
    ADD FOREIGN KEY (request_to) REFERENCES member(member_id)
    """
    sql4 = """ALTER TABLE block
    ADD FOREIGN KEY (member_id) REFERENCES member(member_id)
    """
    sql5 = """ALTER TABLE block_tag
    ADD FOREIGN KEY (block_id) REFERENCES block(block_id) ON DELETE CASCADE,
    ADD FOREIGN KEY (tag_id) REFERENCES tag(tag_id)
    """
    sql6 = """ALTER TABLE block_comment
    ADD FOREIGN KEY (block_id) REFERENCES block(block_id) ON DELETE CASCADE,
    ADD FOREIGN KEY (member_id) REFERENCES member(member_id)
    """
    sql7 = """ALTER TABLE notifi
    ADD FOREIGN KEY (sender_id) REFERENCES member(member_id),
    ADD FOREIGN KEY (reciever_id) REFERENCES member(member_id)
    """
    cursor.execute(sql1)
    cursor.execute(sql2)
    cursor.execute(sql3)
    cursor.execute(sql4)
    cursor.execute(sql5)
    cursor.execute(sql6)
    cursor.execute(sql7)
    conn.commit()

def auto_increment_set(conn):
    sql1= "ALTER TABLE block AUTO_INCREMENT=1000"
    sql2 = "ALTER TABLE member AUTO_INCREMENT=5000"
    sql3 = "ALTER TABLE tag AUTO_INCREMENT=3000"
    cursor.execute(sql1)
    cursor.execute(sql2)
    cursor.execute(sql3)
    conn.commit()


if __name__ == "__main__":
    load_dotenv()
    conn = pymysql.connect(charset='utf8', host=os.getenv("AWS_motivetag_DB"),
                           password=os.getenv("DB_PASS"), port=3306, user='root')
    cursor = conn.cursor()
    build_database(conn)
    build_member(conn)
    build_global_tag(conn)
    build_member_tags(conn)
    build_friendship(conn)
    build_table_block(conn)
    build_table_block_tag(conn)
    build_table_block_comment(conn)
    build_table_nofiti(conn)
    build_foreign_key_ref(conn)
    auto_increment_set(conn)
    cursor.close()
    conn.close()
