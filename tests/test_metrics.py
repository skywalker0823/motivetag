import re

from conftest import NOW


def metric(client, name, **labels):
    """The current value of one series in /metrics, or 0."""
    text = client.get("/metrics").get_data(as_text=True)
    want = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    for line in text.splitlines():
        match = re.match(rf"^{name}\{{(.*)\}} (\S+)$", line)
        if match and ",".join(sorted(match.group(1).split(","))) == want:
            return float(match.group(2))
    return 0.0


def test_requests_are_counted_by_route_pattern(client):
    before = metric(
        client,
        "motivetag_http_requests_total",
        endpoint="/tag/<tag_name>",
        method="GET",
        status="302",
    )
    client.get("/tag/咖啡")
    client.get("/tag/登山")
    after = metric(
        client,
        "motivetag_http_requests_total",
        endpoint="/tag/<tag_name>",
        method="GET",
        status="302",
    )
    assert after == before + 2
    text = client.get("/metrics").get_data(as_text=True)
    assert "咖啡" not in text  # raw URLs never become labels
    assert "motivetag_http_request_duration_seconds_bucket" in text
    assert "_created" not in text


def test_sign_ins_and_sign_ups_are_counted(client, member):
    failed = metric(client, "motivetag_auth_events_total", event="login_failed")
    ok = metric(client, "motivetag_auth_events_total", event="login_ok")
    member()  # signs up and signs in
    client.put("/api/member", json={"account": "nobody-here", "password": "wrong", "time": NOW})
    assert metric(client, "motivetag_auth_events_total", event="login_ok") == ok + 1
    assert metric(client, "motivetag_auth_events_total", event="login_failed") == failed + 1


def test_metrics_are_not_served_through_nginx(client):
    assert client.get("/metrics").status_code == 200
    assert client.get("/metrics", headers={"X-Forwarded-For": "203.0.113.9"}).status_code == 404
