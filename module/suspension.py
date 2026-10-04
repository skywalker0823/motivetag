"""Account suspension (App Store Guideline 1.2; the terms promise it).

A suspended member cannot sign in, and a session that is already open ends on its
next request (api/__init__.py) or socket connection. The owner suspends and lifts
on /admin (api/v1/admin.py). Their posts and comments stay; the owner deletes the
ones that break the rules from the reports.

Every request asks, so answers are kept in memory for a short while. There is one
worker (ADR 0008), so suspending or lifting here also clears that copy at once.
"""

import time
from datetime import datetime, timedelta

from data.data import Suspension
from module.clock import taipei_datetime

# "For good" is stored as a time no one will reach.
PERMANENT = datetime(9999, 12, 31)
DURATIONS = {1, 3, 7, 30}  # days the /admin page offers, besides for good
REASON_MAX = 200
CACHE_SECONDS = 30

_cache = {}  # {member_id: (checked at, {"until", "reason"} or None)}


def current(member_id):
    """{"until": datetime, "reason": str} while the member is suspended, else None."""
    now = time.monotonic()
    cached = _cache.get(member_id)
    if cached and now - cached[0] < CACHE_SECONDS:
        state = cached[1]
    else:
        row = Suspension.of(member_id)
        state = (
            {"until": row["suspended_until"], "reason": row["suspended_reason"]}
            if row and row["suspended_until"]
            else None
        )
        if len(_cache) > 10000:
            _cache.clear()
        _cache[member_id] = (now, state)
    if state and state["until"] > taipei_datetime():
        return state
    return None


def suspend(member_id, days, reason):
    """Suspends for `days` days, or for good when `days` is None; returns the end."""
    until = PERMANENT if days is None else taipei_datetime() + timedelta(days=days)
    Suspension.set(member_id, until, reason)
    _cache.pop(member_id, None)
    return until


def lift(member_id):
    Suspension.set(member_id, None, None)
    _cache.pop(member_id, None)


def is_permanent(until):
    return until >= PERMANENT


def message(state):
    """What the member is told when they try to sign in."""
    if is_permanent(state["until"]):
        text = "這個帳號已被永久停權"
    else:
        text = f"這個帳號已被停權至 {state['until'].strftime('%Y-%m-%d %H:%M')}"
    if state["reason"]:
        text += f"，原因：{state['reason']}"
    return text + "。如有疑問請透過服務條款中的聯絡方式與我們聯繫。"
