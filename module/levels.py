"""Levels and experience points (ADR 0015); static/js/lib/levels.js mirrors the numbers.

Exp rewards what others value (likes and comments on what you wrote) more than raw
activity, and every action has a daily cap, so posting "安安" twenty times earns no
more than a normal day. Reaching level n takes 50·(n−1)² exp in total:

    Lv 2: 50   Lv 3: 200   Lv 5: 800   Lv 10: 4,050   Lv 20: 18,050

An active member (a visit, a post, a few comments and likes given and received)
earns about 60 a day: Lv 2 on the first day, Lv 3 within the first week, Lv 5 in
about two weeks, Lv 10 after two to three months.
"""

import math
from datetime import timedelta

from data.data import Level
from module.clock import taipei_datetime

STEP = 50

# action: (exp, how many times a day it counts)
REWARDS = {
    "daily_visit": (10, 1),
    "streak_week": (50, 1),  # every 7th day in a row
    "post": (20, 3),
    "comment": (5, 10),
    "like_given": (1, 20),
    "like_received": (5, 20),
    "comment_received": (3, 20),
    "comment_like_received": (3, 20),
    "friend_made": (10, 5),
}

# Below Lv 3 (reached by others liking and answering you, or on day two at the
# earliest by yourself) posts are limited, against throwaway spam accounts.
TOPICS_LEVEL = 3  # also opens discussions on a tag's board
NEWCOMER_POSTS_PER_DAY = 10
FRAME_LEVEL = 5  # avatar frame in the tier's colour
TRUSTED_LEVEL = 10  # reports count double
TRUSTED_REPORT_WEIGHT = 2

# Shown on the level card: what the next levels unlock.
PERKS = [
    (TOPICS_LEVEL, "發文不限篇數、在標籤討論區發起討論、綠色等級徽章"),
    (FRAME_LEVEL, "頭像外框、藍色等級徽章"),
    (TRUSTED_LEVEL, "資深會員：檢舉加倍計算、紫色等級徽章"),
    (20, "金色等級徽章"),
]


def level_of(exp):
    return math.isqrt(max(int(exp or 0), 0) // STEP) + 1


def exp_for(level):
    """Total exp needed to reach `level`."""
    return STEP * (level - 1) ** 2


def award(member_id, action):
    """Gives `member_id` the exp for `action` unless today's cap is reached; returns it.

    Their open tabs hear about it ("exp" event), with level_up when they went up.
    """
    exp, cap = REWARDS[action]
    if not member_id or Level.count_today(member_id, action, taipei_datetime().date()) > cap:
        return 0
    before, after, account = Level.add_exp(member_id, exp)
    from api.blueprints.api_chat import push_to  # the socket layer imports this module

    push_to(
        account,
        "exp",
        {
            "exp": after,
            "level": level_of(after),
            "gained": exp,
            "action": action,
            "level_up": level_of(after) > level_of(before),
        },
    )
    return exp


def daily_visit(member_id):
    """The first visit of a Taipei day: +10, and +50 on every 7th day in a row.

    Returns {"gained", "streak"} for the page to mention, or None if already counted.
    """
    today = taipei_datetime().date()
    last, streak = Level.last_visit(member_id)
    if last == today:
        return None
    streak = streak + 1 if last == today - timedelta(days=1) else 1
    Level.set_visit(member_id, today, streak)
    Level.purge(today - timedelta(days=2))  # yesterday's caps no longer matter
    gained = award(member_id, "daily_visit")
    if streak % 7 == 0:
        gained += award(member_id, "streak_week")
    return {"gained": gained, "streak": streak}
