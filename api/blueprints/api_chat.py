import secrets

from flask import request, session
from flask_socketio import emit, join_room, leave_room
from flask_socketio import rooms as joined_rooms

from .. import socketio
from . import api_chat  # noqa: F401 - re-exported for api/__init__.py

online = {}  # {account:socketid}

rooms = {}  # {socket_id : {who?:room,who2:room2...}}

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
    online[me] = request.sid
    if came_online:
        tell_watchers(me, "on")


def go_offline(me):
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
    online_box = {}
    for a_friend in friend_list:
        if a_friend in online:
            online_box[a_friend] = "on"
            if online[a_friend] in rooms and me in rooms[online[a_friend]]:
                online_box[a_friend] = "on_calling"
        else:
            online_box[a_friend] = "off"
    emit("awake_result", online_box)


@socketio.on("logout")
def logout(data):
    me = current_account()
    if online.get(me) == request.sid:
        go_offline(me)
    return


@socketio.on("init_room")
def init_room(data):
    who_to_chat = data["account"]
    me = current_account()
    if who_to_chat not in online:
        emit("init_result", {"error": who_to_chat + " is not online"})
        return
    who_sid = online[who_to_chat]
    if who_sid in rooms and me in rooms[who_sid]:
        if request.sid not in rooms or len(rooms[request.sid]) == 0:
            rooms[request.sid] = {who_to_chat: rooms[who_sid][me]}
        join_room(rooms[who_sid][me])
        emit("init_result", {"ok": "JOINED", "room": rooms[who_sid][me]})
        emit(
            "message",
            {
                "type": "message",
                "to": who_to_chat,
                "from": me,
                "content": me + " JOINED!",
                "room": rooms[who_sid][me],
            },
            room=rooms[who_sid][me],
        )
        return
    new_room = "room" + secrets.token_hex(16)
    if request.sid not in rooms or len(rooms[request.sid]) == 0:
        rooms[request.sid] = {who_to_chat: new_room}
    else:
        rooms[request.sid].update({who_to_chat: new_room})
    join_room(new_room)
    emit("init_result", {"ok": "CREATED & WAITING", "room": new_room})
    push_to(who_to_chat, "awake_result", {me: "on_calling"})


@socketio.on("send")
def send_mess(data):
    room = data["room"]
    if room not in joined_rooms():
        return
    data["from"] = current_account()
    emit("message", data, room=room)


@socketio.on("connect")
def test_connect():
    me = current_account()
    if me is None:
        return False
    join_room(member_room(me))
    # Online from the moment the page connects, even for members without friends yet.
    go_online(me)
    emit("connected", {"data": "connected confirm"})


@socketio.on("disconnect")
def test_disconnect():
    if request.sid in rooms:
        del rooms[request.sid]
    me = current_account()
    if online.get(me) == request.sid:
        go_offline(me)


@socketio.on("left")
def left(message):
    """Sent by clients when they leave a room.
    A status message is broadcast to all people in the room."""
    me = current_account()
    room = message["room"]
    if room not in joined_rooms():
        return
    emit(
        "message",
        {
            "type": "message",
            "to": message["account"],
            "from": me,
            "content": me + " 離開了QQ!",
            "room": room,
        },
        room=room,
    )
    rooms.get(request.sid, {}).pop(message["account"], None)
    if message["account"] in online:
        push_to(message["account"], "awake_result", {me: "on"})
    emit("status", {"msg": me + " has left the room."}, room=room)
    leave_room(room)
