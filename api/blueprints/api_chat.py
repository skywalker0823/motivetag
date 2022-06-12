
from flask import request, session
from flask_socketio import emit, join_room, leave_room
from random import randint
from .. import socketio
from . import api_chat
import time

online = {}  # {account:socketid}

rooms = {}  # {socket_id : {who?:room,who2:room2...}}


@socketio.on('awake')
def init_chat(data):
    online[data["account"]]=request.sid
    friend_list = data["check_who_is_awake_too"]
    online_box = {}
    for a_friend in friend_list:
        if a_friend in online:
            online_box[a_friend] = "on"
            if online[a_friend] in rooms and data["account"] in rooms[online[a_friend]]:
                online_box[a_friend] = "on_calling"
        else:
            online_box[a_friend] = "off"
    emit("awake_result",online_box)


@socketio.on('logout')
def init_chat(data):
    del online[data["account"]]
    return


@socketio.on("init_room")
def init_room(data):
    who_to_chat = data["account"]
    me = data["me"]
    if who_to_chat not in online:
        emit("init_result",{"error":who_to_chat+" is not online"})
        return
    who_sid = online[who_to_chat]
    if who_sid in rooms and me in rooms[who_sid]:
        if request.sid not in rooms or len(rooms[request.sid]) == 0:
            rooms[request.sid] = {who_to_chat: rooms[who_sid][me]}
        join_room(rooms[who_sid][me])
        emit("init_result", {"ok": "JOINED", "room": rooms[who_sid][me]})
        emit("message", {"type": "message", "to": who_to_chat, "from": me,
             "content": me+" JOINED!", "room":rooms[who_sid][me]}, room=rooms[who_sid][me])
        return
    new_room = "room"+str(randint(10000, 99999))+str(time.time())
    if request.sid not in rooms or len(rooms[request.sid]) == 0:
        rooms[request.sid] = {who_to_chat:new_room}
    else:
        rooms[request.sid].update({who_to_chat: new_room})
    join_room(new_room)
    emit("init_result", {"ok": "CREATED & WAITING", "room": new_room})


@socketio.on('send')
def send_mess(data):
    room = data["room"]
    emit("message",data,room=room)


@socketio.on('connect')
def test_connect():
    emit("connected",{"data":"connected confirm"})


@socketio.on('disconnect')
def test_disconnect():
    if request.sid in rooms:
        del rooms[request.sid]


@socketio.on('left')
def left(message):
    """Sent by clients when they leave a room.
    A status message is broadcast to all people in the room."""
    emit("message", {"type": "message", "to": message["account"], "from": message["me"],
                     "content": message["me"]+" 離開了QQ!", "room": message["room"]}, room=message["room"])
    del rooms[request.sid][message["account"]]
    room = message["room"]
    emit('status', {'msg': session.get("account") +
         ' has left the room.'}, room=room)
    leave_room(room)