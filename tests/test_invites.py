import uuid
from urllib.parse import parse_qs, urlparse

from conftest import NOW


def invite_token(client):
    url = client.get("/api/v1/invites/mine").get_json()["url"]
    return parse_qs(urlparse(url).query)["invite"][0]


def sign_up(client, invite=None):
    account = "i" + uuid.uuid4().hex[:12]
    body = {
        "account": account,
        "password": account + "-pw",
        "email": account + "@example.com",
        "birthday": "2000-1-1",
    }
    if invite is not None:
        body["invite"] = invite
    assert client.post("/api/member", json=body).get_json() == {"ok": True}
    client.put("/api/member", json={"account": account, "password": account + "-pw", "time": NOW})
    return account


def friend_accounts(client):
    relations = client.get("/api/friend").get_json()["ok"]
    relations = relations if isinstance(relations, list) else []
    return {r["req_from"] for r in relations if str(r["status"]) == "0"} | {
        r["req_to"] for r in relations if str(r["status"]) == "0"
    }


def test_signing_up_through_an_invite_makes_friends_and_tells_the_inviter(app, member):
    alice, _, alice_account = member()
    token = invite_token(alice)
    assert invite_token(alice) == token  # the same link every time

    newcomer = app.test_client()
    new_account = sign_up(newcomer, invite=token)
    assert alice_account in friend_accounts(newcomer)
    assert new_account in friend_accounts(alice)
    notes = alice.get("/api/notifi").get_json()["data"]
    assert any(new_account in n["content"] and "邀請" in n["content"] for n in notes)


def test_bad_or_missing_invites_still_sign_up(app, member):
    alice, _, alice_account = member()
    forged = invite_token(alice)[:-2] + "xx"
    for invite in (forged, "nonsense", None, 123):
        client = app.test_client()
        sign_up(client, invite=invite)
        assert alice_account not in friend_accounts(client)


def test_landing_page_names_the_inviter_in_its_link_preview(client, member):
    alice, _, alice_account = member()
    page = client.get(f"/?invite={invite_token(alice)}").get_data(as_text=True)
    assert f'<meta property="og:title" content="{alice_account} 邀請你加入 MotiveTag">' in page
    assert f"<strong>{alice_account}</strong> 邀請你加入" in page

    plain = client.get("/").get_data(as_text=True)
    assert 'property="og:image" content="http://localhost/img/og.png?v=' in plain
    assert "邀請你加入" not in plain
    assert "twitter:card" in plain


def test_invite_link_needs_sign_in(client):
    assert client.get("/api/v1/invites/mine").status_code == 401
