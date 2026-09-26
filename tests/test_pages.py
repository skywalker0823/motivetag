def test_home_page(client):
    assert client.get("/").status_code == 200


def test_home_page_rejects_post(client):
    assert client.post("/").status_code == 405


def test_member_page_requires_login(client):
    assert client.get("/tag/cats").status_code == 302


def test_healthz(client):
    assert client.get("/healthz").get_json() == {"ok": True}


def test_image_redirects_to_presigned_s3_url(client):
    response = client.get("/images/avatar_5000")
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "motivetag-images-test" in location
    assert "avatar_5000" in location
    assert "X-Amz-Signature" in location


def test_image_rejects_unexpected_keys(client):
    assert client.get("/images/..%2Fsecret").status_code == 404
    assert client.get("/images/other_1").status_code == 404
