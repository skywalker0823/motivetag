
from flask import request, session
from flask_socketio import emit, join_room, leave_room, rooms as joined_rooms
from random import randint
from .. import socketio
from . import api_chat
import time

online = {}  # {account:socketid}

rooms = {}  # {socket_id : {who?:room,who2:room2...}}


# Identity always comes from the Flask session, never from what the client sends.
def current_account():
    return session.get("account")


@socketio.on('awake')
def init_chat(data):
    me = current_account()
    online[me] = request.sid
    friend_list = data["check_who_is_awake_too"]
    online_box = {}
    for a_friend in friend_list:
        if a_friend in online:
            online_box[a_friend] = "on"
            if online[a_friend] in rooms and me in rooms[online[a_friend]]:
                online_box[a_friend] = "on_calling"
        else:
            online_box[a_friend] = "off"
    emit("awake_result", online_box)


@socketio.on('logout')
def init_chat(data):
    me = current_account()
    if online.get(me) == request.sid:
        del online[me]
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
        emit("message", {"type": "message", "to": who_to_chat, "from": me,
             "content": me + " JOINED!", "room": rooms[who_sid][me]}, room=rooms[who_sid][me])
        return
    new_room = "room" + str(randint(10000, 99999)) + str(time.time())
    if request.sid not in rooms or len(rooms[request.sid]) == 0:
        rooms[request.sid] = {who_to_chat: new_room}
    else:
        rooms[request.sid].update({who_to_chat: new_room})
    join_room(new_room)
    emit("init_result", {"ok": "CREATED & WAITING", "room": new_room})


@socketio.on('send')
def send_mess(data):
    room = data["room"]
    if room not in joined_rooms():
        return
    data["from"] = current_account()
    emit("message", data, room=room)


@socketio.on('connect')
def test_connect():
    if current_account() is None:
        return False
    emit("connected", {"data": "connected confirm"})


@socketio.on('disconnect')
def test_disconnect():
    if request.sid in rooms:
        del rooms[request.sid]
    me = current_account()
    if online.get(me) == request.sid:
        del online[me]


@socketio.on('left')
def left(message):
    """Sent by clients when they leave a room.
    A status message is broadcast to all people in the room."""
    me = current_account()
    room = message["room"]
    if room not in joined_rooms():
        return
    emit("message", {"type": "message", "to": message["account"], "from": me,
                     "content": me + " 離開了QQ!", "room": room}, room=room)
    rooms.get(request.sid, {}).pop(message["account"], None)
    emit('status', {'msg': me +
         ' has left the room.'}, room=room)
    leave_room(room)
