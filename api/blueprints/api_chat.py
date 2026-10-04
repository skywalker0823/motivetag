"""Socket.IO side of presence and chat.

Every tab of a member joins the room `member:<account>`; the server pushes presence,
notifications and chat messages there (chat itself is stored and sent over HTTP, see
api/v1/chats.py). Presence is kept in memory, which is why there is one worker (ADR 0008).
"""

from flask import request, session
from flask_socketio import emit, join_room

from api.metrics import ONLINE
from data.data import Friend, Member, MemberBlock
from module import suspension

from .. import socketio
from . import api_chat  # noqa: F401 - re-exported for api/__init__.py

online = {}  # {account: {socket ids of their open tabs}}
ONLINE.set_function(lambda: len(online))

watching = {}  # {account: {friends whose presence they asked about}}
watchers = {}  # the reverse: {account: {who wants to hear when it changes}}
MAX_WATCHED = 1000


def member_room(account):
    """Every tab of one member joins this room, so the server can push to them."""
    return "member:" + account


def push_to(account, event, data):
    socketio.emit(event, data, to=member_room(account))


def tell_watchers(account, state):
    """`account` came online or went away: tell the friends who are looking."""
    for watcher in list(watchers.get(account, ())):
        if watcher in online:
            push_to(watcher, "awake_result", {account: state})


def watch(me, friends):
    unwatch(me)
    watching[me] = friends
    for friend in friends:
        watchers.setdefault(friend, set()).add(me)


def unwatch(me):
    for friend in watching.pop(me, ()):
        others = watchers.get(friend)
        if others:
            others.discard(me)
            if not others:
                del watchers[friend]


def go_online(me):
    came_online = me not in online
    online.setdefault(me, set()).add(request.sid)
    if came_online:
        tell_watchers(me, "on")


def go_offline(me):
    """This tab went away; the member is offline once their last tab has."""
    tabs = online.get(me)
    if tabs is None:
        return
    tabs.discard(request.sid)
    if tabs:
        return
    del online[me]
    unwatch(me)
    tell_watchers(me, "off")


# Identity always comes from the Flask session, never from what the client sends.
def current_account():
    return session.get("account")


@socketio.on("awake")
def init_chat(data):
    me = current_account()
    friend_list = data["check_who_is_awake_too"]
    watch(me, {f for f in list(friend_list)[:MAX_WATCHED] if isinstance(f, str) and f != me})
    go_online(me)
    emit("awake_result", {friend: "on" if friend in online else "off" for friend in friend_list})


@socketio.on("logout")
def logout(data):
    go_offline(current_account())


@socketio.on("chat:typing")
def typing(data):
    """Tells a friend I am typing to them. The browser sends this at most every few seconds."""
    me = current_account()
    to = data.get("to") if isinstance(data, dict) else None
    if not isinstance(to, str) or to == me or to not in online:
        return
    to_id = Member.id_for(to)
    me_id = session.get("member_id")
    if to_id is None or not Friend.are_friends(me_id, to_id) or MemberBlock.between(me_id, to_id):
        return
    push_to(to, "chat:typing", {"from": me})


def end_sessions(account):
    """Signs a suspended member's open tabs out: they hear why, then the server hangs up."""
    push_to(account, "account:suspended", {})
    for sid in list(online.get(account, ())):
        socketio.server.disconnect(sid, namespace="/")


@socketio.on("connect")
def test_connect():
    me = current_account()
    if me is None or suspension.current(session["member_id"]):
        return False
    join_room(member_room(me))
    # Online from the moment the page connects, even for members without friends yet.
    go_online(me)
    emit("connected", {"data": "connected confirm"})


@socketio.on("disconnect")
def test_disconnect():
    go_offline(current_account())
