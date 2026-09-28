def subscribe(client, *tags):
    for tag in tags:
        assert client.patch("/api/member_tags", json={"tag": tag}).get_json().get("ok")


def suggested(client):
    response = client.get("/api/v1/members/suggested")
    assert response.status_code == 200
    return {m["account"]: m for m in response.get_json()["data"]}


def test_suggests_people_with_shared_tags_best_match_first(member):
    alice, _, _ = member()
    bob, _, bob_account = member()
    carol, _, carol_account = member()
    dave, _, dave_account = member()
    subscribe(alice, "sgcoffee", "sghiking", "sgcats")
    subscribe(bob, "sgcoffee", "sghiking")
    subscribe(carol, "sgcats")
    subscribe(dave, "sgunrelated")  # shares only the starter tag everyone gets

    people = suggested(alice)
    assert people[bob_account]["shared_count"] == 2
    assert sorted(people[bob_account]["shared"]) == ["sgcoffee", "sghiking"]
    assert people[carol_account]["shared"] == ["sgcats"]
    assert dave_account not in people
    order = [a for a in people if a in (bob_account, carol_account)]
    assert order == [bob_account, carol_account]


def test_friends_and_pending_invites_are_not_suggested(member):
    alice, _, alice_account = member()
    bob, _, bob_account = member()
    carol, _, carol_account = member()
    for client in (alice, bob, carol):
        subscribe(client, "sgfilm")
    alice.post("/api/friend", json={"who": bob_account})  # pending
    people = suggested(alice)
    assert bob_account not in people
    assert carol_account in people
    assert alice_account not in suggested(bob)  # the invite shows in bob's list instead


def test_member_card_shows_age_and_shared_tags_not_birthday(member):
    alice, _, _ = member()
    bob, bob_id, _ = member()
    subscribe(alice, "sgjazz", "sgtea")
    subscribe(bob, "sgjazz")
    card = alice.get(f"/api/get_user_sp?member_id={bob_id}").get_json()
    assert "birthday" not in card["data"]
    assert card["data"]["age"] >= 18
    assert card["shared_tags"] == ["sgjazz"]


def test_suggestions_need_sign_in(client):
    assert client.get("/api/v1/members/suggested").status_code == 401
