def payload(message):
    args = message["args"]
    return args[0] if isinstance(args, list) else args


def events(client, name):
    return [payload(m) for m in client.get_received() if m["name"] == name]


def befriend(query, a_id, b_id):
    query(
        "INSERT INTO friendship (request_from, request_to, status) VALUES (%s, %s, '0')",
        a_id,
        b_id,
    )


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


def test_cannot_log_out_someone_else(member, socket_client, chat_state):
    alice, _, alice_account = member()
    carol, _, _ = member()
    socket_client(alice).emit("awake", {"check_who_is_awake_too": []})
    socket_client(carol).emit("logout", {"account": alice_account})
    assert alice_account in chat_state.online


def test_online_until_the_last_tab_goes(member, socket_client, chat_state):
    alice, _, alice_account = member()
    tab1, tab2 = socket_client(alice), socket_client(alice)
    tab1.disconnect()
    assert alice_account in chat_state.online
    tab2.disconnect()
    assert alice_account not in chat_state.online


def presence_updates(client):
    return events(client, "awake_result")


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


def test_notifications_are_pushed(member, socket_client):
    alice, _, _ = member()
    bob, _, bob_account = member()
    sb = socket_client(bob)
    sb.get_received()
    alice.post("/api/notifi", json={"who": bob_account, "type": "friend_invite"})
    assert [m for m in sb.get_received() if m["name"] == "notification"]


def test_only_friends_can_message(member):
    alice, _, _ = member()
    _, _, bob_account = member()
    response = alice.post(f"/api/v1/chats/{bob_account}/messages", json={"content": "hi"})
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "not_friends"


def test_message_reaches_every_tab_even_if_the_chat_was_never_opened(member, socket_client, query):
    alice, alice_id, alice_account = member()
    bob, bob_id, bob_account = member()
    befriend(query, alice_id, bob_id)
    bob_phone, bob_laptop, alice_other_tab = (
        socket_client(bob),
        socket_client(bob),
        socket_client(alice),
    )
    for client in (bob_phone, bob_laptop, alice_other_tab):
        client.get_received()

    response = alice.post(f"/api/v1/chats/{bob_account}/messages", json={"content": " 嗨 😀 "})
    assert response.status_code == 201
    sent = response.get_json()["data"]
    assert sent["from"] == alice_account and sent["to"] == bob_account
    assert sent["content"] == "嗨 😀" and sent["read_at"] is None

    for client in (bob_phone, bob_laptop, alice_other_tab):
        assert events(client, "chat:message") == [sent]


def test_offline_member_finds_the_message_later(member, query):
    alice, alice_id, alice_account = member()
    bob, bob_id, bob_account = member()
    befriend(query, alice_id, bob_id)
    alice.post(f"/api/v1/chats/{bob_account}/messages", json={"content": "one"})
    alice.post(f"/api/v1/chats/{bob_account}/messages", json={"content": "two"})

    chats = bob.get("/api/v1/chats").get_json()
    assert chats["unread"] == 2
    assert chats["data"][0]["partner"]["account"] == alice_account
    assert chats["data"][0]["last"]["content"] == "two"
    assert chats["data"][0]["unread"] == 2

    history = bob.get(f"/api/v1/chats/{alice_account}/messages").get_json()
    assert [m["content"] for m in history["data"]] == ["one", "two"]
    assert history["can_send"] is True


def test_reading_sends_a_receipt(member, socket_client, query):
    alice, alice_id, alice_account = member()
    bob, bob_id, bob_account = member()
    befriend(query, alice_id, bob_id)
    sent = alice.post(f"/api/v1/chats/{bob_account}/messages", json={"content": "hi"}).get_json()
    sa = socket_client(alice)
    sa.get_received()

    result = bob.post(f"/api/v1/chats/{alice_account}/read", json={"up_to": sent["data"]["id"]})
    assert result.get_json()["data"]["read"] == 1
    receipt = events(sa, "chat:read")[-1]
    assert receipt["by"] == bob_account and receipt["up_to"] == sent["data"]["id"]
    assert bob.get("/api/v1/chats").get_json()["unread"] == 0

    # Alice cannot mark her own messages read for Bob.
    alice.post(f"/api/v1/chats/{bob_account}/messages", json={"content": "again"})
    alice.post(f"/api/v1/chats/{bob_account}/read", json={"up_to": 10**12})
    assert bob.get("/api/v1/chats").get_json()["unread"] == 1


def test_history_pages_back(member, query, monkeypatch):
    monkeypatch.setattr("module.rules.CHAT_PER_MINUTE", 100)
    alice, alice_id, _ = member()
    _, bob_id, bob_account = member()
    befriend(query, alice_id, bob_id)
    for n in range(35):
        alice.post(f"/api/v1/chats/{bob_account}/messages", json={"content": str(n)})
    first = alice.get(f"/api/v1/chats/{bob_account}/messages").get_json()
    assert [m["content"] for m in first["data"]] == [str(n) for n in range(5, 35)]
    assert first["more"] is True
    older = alice.get(
        f"/api/v1/chats/{bob_account}/messages", query_string={"before": first["data"][0]["id"]}
    ).get_json()
    assert [m["content"] for m in older["data"]] == [str(n) for n in range(5)]
    assert older["more"] is False


def test_bad_messages_are_refused(member, query):
    alice, alice_id, alice_account = member()
    _, bob_id, bob_account = member()
    befriend(query, alice_id, bob_id)
    url = f"/api/v1/chats/{bob_account}/messages"
    assert alice.post(url, json={"content": "   "}).status_code == 400
    assert alice.post(url, json={"content": "x" * 1001}).status_code == 400
    to_nobody = alice.post("/api/v1/chats/nobody-here/messages", json={"content": "x"})
    assert to_nobody.status_code == 404
    to_self = alice.post(f"/api/v1/chats/{alice_account}/messages", json={"content": "x"})
    assert to_self.status_code == 400
    assert alice.get(url, query_string={"before": "x"}).status_code == 400


def test_sending_is_rate_limited(member, query, monkeypatch):
    monkeypatch.setattr("module.rules.CHAT_PER_MINUTE", 2)
    alice, alice_id, _ = member()
    _, bob_id, bob_account = member()
    befriend(query, alice_id, bob_id)
    url = f"/api/v1/chats/{bob_account}/messages"
    assert [alice.post(url, json={"content": "x"}).status_code for _ in range(3)] == [201, 201, 429]


def test_a_new_conversation_is_empty(member, query):
    alice, alice_id, _ = member()
    _, bob_id, bob_account = member()
    befriend(query, alice_id, bob_id)
    history = alice.get(f"/api/v1/chats/{bob_account}/messages").get_json()
    assert history["data"] == [] and history["more"] is False and history["can_send"] is True
    assert alice.get("/api/v1/chats").get_json() == {"data": [], "unread": 0}


def test_chat_needs_sign_in(client):
    assert client.get("/api/v1/chats").status_code == 401


def test_typing_reaches_friends_only(member, socket_client, query):
    alice, alice_id, alice_account = member()
    bob, bob_id, bob_account = member()
    carol, _, _ = member()
    befriend(query, alice_id, bob_id)
    sa, sb, sc = socket_client(alice), socket_client(bob), socket_client(carol)
    sb.get_received()
    sa.emit("chat:typing", {"to": bob_account})
    assert events(sb, "chat:typing") == [{"from": alice_account}]
    sc.emit("chat:typing", {"to": bob_account})
    assert events(sb, "chat:typing") == []
