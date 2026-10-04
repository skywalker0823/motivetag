"""Too many wrong passwords for one account: sign-in is refused for a while.

Cloudflare limits requests per IP; this stops someone guessing one account's password
slowly or from many addresses (the owner's admin account above all). Kept in memory:
there is one worker (ADR 0008), and a restart only gives a guesser a fresh start.
"""

import time
from collections import deque

MAX_FAILURES = 10
WINDOW_SECONDS = 15 * 60

_failures = {}  # {account (lower case): deque of monotonic times}


def _recent(account, now):
    times = _failures.get(account.lower())
    if not times:
        return None
    while times and now - times[0] > WINDOW_SECONDS:
        times.popleft()
    if not times:
        del _failures[account.lower()]
        return None
    return times


def locked(account):
    """Seconds until `account` may try again, or 0."""
    now = time.monotonic()
    times = _recent(account, now)
    if times is None or len(times) < MAX_FAILURES:
        return 0
    return int(WINDOW_SECONDS - (now - times[0])) + 1


def failed(account):
    now = time.monotonic()
    if len(_failures) > 100000:
        _failures.clear()
    times = _recent(account, now) or _failures.setdefault(account.lower(), deque())
    times.append(now)
    if len(times) > MAX_FAILURES:
        times.popleft()


def succeeded(account):
    _failures.pop(account.lower(), None)
