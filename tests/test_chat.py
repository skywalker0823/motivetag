def payload(message):
    args = message["args"]
    return args[0] if isinstance(args, list) else args


def test_anonymous_socket_rejected(app, socket_client):
    assert not socket_client(app.test_client()).is_connected()


def test_chat_identity_comes_from_session(member, socket_client, chat_state):
    alice, _, alice_account = member()
    _, _, bob_account = member()
    sa = socket_client(alice)
    assert sa.is_connected()
    sa.emit("awake", {"account": bob_account, "check_who_is_awake_too": []})
    assert alice_account in chat_state.online
    assert bob_account not in chat_state.online


def test_only_room_members_can_post(member, socket_client):
    alice, _, alice_account = member()
    bob, _, bob_account = member()
    carol, _, _ = member()
    sa, sb, sc = socket_client(alice), socket_client(bob), socket_client(carol)
    sa.emit("awake", {"check_who_is_awake_too": []})
    sb.emit("awake", {"check_who_is_awake_too": []})
    sa.emit("init_room", {"account": bob_account})
    room = [payload(m) for m in sa.get_received() if m["name"] == "init_result"][-1]["room"]
    sb.emit("init_room", {"account": alice_account})
    sa.get_received()

    sc.emit("send", {"room": room, "content": "intruder"})
    assert not [m for m in sa.get_received() if m["name"] == "message"]

    sb.emit("send", {"room": room, "from": alice_account, "content": "hi"})
    messages = [payload(m) for m in sa.get_received() if m["name"] == "message"]
    assert messages[-1]["from"] == bob_account


def test_cannot_log_out_someone_else(member, socket_client, chat_state):
    alice, _, alice_account = member()
    carol, _, _ = member()
    socket_client(alice).emit("awake", {"check_who_is_awake_too": []})
    socket_client(carol).emit("logout", {"account": alice_account})
    assert alice_account in chat_state.online


def presence_updates(client):
    return [payload(m) for m in client.get_received() if m["name"] == "awake_result"]


def test_friends_hear_when_someone_comes_and_goes(member, socket_client):
    alice, _, alice_account = member()
    bob, _, bob_account = member()
    sa = socket_client(alice)
    sa.emit("awake", {"check_who_is_awake_too": {bob_account: "off"}})
    assert presence_updates(sa)[-1] == {bob_account: "off"}

    sb = socket_client(bob)
    assert {bob_account: "on"} in presence_updates(sa)

    sb.emit("logout", {})
    assert {bob_account: "off"} in presence_updates(sa)


def test_a_call_is_pushed_to_the_one_called(member, socket_client):
    alice, _, alice_account = member()
    bob, _, bob_account = member()
    sa, sb = socket_client(alice), socket_client(bob)
    sb.get_received()
    sa.emit("init_room", {"account": bob_account})
    assert {alice_account: "on_calling"} in presence_updates(sb)


def test_notifications_are_pushed(member, socket_client):
    alice, _, _ = member()
    bob, _, bob_account = member()
    sb = socket_client(bob)
    sb.get_received()
    alice.post("/api/notifi", json={"who": bob_account, "type": "friend_invite"})
    assert [m for m in sb.get_received() if m["name"] == "notification"]
