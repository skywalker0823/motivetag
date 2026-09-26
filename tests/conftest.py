"""Integration tests run against a real MySQL that `alembic upgrade head` has prepared.

Point them at a database with AWS_motivetag_DB / DB_PASSWORD (see README).
"""

import importlib
import os
import uuid

import pymysql
import pytest

os.environ.setdefault("AWS_motivetag_DB", "127.0.0.1")
os.environ.setdefault("DB_PASSWORD", "testpw")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test.apps.googleusercontent.com")

from api import create_app, socketio  # noqa: E402
from config import db_settings  # noqa: E402

NOW = "2026-09-26 10:00:00"


@pytest.fixture(scope="session")
def app():
    app = create_app("dev")
    app.config.update(TESTING=True)
    return app


@pytest.fixture(scope="session")
def db():
    settings = db_settings()
    conn = pymysql.connect(
        host=settings["hosts"][0],
        user=settings["user"],
        password=settings["password"],
        database=settings["database"],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    yield conn
    conn.close()


@pytest.fixture()
def query(db):
    def run(sql, *args):
        with db.cursor() as cursor:
            cursor.execute(sql, args)
            return cursor.fetchall()

    return run


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def member(app):
    """Sign up and sign in a fresh member; returns (client, member_id, account)."""

    def create():
        account = "t" + uuid.uuid4().hex[:12]
        client = app.test_client()
        client.post(
            "/api/member",
            json={
                "account": account,
                "password": account + "-pw",
                "email": account + "@example.com",
                "birthday": "2000-1-1",
                "first_signup": "2026-9-26",
            },
        )
        result = client.put(
            "/api/member", json={"account": account, "password": account + "-pw", "time": NOW}
        ).get_json()
        assert result.get("ok"), result
        return client, result["data"]["member_id"], account

    return create


@pytest.fixture()
def socket_client(app):
    def connect(flask_client):
        return socketio.test_client(app, flask_test_client=flask_client)

    return connect


@pytest.fixture()
def chat_state():
    return importlib.import_module("api.blueprints.api_chat")
