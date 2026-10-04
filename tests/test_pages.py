def test_home_page(client):
    assert client.get("/").status_code == 200


def test_home_page_rejects_post(client):
    assert client.post("/").status_code == 405


def test_member_page_requires_login(client):
    assert client.get("/tag/cats").status_code == 302


def test_healthz(client):
    assert client.get("/healthz").get_json() == {"ok": True}


def test_avatar_without_upload_redirects_to_the_default(client):
    response = client.get("/images/avatar_5000")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/img/avatar.svg")
    assert "max-age" in response.headers["Cache-Control"]


def test_uploaded_avatar_redirects_to_presigned_s3_url(member, query):
    alice, alice_id, _ = member()
    query("UPDATE member SET member_img=%s WHERE member_id=%s", f"avatar_{alice_id}", alice_id)
    response = alice.get(f"/images/avatar_{alice_id}")
    location = response.headers["Location"]
    assert response.status_code == 302
    assert "motivetag-images-test" in location
    assert f"avatar_{alice_id}" in location
    assert "X-Amz-Signature" in location
    assert "response-cache-control" in location


def test_image_rejects_unexpected_keys(client):
    assert client.get("/images/..%2Fsecret").status_code == 404
    assert client.get("/images/other_1").status_code == 404


def test_assets_are_versioned_and_cached_for_a_year(client):
    page = client.get("/").get_data(as_text=True)
    assert '<script type="importmap">' in page
    assert 'rel="modulepreload" href="/js/lib/api.js?v=' in page
    css = next(
        part.split('"')[0] for part in page.split('href="') if part.startswith("/css/base.css?v=")
    )
    assert "immutable" in client.get(css).headers["Cache-Control"]
    assert "immutable" not in client.get("/css/base.css").headers["Cache-Control"]


def test_member_page_carries_who_i_am(member):
    alice, alice_id, account = member()
    page = alice.get(f"/{account}").get_data(as_text=True)
    bootstrap = page.split('id="bootstrap">', 1)[1].split("</script>", 1)[0]
    assert f'"member_id": {alice_id}' in bootstrap
    assert "password" not in bootstrap


def test_privacy_and_terms_pages(client, app, monkeypatch):
    for path in ("/privacy", "/terms"):
        page = client.get(path)
        assert page.status_code == 200
        assert "35 天" in page.get_data(as_text=True)
    monkeypatch.setitem(app.config, "CONTACT_EMAIL", "hello@example.com")
    assert "mailto:hello@example.com" in client.get("/privacy").get_data(as_text=True)
    assert 'href="/terms"' in client.get("/").get_data(as_text=True)
