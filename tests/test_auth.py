from conftest import NOW
from werkzeug.security import check_password_hash


def sign_in(client, account, password):
    return client.put(
        "/api/member", json={"account": account, "password": password, "time": NOW}
    ).get_json()


def test_account_check_only_reveals_existence(client):
    assert client.get("/api/member?account_check=guest").get_json() == {"ok": True}
    assert client.get("/api/member?account_check=nobody-here").get_json() == {"ok": None}


def test_guest_demo_login(client):
    result = sign_in(client, "guest", "guest")
    assert result["ok"] is True
    assert "password" not in result["data"]


def test_signup_stores_password_hash(member, query):
    _, member_id, account = member()
    stored = query("SELECT password FROM member WHERE member_id=%s", member_id)[0]["password"]
    assert stored.startswith("scrypt:")
    assert check_password_hash(stored, account + "-pw")


def test_wrong_password_rejected(member, client):
    _, _, account = member()
    assert "error" in sign_in(client, account, "wrong")


def test_legacy_plaintext_password_is_upgraded(client, query):
    query("DELETE FROM member WHERE account='legacyuser'")
    query(
        "INSERT INTO member (account, password, email, first_signup) "
        "VALUES ('legacyuser', 'oldpass', 'legacy@example.com', '2020-01-01')"
    )
    assert sign_in(client, "legacyuser", "oldpass")["ok"] is True
    stored = query("SELECT password FROM member WHERE account='legacyuser'")[0]["password"]
    assert check_password_hash(stored, "oldpass")


def test_member_api_never_returns_password(member):
    client, _, _ = member()
    assert "password" not in client.get("/api/member").get_json()["data"]


def test_forged_google_profile_rejected(client):
    forged = {"user_data": {"given_name": "guest", "sub": "12345", "email": "a@example.com"}}
    assert client.post("/api/google_sign_in", json=forged).status_code == 401


def test_invalid_google_token_rejected(client):
    assert client.post("/api/google_sign_in", json={"credential": "not.a.jwt"}).status_code == 401
