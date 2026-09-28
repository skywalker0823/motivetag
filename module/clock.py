from datetime import datetime, timedelta, timezone

# The database stores Taiwan wall-clock times (the site's users are in Taiwan, which
# has no daylight saving), so the server stamps new rows itself instead of trusting
# the time a browser sends.
TAIPEI = timezone(timedelta(hours=8))


def taipei_now():
    return datetime.now(TAIPEI).strftime("%Y-%m-%d %H:%M:%S")


def taipei_datetime():
    """Now as a naive Taiwan wall-clock datetime, the form DATETIME columns hold."""
    return datetime.now(TAIPEI).replace(tzinfo=None, microsecond=0)
