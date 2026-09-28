"""Limits the server enforces on what members send, whatever the browser checks."""

import re

POST_TYPES = {"PUBLIC", "SECRET", "Anonymous"}
POST_MAX = 2000
COMMENT_MAX = 500
MOOD_MAX = 100
POLL_MIN, POLL_MAX, POLL_OPTION_MAX = 2, 5, 40
SCORE_MIN, SCORE_MAX = -5, 5
TOPIC_TITLE_MAX, TOPIC_MAX, REPLY_MAX = 100, 5000, 2000
CHAT_MESSAGE_MAX = 1000
CHAT_PER_MINUTE = 30  # messages one member may send in a minute, to everyone together
TAG_NAME = re.compile(r"^\w{1,30}$")


def text(value, limit):
    """`value` stripped if it is non-empty text within `limit` characters, else None."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if 0 < len(value) <= limit else None


def integer(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
