import pymysql
import os
from dotenv import load_dotenv

#Build database
def build_database(conn):
    cursor.execute("DROP DATABASE IF EXISTS motivetag")
    cursor.execute("CREATE DATABASE motivetag")
    cursor.execute("USE motivetag")
    conn.commit()

#Build member Table
def build_member(conn):
    cursor.execute("DROP TABLE IF EXISTS member")
    sql = """CREATE TABLE member(
        member_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        account varchar(50) UNIQUE KEY NOT NULL,
        password varchar(50) NOT NULL,
        email varchar(100) NOT NULL,
        birthday DATE,
        first_signup DATE NOT NULL,
        last_signin DATETIME,
        member_img varchar(100),
        follower INT default 0,
        mood VARCHAR(100),
        exp INT default 0
    )"""
    cursor.execute(sql)
    conn.commit()

#Build tag table
def build_global_tag(conn):
    cursor.execute("DROP TABLE IF EXISTS tag")
    sql = """CREATE TABLE tag(
        tag_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        name varchar(100) UNIQUE KEY,
        popularity INT,
        create_date DATE,
        create_by INT,
        prime_level INT
    )"""
    cursor.execute(sql)
    conn.commit()

#Build member_tags table
def build_member_tags(conn):
    cursor.execute("DROP TABLE IF EXISTS member_tags")
    sql = """CREATE TABLE member_tags(
        member_tag_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        member_id INT NOT NULL,
        tag_id INT NOT NULL
    )"""
    cursor.execute(sql)
    conn.commit()

#Build friendship table
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

