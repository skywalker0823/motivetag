import io
import json
import re
import uuid
from datetime import timedelta

import pytest
from conftest import NOW

from module import disposable, email_verification, mailer, turnstile


@pytest.fixture()
def outbox(app, monkeypatch):
    """Turns verification on and catches e-mail instead of sending it through SES."""
    monkeypatch.setitem(app.config, "EMAIL_FROM", "no-reply@motivetag.com")
    sent = []
    monkeypatch.setattr(mailer, "send", lambda to, subject, text, html: sent.append((to, text)))
    return sent


def sign_up(app, email=None):
    """A new member signed in through the pages, as a person would; returns (client, account)."""
    account = "v" + uuid.uuid4().hex[:12]
    client = app.test_client()
    body = {
        "account": account,
        "password": account + "-pw",
        "email": email or account + "@example.com",
        "birthday": "2000-1-1",
    }
    result = client.post("/api/member", json=body)
    assert result.get_json() == {"ok": True}, result.get_json()
    client.put("/api/member", json={"account": account, "password": account + "-pw", "time": NOW})
    return client, account


def token_in(text):
    return re.search(r"token=([\w-]+)", text).group(1)


def post(client):
    return client.post("/api/blocks", json={"type": "PUBLIC", "content": "hello"})


def test_new_member_must_verify_before_posting(app, outbox):
    client, account = sign_up(app)
    assert outbox[-1][0] == f"{account}@example.com"
    assert "/api/v1/email/verify?token=" in outbox[-1][1]
    assert client.get("/api/member").get_json()["data"]["email_verified"] is False

    blocked = post(client)
    assert blocked.status_code == 403
    assert blocked.get_json() == {"error": "email not verified"}
    assert client.post("/api/friend", json={"who": "someone"}).status_code == 403
    assert client.post("/api/message", json={"block_id": 1, "message": "hi"}).status_code == 403
    # Reading still works.
    assert client.get("/api/v1/posts/explore").status_code == 200

    link = client.get(f"/api/v1/email/verify?token={token_in(outbox[-1][1])}")
    assert link.status_code == 302
    assert link.headers["Location"] == f"/{account}?verified=1"
    assert client.get("/api/member").get_json()["data"]["email_verified"] is True
    assert post(client).get_json()["ok"]


def test_link_works_in_another_browser_and_bad_links_are_refused(app, client, outbox):
    member, account = sign_up(app)
    token = token_in(outbox[-1][1])
    assert client.get(f"/api/v1/email/verify?token={token}").headers["Location"] == "/?verified=1"
    assert post(member).get_json()["ok"]

    assert client.get("/api/v1/email/verify?token=nope").headers["Location"] == "/?verify=invalid"
    assert member.get("/api/v1/email/verify").headers["Location"] == f"/{account}?verify=invalid"


def test_expired_link_is_refused(app, client, outbox, monkeypatch):
    member, _ = sign_up(app)
    token = token_in(outbox[-1][1])
    later = email_verification.taipei_datetime() + timedelta(hours=25)
    monkeypatch.setattr(email_verification, "taipei_datetime", lambda: later)
    assert (
        client.get(f"/api/v1/email/verify?token={token}").headers["Location"] == "/?verify=invalid"
    )
    assert post(member).status_code == 403


def test_resend_waits_a_minute_and_stops_for_the_day(app, outbox, monkeypatch):
    client, _ = sign_up(app)
    too_soon = client.post("/api/v1/email/verification")
    assert too_soon.status_code == 429
    assert too_soon.get_json()["error"]["code"] == "too_soon"
    assert int(too_soon.headers["Retry-After"]) <= 60

    # Early tomorrow, so the day's count starts at zero whenever the test runs.
    now = (email_verification.taipei_datetime() + timedelta(days=1)).replace(hour=0, minute=30)
    for minutes in range(0, 10, 2):  # PER_MEMBER_DAILY resends, two minutes apart
        at = now + timedelta(minutes=minutes)
        monkeypatch.setattr(email_verification, "taipei_datetime", lambda at=at: at)
        assert client.post("/api/v1/email/verification").get_json() == {
            "sent": True,
            "email": outbox[-1][0],
        }
    at = now + timedelta(minutes=20)
    monkeypatch.setattr(email_verification, "taipei_datetime", lambda: at)
    tired = client.post("/api/v1/email/verification")
    assert tired.status_code == 429
    assert tired.get_json()["error"]["code"] == "limit_reached"


def test_site_wide_daily_limit(app, outbox, monkeypatch):
    client, _ = sign_up(app)
    monkeypatch.setattr(email_verification, "DAILY_LIMIT", 1)  # already used today
    later = email_verification.taipei_datetime() + timedelta(minutes=2)
    monkeypatch.setattr(email_verification, "taipei_datetime", lambda: later)
    capped = client.post("/api/v1/email/verification")
    assert capped.status_code == 429
    assert "上限" in capped.get_json()["error"]["message"]


