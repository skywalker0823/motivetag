"""Content Security Policy (api/security.py) and the legacy-password migration."""

import re

from werkzeug.security import check_password_hash


def nonces(html):
    return set(re.findall(r'<script[^>]* nonce="([^"]+)"', html))


def test_pages_carry_a_fresh_nonce_on_every_script(client, member):
    alice, _, account = member()
    for who, url in ((client, "/"), (alice, f"/{account}"), (client, "/privacy")):
        page = who.get(url)
        policy = page.headers["Content-Security-Policy"]
        html = page.get_data(as_text=True)
        found = nonces(html)
        assert len(found) == 1, url
        assert f"'nonce-{found.pop()}'" in policy
        # Every executable script carries it; only data blocks go without.
        for tag in re.findall(r"<script[^>]*>", html):
            assert "nonce=" in tag or 'type="application/json"' in tag, tag
        assert "frame-ancestors 'none'" in policy and "object-src 'none'" in policy
    assert nonces(client.get("/").get_data(as_text=True)) != nonces(
        client.get("/").get_data(as_text=True)
    )


def test_json_answers_have_no_policy(client):
    assert "Content-Security-Policy" not in client.get("/api/v1/posts/explore").headers


def test_sign_in_still_works_after_hashing(member, query):
    _, member_id, account = member()
    stored = query("SELECT password FROM member WHERE member_id=%s", member_id)[0]["password"]
    assert stored.startswith(("scrypt:", "pbkdf2:"))
    assert check_password_hash(stored, account + "-pw")