#Build block table
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
        block_img varchar(100),
        total_score INT DEFAULT 0
    )"""
    cursor.execute(sql)
    conn.commit()

#Build block_tag table
def build_table_block_tag(conn):
    cursor.execute("DROP TABLE IF EXISTS block_tag")
    sql = """CREATE TABLE block_tag(
        block_tag_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        block_id INT NOT NULL,
        tag_id INT NOT NULL
    )"""
    cursor.execute(sql)
    conn.commit()

#Build block_comment table
def build_table_block_comment(conn):
    cursor.execute("DROP TABLE IF EXISTS block_comment")
    sql = """CREATE TABLE block_comment(
        comment_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        member_id INT NOT NULL,
        block_id INT NOT NULL,
        content TEXT,
        build_time DATETIME,
        nice_comment INT DEFAULT 0,
        given_score INT DEFAULT 0
    )"""
    cursor.execute(sql)
    conn.commit()

#Build notification table
def build_table_nofiti(conn):
    cursor.execute("DROP TABLE IF EXISTS notifi")
    sql = """CREATE TABLE notifi(
        notifi_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        sender_id INT NOT NULL,
        reciever_id INT NOT NULL,
        content TEXT,
        send_time DATETIME
    )"""
    cursor.execute(sql)
    conn.commit()

#Build vote_options table
def vote_options(conn):
    cursor.execute("DROP TABLE IF EXISTS vote_options")
    sql = """CREATE TABLE vote_options(
        vote_option_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        block_id INT NOT NULL,
        best_before datetime,
        option_name TEXT
    )"""
    cursor.execute(sql)
    conn.commit()

#Build votes table
def votes(conn):
    cursor.execute("DROP TABLE IF EXISTS votes")
    sql = """CREATE TABLE votes(
        vote_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        member_id INT NOT NULL,
        vote_option_id INT NOT NULL
    )"""
    cursor.execute(sql)
    conn.commit()

#Build good table
def goods(conn):
    cursor.execute("DROP TABLE IF EXISTS goods")
    sql = """CREATE TABLE goods(
        good_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        member_id INT NOT NULL,
        block_id INT NOT NULL
    )"""
    cursor.execute(sql)
    conn.commit()

#Build comment_good table
def c_goods(conn):
    cursor.execute("DROP TABLE IF EXISTS c_goods")
    sql = """CREATE TABLE c_goods(
        c_good_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        comment_id INT NOT NULL,
        member_id INT NOT NULL
    )"""
    cursor.execute(sql)
    conn.commit()

#Build bad table
def bads(conn):
    cursor.execute("DROP TABLE IF EXISTS bads")
    sql = """CREATE TABLE bads(
        bad_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        member_id INT NOT NULL,
        block_id INT NOT NULL
    )"""
    cursor.execute(sql)
    conn.commit()

#Build bricks table
def bricks(conn):
    cursor.execute("DROP TABLE IF EXISTS bricks")
    sql = """CREATE TABLE bricks(
        brick_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        member_id INT,
        tag_id INT,
        title varchar(100),
        content TEXT,
        classifi varchar(100),
        feedbacks INT default 0,
        popularity INT default 0,
        time DATETIME
    )
    """
    cursor.execute(sql)
    conn.commit()

#Build brick_discuss table
def brick_discuss(conn):
    cursor.execute("DROP TABLE IF EXISTS brick_discuss")
    sql = """CREATE TABLE brick_discuss(
        brick_discuss_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        member_id INT,
        brick_id INT,
        content TEXT,
        time datetime
    )
    """
    cursor.execute(sql)
    conn.commit()

#Build follower table
def follower(conn):
    cursor.execute("DROP TABLE IF EXISTS follower")
    sql = """CREATE TABLE follower(
        follow_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        member_id INT NOT NULL,
        follow_who INT NOT NULL
    )"""
    cursor.execute(sql)
    conn.commit()

#References
def build_foreign_key_ref(conn):
    sql1 = """ALTER TABLE tag
    ADD FOREIGN KEY (create_by) REFERENCES member(member_id)
    """
    sql2 = """ALTER TABLE member_tags
    ADD FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE CASCADE,
    ADD FOREIGN KEY (tag_id) REFERENCES tag(tag_id)
    """
    sql3 = """ALTER TABLE friendship
    ADD FOREIGN KEY (request_from) REFERENCES member(member_id) ON DELETE CASCADE,
    ADD FOREIGN KEY (request_to) REFERENCES member(member_id) ON DELETE CASCADE
    """
    sql4 = """ALTER TABLE block
    ADD FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE CASCADE
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
    ADD FOREIGN KEY (sender_id) REFERENCES member(member_id) ON DELETE CASCADE,
    ADD FOREIGN KEY (reciever_id) REFERENCES member(member_id) ON DELETE CASCADE
    """
    sql8 = """ALTER TABLE vote_options
    ADD FOREIGN KEY (block_id) REFERENCES block(block_id) ON DELETE CASCADE
    """
    sql9 = """ALTER TABLE votes
    ADD FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE CASCADE,
    ADD FOREIGN KEY (vote_option_id) REFERENCES vote_options(vote_option_id) ON DELETE CASCADE
    """
    sql10 = """ALTER TABLE goods
    ADD FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE CASCADE,
    ADD FOREIGN KEY (block_id) REFERENCES block(block_id) ON DELETE CASCADE
    """
    sql11 = """ALTER TABLE c_goods
    ADD FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE CASCADE,
    ADD FOREIGN KEY (comment_id) REFERENCES block_comment(comment_id) ON DELETE CASCADE
    """
    sql12 = """ALTER TABLE bads
    ADD FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE CASCADE,
    ADD FOREIGN KEY (block_id) REFERENCES block(block_id) ON DELETE CASCADE
    """
    sql13 = """ALTER TABLE bricks
    ADD FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE SET NULL,
    ADD FOREIGN KEY (tag_id) REFERENCES tag(tag_id) ON DELETE SET NULL
    """
    sql14 = """ALTER TABLE brick_discuss
    ADD FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE SET NULL,
    ADD FOREIGN KEY (brick_id) REFERENCES bricks(brick_id) ON DELETE SET NULL
    """
    sql15 = """ALTER TABLE follower
    ADD FOREIGN KEY (member_id) REFERENCES member(member_id) ON DELETE CASCADE,
    ADD FOREIGN KEY (follow_who) REFERENCES member(member_id) ON DELETE CASCADE
    """

    cursor.execute(sql1)
    cursor.execute(sql2)
    cursor.execute(sql3)
    cursor.execute(sql4)
    cursor.execute(sql5)
    cursor.execute(sql6)
    cursor.execute(sql7)
    cursor.execute(sql8)
    cursor.execute(sql9)
    cursor.execute(sql10)
    cursor.execute(sql11)
    cursor.execute(sql12)
    cursor.execute(sql13)
    cursor.execute(sql14)
    cursor.execute(sql15)
    conn.commit()

#Auto_increment start
def auto_increment_set(conn):
    sql1= "ALTER TABLE block AUTO_INCREMENT=1000"
    sql2 = "ALTER TABLE member AUTO_INCREMENT=5000"
    sql3 = "ALTER TABLE tag AUTO_INCREMENT=3000"
    cursor.execute(sql1)
    cursor.execute(sql2)
    cursor.execute(sql3)
    conn.commit()

#Tag given
def pre_insert_tags(conn):
    cursor.execute("INSERT INTO tag(name,popularity,prime_level)VALUES(%s,%s,%s)",("新手引導",0,5))
    cursor.execute("INSERT INTO tag(name,popularity,prime_level)VALUES(%s,%s,%s)",("BroadCast",0,3))
    cursor.execute("INSERT INTO tag(name,popularity,prime_level)VALUES(%s,%s,%s)",("Anonymous",0,1))
    cursor.execute("INSERT INTO tag(name,popularity,prime_level)VALUES(%s,%s,%s)",("MotiveTag",0,None))
    conn.commit()


if __name__ == "__main__":
    load_dotenv()
    conn = pymysql.connect(charset='utf8', host=os.getenv("DB_BK2"),
                           password=os.getenv("DB_PASSWORD"), port=3306, user='root')
    cursor = conn.cursor()
    print("databases connected, start building tables...")
    build_database(conn)
    build_member(conn)
    build_global_tag(conn)
    build_member_tags(conn)
    build_friendship(conn)
    build_table_block(conn)
    build_table_block_tag(conn)
    build_table_block_comment(conn)
    build_table_nofiti(conn)
    vote_options(conn)
    votes(conn)
    goods(conn)
    c_goods(conn)
    bads(conn)
    bricks(conn)
    brick_discuss(conn)
    follower(conn)
    
    print("tables built, start building foreign key references...")
    build_foreign_key_ref(conn)
    auto_increment_set(conn)
    pre_insert_tags(conn)
    print("OK")
    cursor.close()
    conn.close()
