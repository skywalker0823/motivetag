"""Baseline schema taken from the original database/basic_data.sql.

Revision ID: 0001
Revises:
Create Date: 2026-09-26
"""
import sqlalchemy as sa
from alembic import op
from werkzeug.security import generate_password_hash

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TABLES = [
    """
CREATE TABLE `member` (
  `member_id` int NOT NULL AUTO_INCREMENT,
  `account` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `email` varchar(100) NOT NULL,
  `birthday` date DEFAULT NULL,
  `first_signup` date NOT NULL,
  `last_signin` datetime DEFAULT NULL,
  `member_img` varchar(100) DEFAULT NULL,
  `follower` int DEFAULT '0',
  `mood` varchar(100) DEFAULT NULL,
  `exp` int DEFAULT '0',
  PRIMARY KEY (`member_id`),
  UNIQUE KEY `account` (`account`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `tag` (
  `tag_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL,
  `popularity` int DEFAULT NULL,
  `create_date` date DEFAULT NULL,
  `create_by` int DEFAULT NULL,
  `prime_level` int DEFAULT NULL,
  PRIMARY KEY (`tag_id`),
  UNIQUE KEY `name` (`name`),
  KEY `create_by` (`create_by`),
  CONSTRAINT `tag_ibfk_1` FOREIGN KEY (`create_by`) REFERENCES `member` (`member_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `block` (
  `block_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `content_type` varchar(25) DEFAULT NULL,
  `content` text,
  `build_time` datetime DEFAULT NULL,
  `good` int DEFAULT '0',
  `bad` int DEFAULT '0',
  `block_img` varchar(100) DEFAULT NULL,
  `total_score` int DEFAULT '0',
  PRIMARY KEY (`block_id`),
  KEY `member_id` (`member_id`),
  CONSTRAINT `block_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `bads` (
  `bad_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `block_id` int NOT NULL,
  PRIMARY KEY (`bad_id`),
  KEY `member_id` (`member_id`),
  KEY `block_id` (`block_id`),
  CONSTRAINT `bads_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `bads_ibfk_2` FOREIGN KEY (`block_id`) REFERENCES `block` (`block_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `block_comment` (
  `comment_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `block_id` int NOT NULL,
  `content` text,
  `build_time` datetime DEFAULT NULL,
  `nice_comment` int DEFAULT '0',
  `given_score` int DEFAULT '0',
  PRIMARY KEY (`comment_id`),
  KEY `block_id` (`block_id`),
  KEY `member_id` (`member_id`),
  CONSTRAINT `block_comment_ibfk_1` FOREIGN KEY (`block_id`) REFERENCES `block` (`block_id`) ON DELETE CASCADE,
  CONSTRAINT `block_comment_ibfk_2` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `block_tag` (
  `block_tag_id` int NOT NULL AUTO_INCREMENT,
  `block_id` int NOT NULL,
  `tag_id` int NOT NULL,
  PRIMARY KEY (`block_tag_id`),
  KEY `block_id` (`block_id`),
  KEY `tag_id` (`tag_id`),
  CONSTRAINT `block_tag_ibfk_1` FOREIGN KEY (`block_id`) REFERENCES `block` (`block_id`) ON DELETE CASCADE,
  CONSTRAINT `block_tag_ibfk_2` FOREIGN KEY (`tag_id`) REFERENCES `tag` (`tag_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `bricks` (
  `brick_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int DEFAULT NULL,
  `tag_id` int DEFAULT NULL,
  `title` varchar(100) DEFAULT NULL,
  `content` text,
  `classifi` varchar(100) DEFAULT NULL,
  `feedbacks` int DEFAULT '0',
  `popularity` int DEFAULT '0',
  `time` datetime DEFAULT NULL,
  PRIMARY KEY (`brick_id`),
  KEY `member_id` (`member_id`),
  KEY `tag_id` (`tag_id`),
  CONSTRAINT `bricks_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE SET NULL,
  CONSTRAINT `bricks_ibfk_2` FOREIGN KEY (`tag_id`) REFERENCES `tag` (`tag_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `brick_discuss` (
  `brick_discuss_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int DEFAULT NULL,
  `brick_id` int DEFAULT NULL,
  `content` text,
  `time` datetime DEFAULT NULL,
  PRIMARY KEY (`brick_discuss_id`),
  KEY `member_id` (`member_id`),
  KEY `brick_id` (`brick_id`),
  CONSTRAINT `brick_discuss_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE SET NULL,
  CONSTRAINT `brick_discuss_ibfk_2` FOREIGN KEY (`brick_id`) REFERENCES `bricks` (`brick_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `c_goods` (
  `c_good_id` int NOT NULL AUTO_INCREMENT,
  `comment_id` int NOT NULL,
  `member_id` int NOT NULL,
  PRIMARY KEY (`c_good_id`),
  KEY `member_id` (`member_id`),
  KEY `comment_id` (`comment_id`),
  CONSTRAINT `c_goods_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `c_goods_ibfk_2` FOREIGN KEY (`comment_id`) REFERENCES `block_comment` (`comment_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `follower` (
  `follow_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `follow_who` int NOT NULL,
  PRIMARY KEY (`follow_id`),
  KEY `member_id` (`member_id`),
  KEY `follow_who` (`follow_who`),
  CONSTRAINT `follower_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `follower_ibfk_2` FOREIGN KEY (`follow_who`) REFERENCES `member` (`member_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `friendship` (
  `friend_ship_id` int NOT NULL AUTO_INCREMENT,
  `request_from` int NOT NULL,
  `request_to` int NOT NULL,
  `status` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`friend_ship_id`),
  KEY `request_from` (`request_from`),
  KEY `request_to` (`request_to`),
  CONSTRAINT `friendship_ibfk_1` FOREIGN KEY (`request_from`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `friendship_ibfk_2` FOREIGN KEY (`request_to`) REFERENCES `member` (`member_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `goods` (
  `good_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `block_id` int NOT NULL,
  PRIMARY KEY (`good_id`),
  KEY `member_id` (`member_id`),
  KEY `block_id` (`block_id`),
  CONSTRAINT `goods_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `goods_ibfk_2` FOREIGN KEY (`block_id`) REFERENCES `block` (`block_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `member_tags` (
  `member_tag_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `tag_id` int NOT NULL,
  PRIMARY KEY (`member_tag_id`),
  KEY `member_id` (`member_id`),
  KEY `tag_id` (`tag_id`),
  CONSTRAINT `member_tags_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `member_tags_ibfk_2` FOREIGN KEY (`tag_id`) REFERENCES `tag` (`tag_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `notifi` (
  `notifi_id` int NOT NULL AUTO_INCREMENT,
  `sender_id` int NOT NULL,
  `reciever_id` int NOT NULL,
  `content` text,
  `send_time` datetime DEFAULT NULL,
  PRIMARY KEY (`notifi_id`),
  KEY `sender_id` (`sender_id`),
  KEY `reciever_id` (`reciever_id`),
  CONSTRAINT `notifi_ibfk_1` FOREIGN KEY (`sender_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `notifi_ibfk_2` FOREIGN KEY (`reciever_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `vote_options` (
  `vote_option_id` int NOT NULL AUTO_INCREMENT,
  `block_id` int NOT NULL,
  `best_before` datetime DEFAULT NULL,
  `option_name` text,
  PRIMARY KEY (`vote_option_id`),
  KEY `block_id` (`block_id`),
  CONSTRAINT `vote_options_ibfk_1` FOREIGN KEY (`block_id`) REFERENCES `block` (`block_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    """
CREATE TABLE `votes` (
  `vote_id` int NOT NULL AUTO_INCREMENT,
  `member_id` int NOT NULL,
  `vote_option_id` int NOT NULL,
  PRIMARY KEY (`vote_id`),
  KEY `member_id` (`member_id`),
  KEY `vote_option_id` (`vote_option_id`),
  CONSTRAINT `votes_ibfk_1` FOREIGN KEY (`member_id`) REFERENCES `member` (`member_id`) ON DELETE CASCADE,
  CONSTRAINT `votes_ibfk_2` FOREIGN KEY (`vote_option_id`) REFERENCES `vote_options` (`vote_option_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
]


def upgrade():
    for statement in TABLES:
        op.execute(statement)
    # Rows the app relies on: the newcomer tag and the demo login shown on the home page.
    op.execute(
        "INSERT INTO tag (tag_id, name, popularity, prime_level) VALUES "
        "(3000, '新手引導', 0, 5), (3001, 'BroadCast', 0, 3), "
        "(3002, 'Anonymous', 0, 1), (3003, 'MotiveTag', 0, NULL)"
    )
    op.get_bind().execute(
        sa.text(
            "INSERT INTO member (member_id, account, password, email, first_signup) "
            "VALUES (5000, 'guest', :password, 'guest@mail.com', '1988-09-12')"
        ),
        {"password": generate_password_hash("guest")},
    )


def downgrade():
    op.execute("SET FOREIGN_KEY_CHECKS=0")
    for statement in reversed(TABLES):
        op.execute("DROP TABLE IF EXISTS `" + statement.split("`")[1] + "`")
    op.execute("SET FOREIGN_KEY_CHECKS=1")
