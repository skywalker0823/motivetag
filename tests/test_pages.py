def test_home_page(client):
    assert client.get("/").status_code == 200


def test_home_page_rejects_post(client):
    assert client.post("/").status_code == 405


def test_member_page_requires_login(client):
    assert client.get("/tag/cats").status_code == 302
