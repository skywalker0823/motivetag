"""deploy/aws_creds_relay.py serves the Pi's AWS credentials the way EC2's IMDSv2 did."""

import importlib.util
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import botocore.session
import pytest

spec = importlib.util.spec_from_file_location(
    "aws_creds_relay", Path(__file__).parent.parent / "deploy" / "aws_creds_relay.py"
)
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)

CREDENTIALS = """[default]
aws_access_key_id = ASIAEXAMPLE
aws_secret_access_key = secret-example
aws_session_token = token-example
"""


@pytest.fixture
def server(tmp_path, monkeypatch):
    path = tmp_path / "credentials"
    path.write_text(CREDENTIALS)
    monkeypatch.setattr(relay, "CREDENTIALS_FILE", str(path))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), relay.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/", path
    httpd.shutdown()


def app_credentials(endpoint, monkeypatch, tmp_path):
    """What boto3 in the app container finds: nothing but the metadata endpoint."""
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN", "AWS_PROFILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "none"))
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "none"))
    monkeypatch.setenv("AWS_EC2_METADATA_SERVICE_ENDPOINT", endpoint)
    return botocore.session.get_session().get_credentials()


def test_botocore_gets_refreshable_credentials(server, monkeypatch, tmp_path):
    endpoint, _ = server
    creds = app_credentials(endpoint, monkeypatch, tmp_path)
    assert creds.method == "iam-role"  # refreshed before expiry, as on EC2
    frozen = creds.get_frozen_credentials()
    assert frozen.access_key == "ASIAEXAMPLE"
    assert frozen.secret_key == "secret-example"
    assert frozen.token == "token-example"


def test_renewed_file_is_read_again(server, monkeypatch, tmp_path):
    endpoint, path = server
    path.write_text(CREDENTIALS.replace("ASIAEXAMPLE", "ASIARENEWED"))
    creds = app_credentials(endpoint, monkeypatch, tmp_path)
    assert creds.get_frozen_credentials().access_key == "ASIARENEWED"


def test_get_without_token_is_refused(server):
    endpoint, _ = server
    url = endpoint + "latest/meta-data/iam/security-credentials/motivetag-app"
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(url, timeout=2)  # noqa: S310 - local test server
    assert error.value.code == 401


def test_token_needs_a_valid_ttl(server):
    endpoint, _ = server
    request = urllib.request.Request(endpoint + "latest/api/token", method="PUT")  # noqa: S310
    with pytest.raises(urllib.error.HTTPError) as error:
        urllib.request.urlopen(request, timeout=2)  # noqa: S310
    assert error.value.code == 400