def test_resend_after_verifying_or_when_off(app, member, outbox):
    client, _ = sign_up(app)
    client.get(f"/api/v1/email/verify?token={token_in(outbox[-1][1])}")
    assert (
        client.post("/api/v1/email/verification").get_json()["error"]["code"] == "already_verified"
    )


def test_nothing_is_required_while_email_is_off(member):
    client, _, _ = member()  # signed up with EMAIL_FROM unset
    assert client.get("/api/member").get_json()["data"]["email_verified"] is True
    assert client.post("/api/v1/email/verification").status_code == 409
    assert post(client).get_json()["ok"]


def test_unverified_member_cannot_chat(app, member, outbox):
    client, _ = sign_up(app)
    _, _, friend = member()
    result = client.post(f"/api/v1/chats/{friend}/messages", json={"content": "hi"})
    assert result.status_code == 403
    assert result.get_json()["error"]["code"] == "email_not_verified"


# ---------- Throwaway addresses ----------


def test_disposable_domains():
    assert disposable.is_disposable("a@mailinator.com")
    assert disposable.is_disposable("a@inbox.mailinator.com")  # subdomains too
    assert disposable.is_disposable("a@MAILINATOR.COM.")
    assert not disposable.is_disposable("a@gmail.com")
    assert not disposable.is_disposable("a@motivetag.com")


def test_sign_up_refuses_disposable_address(client):
    result = client.post(
        "/api/member",
        json={
            "account": "d" + uuid.uuid4().hex[:10],
            "password": "long-enough",
            "email": "someone@mailinator.com",
            "birthday": "2000-1-1",
        },
    )
    assert result.status_code == 400
    assert "拋棄式" in result.get_json()["error"]


# ---------- Turnstile ----------


@pytest.fixture()
def cloudflare(app, monkeypatch):
    """Turns Turnstile on and answers for Cloudflare; returns what it was asked."""
    monkeypatch.setitem(app.config, "TURNSTILE_SECRET", "test-secret")
    monkeypatch.setitem(app.config, "TURNSTILE_SITE_KEY", "test-site-key")
    asked = []

    def answer(success):
        def urlopen(request, timeout):
            asked.append(request.data.decode())
            return io.BytesIO(json.dumps({"success": success}).encode())

        monkeypatch.setattr(turnstile.urllib.request, "urlopen", urlopen)

    return answer, asked


def signup_body(**extra):
    account = "t" + uuid.uuid4().hex[:10]
    return {
        "account": account,
        "password": "long-enough",
        "email": account + "@example.com",
        "birthday": "2000-1-1",
        **extra,
    }


def test_turnstile_token_is_checked(client, cloudflare):
    answer, asked = cloudflare
    answer(True)
    assert client.post("/api/member", json=signup_body(turnstile_token="good")).get_json() == {
        "ok": True
    }
    assert "secret=test-secret" in asked[-1] and "response=good" in asked[-1]

    answer(False)
    refused = client.post("/api/member", json=signup_body(turnstile_token="bad"))
    assert refused.status_code == 400
    assert "人機驗證" in refused.get_json()["error"]
    assert client.post("/api/member", json=signup_body()).status_code == 400  # no token


def test_turnstile_fails_closed_when_cloudflare_is_unreachable(client, cloudflare, monkeypatch):
    def down(request, timeout):
        raise OSError("unreachable")

    monkeypatch.setattr(turnstile.urllib.request, "urlopen", down)
    assert client.post("/api/member", json=signup_body(turnstile_token="x")).status_code == 400


def test_mailer_calls_ses_with_the_site_address(app, monkeypatch):
    calls = []

    class FakeSes:
        def send_email(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setitem(app.config, "EMAIL_FROM", "no-reply@motivetag.com")
    monkeypatch.setitem(app.config, "SES_REGION", "ap-northeast-1")
    monkeypatch.setattr(mailer.boto3, "client", lambda service, region_name: FakeSes())
    with app.app_context():
        assert mailer.send("a@example.com", "主旨", "text", "<p>html</p>")
    assert calls[0]["FromEmailAddress"] == "MotiveTag <no-reply@motivetag.com>"
    assert calls[0]["Destination"] == {"ToAddresses": ["a@example.com"]}
    assert calls[0]["Content"]["Simple"]["Subject"]["Data"] == "主旨"


def test_turnstile_needs_both_keys(app, client, monkeypatch):
    monkeypatch.setitem(app.config, "TURNSTILE_SECRET", "only-the-secret")
    monkeypatch.setitem(app.config, "TURNSTILE_SITE_KEY", None)
    assert client.post("/api/member", json=signup_body()).get_json() == {"ok": True}
