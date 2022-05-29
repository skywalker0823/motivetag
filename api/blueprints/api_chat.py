
from flask import request, session
from flask_socketio import emit, join_room, leave_room
from random import randint
from .. import socketio
from . import api_chat
import time

online = {}  # {account:socketid}這裡是目前在線上的人

rooms = {}  # {socket_id : {who?:room,who2:room2...}} #兩個人都要有一樣的紀錄


#此功能可以保留
#朋友誰在線上檢查器
@socketio.on('awake')
def init_chat(data):
    online[data["account"]]=request.sid#1.簽到
    # print("ONLINE狀態:",online)
    # print("ROOMS狀態:", rooms)
    friend_list = data["check_who_is_awake_too"]#{111:"off",222:"off"}
    online_box = {}
    for a_friend in friend_list:#2.查寢
        if a_friend in online:
            online_box[a_friend] = "on"
            if online[a_friend] in rooms and data["account"] in rooms[online[a_friend]]:#3.在且正在扣
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
    #此程式碼將會檢查該使用者想聊天對象有無開房間(正在等自己)
    #若有加入，若無會新開一個房間 並且等對方加入
    who_to_chat = data["account"]
    me = data["me"]
    if who_to_chat not in online:
        emit("init_result",{"error":who_to_chat+" is not online"})
        return
    who_sid = online[who_to_chat]
    #優先確定對方有無房間在給自己 {socket_id : {who?:room,who2:room2...}}
    #加入
    if who_sid in rooms and me in rooms[who_sid]:  # 對方在等自己！
        # ROOMS[request.sid][who_to_chat]=ROOMS[who_sid][me]
        if request.sid not in rooms or len(rooms[request.sid]) == 0:
            rooms[request.sid] = {who_to_chat: rooms[who_sid][me]}
        #將自己進入對方房間
        join_room(rooms[who_sid][me])
        emit("init_result", {"ok": "JOINED", "room": rooms[who_sid][me]})
        emit("message", {"type": "message", "to": who_to_chat, "from": me,
             "content": me+" JOINED!", "room":rooms[who_sid][me]}, room=rooms[who_sid][me])
        return
    #自開
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

#uid status
@socketio.on('connect')
def test_connect():
    # print('Client connected',request.sid)
    emit("connected",{"data":"connected confirm"})

#User logout clear all the room created
@socketio.on('disconnect')
def test_disconnect():
    if request.sid in rooms:
        del rooms[request.sid]
    # print('Client disconnected',request.sid)

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


